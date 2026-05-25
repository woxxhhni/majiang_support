from __future__ import annotations

from dataclasses import dataclass

from majiang_support.core.effective import EffectiveTiles, calculate_effective_tiles
from majiang_support.core.hand import Hand
from majiang_support.core.shanten import calculate_standard_shanten
from majiang_support.core.tile import Tile
from majiang_support.strategy.structure import evaluate_structure


@dataclass(frozen=True)
class DiscardCandidate:
    tile_id: int
    score: int
    shanten: int
    effective: EffectiveTiles
    structure_score: int
    reasons: tuple[str, ...]

    @property
    def tile(self) -> Tile:
        return Tile.from_id(self.tile_id)


@dataclass(frozen=True)
class Recommendation:
    best: DiscardCandidate
    candidates: tuple[DiscardCandidate, ...]
    missing_suit_active: bool


def recommend_discard(hand: Hand, missing_suit: str | None = None) -> Recommendation:
    if hand.size not in {2, 5, 8, 11, 14}:
        raise ValueError("出牌推荐需要 14 张手牌，或包含副露后的 3n+2 张手牌")

    discard_ids = hand.candidate_discards(missing_suit)
    missing_active = bool(missing_suit and hand.has_suit(missing_suit))
    candidates = [
        _score_discard(hand, tile_id, missing_suit if missing_active else None, missing_active)
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
                -item.tile_id,
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
) -> DiscardCandidate:
    after = hand.remove(tile_id)
    shanten = calculate_standard_shanten(after)
    effective = calculate_effective_tiles(after, forbidden_suit=forbidden_suit)
    structure_score = evaluate_structure(after)
    score = -100 * shanten + effective.remaining_total + structure_score
    reasons = _build_reasons(hand, tile_id, shanten, effective, structure_score, missing_active)
    return DiscardCandidate(
        tile_id=tile_id,
        score=score,
        shanten=shanten,
        effective=effective,
        structure_score=structure_score,
        reasons=tuple(reasons),
    )


def _build_reasons(
    hand: Hand,
    tile_id: int,
    shanten: int,
    effective: EffectiveTiles,
    structure_score: int,
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

    reasons.append(f"打出后向听数为 {shanten}")
    reasons.append(f"有效进张剩余 {effective.remaining_total} 张")
    reasons.append(f"保留结构评分为 {structure_score}")
    return reasons


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
