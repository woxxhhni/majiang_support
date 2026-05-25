from __future__ import annotations

from dataclasses import dataclass

from majiang_support.core.effective import EffectiveTiles
from majiang_support.core.hand import Hand
from majiang_support.core.meld import Meld
from majiang_support.core.remaining import remaining_counts_after_discard
from majiang_support.core.shanten import (
    calculate_seven_pairs_shanten,
    calculate_standard_shanten,
)
from majiang_support.core.tile import Tile
from majiang_support.strategy.ev import RouteEvaluation, evaluate_routes
from majiang_support.strategy.structure import evaluate_structure


@dataclass(frozen=True)
class DiscardCandidate:
    tile_id: int
    score: int
    shanten: int
    standard_shanten: int
    seven_pairs_shanten: int
    effective: EffectiveTiles
    structure_score: int
    discard_value: int
    best_route: RouteEvaluation
    routes: tuple[RouteEvaluation, ...]
    ev: float
    reasons: tuple[str, ...]

    @property
    def tile(self) -> Tile:
        return Tile.from_id(self.tile_id)


@dataclass(frozen=True)
class Recommendation:
    best: DiscardCandidate
    candidates: tuple[DiscardCandidate, ...]
    missing_suit_active: bool


def recommend_discard(
    hand: Hand,
    missing_suit: str | None = None,
    open_melds: tuple[Meld, ...] = (),
    visible_counts: tuple[int, ...] | None = None,
) -> Recommendation:
    if hand.size not in {2, 5, 8, 11, 14}:
        raise ValueError("出牌推荐需要 14 张手牌，或包含副露后的 3n+2 张手牌")

    discard_ids = hand.candidate_discards(missing_suit)
    missing_active = bool(missing_suit and hand.has_suit(missing_suit))
    candidates = [
        _score_discard(hand, tile_id, missing_suit if missing_active else None, missing_active, open_melds, visible_counts)
        for tile_id in discard_ids
    ]
    ordered = tuple(
        sorted(
            candidates,
            key=lambda item: (
                item.score,
                -item.shanten,
                item.effective.remaining_total,
                item.structure_score,
                -item.discard_value,
                item.ev,
                item.tile_id,
            ),
            reverse=True,
        )
    )
    return Recommendation(best=ordered[0], candidates=ordered, missing_suit_active=missing_active)


def _score_discard(
    hand: Hand,
    tile_id: int,
    forbidden_suit: str | None,
    missing_active: bool,
    open_melds: tuple[Meld, ...],
    visible_counts: tuple[int, ...] | None,
) -> DiscardCandidate:
    after = hand.remove(tile_id)
    remaining_counts = remaining_counts_after_discard(hand, tile_id, visible_counts=visible_counts, melds=open_melds)
    probability_total = sum(remaining_counts_after_discard(hand, tile_id, melds=open_melds))
    routes = evaluate_routes(
        after,
        remaining_counts,
        forbidden_suit=forbidden_suit,
        open_melds=open_melds,
        probability_total=probability_total,
    )
    best_route = routes[0]
    shanten = best_route.shanten
    standard_shanten = calculate_standard_shanten(after, open_meld_count=len(open_melds))
    seven_pairs_shanten = calculate_seven_pairs_shanten(after, open_meld_count=len(open_melds))
    effective = best_route.effective
    structure_score = evaluate_structure(after)
    discard_value = evaluate_discard_value(hand, tile_id)
    score = -1000 * shanten + 10 * effective.remaining_total + structure_score - discard_value + int(best_route.ev * 1000)
    reasons = _build_reasons(
        hand,
        tile_id,
        shanten,
        standard_shanten,
        seven_pairs_shanten,
        effective,
        structure_score,
        discard_value,
        best_route,
        missing_active,
    )
    return DiscardCandidate(
        tile_id=tile_id,
        score=score,
        shanten=shanten,
        standard_shanten=standard_shanten,
        seven_pairs_shanten=seven_pairs_shanten,
        effective=effective,
        structure_score=structure_score,
        discard_value=discard_value,
        best_route=best_route,
        routes=routes,
        ev=best_route.ev,
        reasons=tuple(reasons),
    )


def _build_reasons(
    hand: Hand,
    tile_id: int,
    shanten: int,
    standard_shanten: int,
    seven_pairs_shanten: int,
    effective: EffectiveTiles,
    structure_score: int,
    discard_value: int,
    best_route: RouteEvaluation,
    missing_active: bool,
) -> list[str]:
    tile = Tile.from_id(tile_id)
    reasons: list[str] = []

    if missing_active:
        reasons.append(f"当前仍有缺门牌，按川麻规则优先从缺门里打出 {tile.label}")

    if _is_isolated(hand, tile_id):
        rank = tile.rank
        if rank in {1, 9}:
            reasons.append(f"{tile.label} 是孤张幺九，后续组合空间较差")
        else:
            reasons.append(f"{tile.label} 是孤张，打出后不容易破坏已有搭子")

    if hand.count(tile_id) >= 2:
        reasons.append(f"{tile.label} 是对子的一部分，打出会降低对子价值")

    reasons.append(f"当前推荐路线：{best_route.label}，EV {best_route.ev:.3f}")

    if best_route.name == "七对":
        reasons.append(f"打出后七对路线更近，综合向听数为 {shanten}")
    elif best_route.name == "平胡":
        reasons.append(f"打出后平胡路线更近，综合向听数为 {shanten}")
    else:
        reasons.append(f"打出后 {best_route.label} 路线价值最高，路线向听数为 {shanten}")
    reasons.append(f"有效进张剩余 {effective.remaining_total} 张")
    reasons.append(f"保留结构评分为 {structure_score}")
    reasons.append(f"打出牌自身价值为 {discard_value}，越低越适合打")
    return reasons


def evaluate_discard_value(hand: Hand, tile_id: int) -> int:
    counts = hand.counts
    tile = Tile.from_id(tile_id)
    value = 0

    if counts[tile_id] >= 3:
        value += 42
    elif counts[tile_id] == 2:
        value += 24

    rank_index = tile.rank - 1
    suit_start = tile_id // 9 * 9

    if _has_neighbor(counts, suit_start, rank_index, 1):
        value += 16 if 1 <= rank_index <= 6 else 8
    if _has_neighbor(counts, suit_start, rank_index, -1):
        value += 16 if 2 <= rank_index <= 7 else 8
    if _has_neighbor(counts, suit_start, rank_index, 2):
        value += 9
    if _has_neighbor(counts, suit_start, rank_index, -2):
        value += 9

    if 2 <= tile.rank <= 8:
        value += 4
    else:
        value += 1

    if _is_isolated(hand, tile_id):
        value -= 10 if tile.rank in {1, 9} else 6

    return max(0, value)


def _has_neighbor(counts: tuple[int, ...], suit_start: int, rank_index: int, delta: int) -> bool:
    other = rank_index + delta
    return 0 <= other < 9 and counts[suit_start + other] > 0


def _is_isolated(hand: Hand, tile_id: int) -> bool:
    counts = hand.counts
    suit_start = tile_id // 9 * 9
    rank_index = tile_id % 9
    if counts[tile_id] != 1:
        return False
    for delta in (-2, -1, 1, 2):
        other = rank_index + delta
        if 0 <= other < 9 and counts[suit_start + other] > 0:
            return False
    return True
