from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from majiang_support.core.effective import EffectiveTiles
from majiang_support.core.hand import Hand, all_suited_tile_ids
from majiang_support.core.meld import Meld
from majiang_support.core.shanten import calculate_seven_pairs_shanten, calculate_standard_shanten
from majiang_support.core.tile import SUIT_LABELS, Tile, tile_label


STAGE_FACTOR = {
    "early": 1.15,
    "middle": 1.0,
    "late": 0.75,
}

FAN_TABLE = {
    "平胡": 1,
    "七对": 4,
    "对对胡": 2,
    "清一色": 4,
}


@dataclass(frozen=True)
class RouteEvaluation:
    name: str
    shanten: int
    fan: int
    effective: EffectiveTiles
    probability: float
    ev: float
    target_suit: str | None = None

    @property
    def label(self) -> str:
        if self.target_suit:
            return f"{self.name}({SUIT_LABELS[self.target_suit]})"
        return self.name


def evaluate_routes(
    hand: Hand,
    remaining_counts: tuple[int, ...],
    forbidden_suit: str | None = None,
    stage: str = "middle",
    open_melds: tuple[Meld, ...] = (),
    probability_total: int | None = None,
) -> tuple[RouteEvaluation, ...]:
    factor = STAGE_FACTOR.get(stage, STAGE_FACTOR["middle"])
    unknown_total = probability_total if probability_total is not None else sum(remaining_counts)
    open_count = len(open_melds)
    routes: list[RouteEvaluation] = [
        _build_route("平胡", hand, remaining_counts, lambda h: calculate_standard_shanten(h, open_count), FAN_TABLE["平胡"], factor, unknown_total, forbidden_suit),
        _build_route("七对", hand, remaining_counts, lambda h: calculate_seven_pairs_shanten(h, open_count), FAN_TABLE["七对"], factor, unknown_total, forbidden_suit),
        _build_route("对对胡", hand, remaining_counts, lambda h: calculate_all_triplets_shanten(h, open_melds), FAN_TABLE["对对胡"], factor, unknown_total, forbidden_suit),
    ]

    for suit in ("m", "p", "s"):
        if forbidden_suit == suit:
            continue
        routes.append(_evaluate_flush_route(hand, remaining_counts, suit, factor, unknown_total, forbidden_suit, open_melds))

    return tuple(sorted(routes, key=lambda route: (route.ev, -route.shanten, route.effective.remaining_total), reverse=True))


def calculate_all_triplets_shanten(hand: Hand, open_melds: tuple[Meld, ...] = ()) -> int:
    open_triplets = sum(1 for meld in open_melds if meld.is_triplet_like)
    triplets = sum(1 for count in hand.counts if count >= 3) + open_triplets
    pairs = sum(1 for count in hand.counts if count >= 2)

    best = 8
    for uses_pair in (False, True):
        if uses_pair and pairs == 0:
            continue
        pair_count = 1 if uses_pair else 0
        taatsu = pairs - pair_count
        needed_melds = 4
        if triplets + taatsu > needed_melds:
            taatsu = needed_melds - triplets
        best = min(best, 8 - 2 * triplets - taatsu - pair_count)
    return best


def _build_route(
    name: str,
    hand: Hand,
    remaining_counts: tuple[int, ...],
    shanten_fn: Callable[[Hand], int],
    fan: int,
    stage_factor: float,
    unknown_total: int,
    forbidden_suit: str | None,
) -> RouteEvaluation:
    shanten = shanten_fn(hand)
    effective = _route_effective_tiles(hand, remaining_counts, shanten_fn, forbidden_suit=forbidden_suit)
    probability = _estimate_probability(effective.remaining_total, unknown_total, shanten)
    return RouteEvaluation(
        name=name,
        shanten=shanten,
        fan=fan,
        effective=effective,
        probability=probability,
        ev=probability * fan * stage_factor,
    )


def _evaluate_flush_route(
    hand: Hand,
    remaining_counts: tuple[int, ...],
    target_suit: str,
    stage_factor: float,
    unknown_total: int,
    forbidden_suit: str | None,
    open_melds: tuple[Meld, ...],
) -> RouteEvaluation:
    if any(meld.tile.suit != target_suit for meld in open_melds):
        return RouteEvaluation(
            name="清一色",
            target_suit=target_suit,
            shanten=99,
            fan=FAN_TABLE["清一色"],
            effective=EffectiveTiles((), 0),
            probability=0.0,
            ev=0.0,
        )

    off_suit_count = sum(
        count
        for tile_id, count in enumerate(hand.counts)
        if count and Tile.from_id(tile_id).suit != target_suit
    )

    def flush_shanten(next_hand: Hand) -> int:
        return calculate_standard_shanten(next_hand, open_meld_count=len(open_melds)) + off_suit_count_for(next_hand, target_suit)

    shanten = flush_shanten(hand)
    effective = _route_effective_tiles(
        hand,
        remaining_counts,
        flush_shanten,
        forbidden_suit=forbidden_suit,
        required_suit=target_suit,
    )
    probability = _estimate_probability(effective.remaining_total, unknown_total, shanten)
    return RouteEvaluation(
        name="清一色",
        target_suit=target_suit,
        shanten=shanten,
        fan=FAN_TABLE["清一色"],
        effective=effective,
        probability=probability,
        ev=probability * FAN_TABLE["清一色"] * stage_factor,
    )


def off_suit_count_for(hand: Hand, target_suit: str) -> int:
    return sum(
        count
        for tile_id, count in enumerate(hand.counts)
        if count and Tile.from_id(tile_id).suit != target_suit
    )


def _route_effective_tiles(
    hand: Hand,
    remaining_counts: tuple[int, ...],
    shanten_fn: Callable[[Hand], int],
    forbidden_suit: str | None = None,
    required_suit: str | None = None,
) -> EffectiveTiles:
    base_shanten = shanten_fn(hand)
    useful: list[int] = []
    total = 0
    for tile_id in all_suited_tile_ids():
        tile = Tile.from_id(tile_id)
        if forbidden_suit and tile.suit == forbidden_suit:
            continue
        if required_suit and tile.suit != required_suit:
            continue
        if remaining_counts[tile_id] <= 0 or hand.count(tile_id) >= 4:
            continue
        next_hand = hand.add(tile_id)
        if shanten_fn(next_hand) < base_shanten:
            useful.append(tile_id)
            total += remaining_counts[tile_id]
    return EffectiveTiles(tuple(useful), total)


def _estimate_probability(effective_count: int, unknown_total: int, shanten: int) -> float:
    if shanten < 0:
        return 1.0
    if unknown_total <= 0 or effective_count <= 0:
        return 0.0
    draw_probability = effective_count / unknown_total
    distance_decay = 0.35 ** shanten
    return min(1.0, (draw_probability ** (shanten + 1)) * distance_decay)


def route_effective_labels(route: RouteEvaluation) -> list[str]:
    return [tile_label(tile_id) for tile_id in route.effective.tile_ids]
