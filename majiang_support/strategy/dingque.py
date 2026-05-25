from __future__ import annotations

from dataclasses import dataclass

from majiang_support.core.hand import Hand
from majiang_support.core.tile import SUIT_LABELS


@dataclass(frozen=True)
class DingQueCandidate:
    suit: str
    score: int
    tile_count: int
    structure_value: int
    reasons: tuple[str, ...]

    @property
    def label(self) -> str:
        return SUIT_LABELS[self.suit]


@dataclass(frozen=True)
class DingQueRecommendation:
    best: DingQueCandidate
    candidates: tuple[DingQueCandidate, ...]


def recommend_dingque(hand: Hand) -> DingQueRecommendation:
    candidates = tuple(_score_suit(hand, suit) for suit in ("m", "p", "s"))
    ordered = tuple(sorted(candidates, key=lambda item: (item.score, item.tile_count, item.structure_value)))
    return DingQueRecommendation(best=ordered[0], candidates=ordered)


def _score_suit(hand: Hand, suit: str) -> DingQueCandidate:
    start = {"m": 0, "p": 9, "s": 18}[suit]
    counts = list(hand.counts[start : start + 9])
    tile_count = sum(counts)
    structure_value = _structure_value(counts)
    score = tile_count * 100 + structure_value
    reasons = _build_reasons(suit, counts, tile_count, structure_value)
    return DingQueCandidate(
        suit=suit,
        score=score,
        tile_count=tile_count,
        structure_value=structure_value,
        reasons=tuple(reasons),
    )


def _structure_value(counts: list[int]) -> int:
    value = 0

    for index, count in enumerate(counts):
        rank = index + 1
        if count >= 3:
            value += 45
        elif count == 2:
            value += 24
        elif count == 1:
            value += 8 if 3 <= rank <= 7 else 4

    for index in range(7):
        if counts[index] and counts[index + 1] and counts[index + 2]:
            value += 38

    for index in range(8):
        if counts[index] and counts[index + 1]:
            value += 20 if 1 <= index <= 5 else 10

    for index in range(7):
        if counts[index] and counts[index + 2]:
            value += 12

    return value


def _build_reasons(suit: str, counts: list[int], tile_count: int, structure_value: int) -> list[str]:
    label = SUIT_LABELS[suit]
    reasons: list[str] = []

    if tile_count == 0:
        return [f"手里没有{label}，定缺{label}成本最低"]

    reasons.append(f"{label}共 {tile_count} 张")

    pairs = sum(1 for count in counts if count == 2)
    triplets = sum(1 for count in counts if count >= 3)
    sequences = sum(1 for index in range(7) if counts[index] and counts[index + 1] and counts[index + 2])
    adjacent = sum(1 for index in range(8) if counts[index] and counts[index + 1])
    isolated = [
        index + 1
        for index, count in enumerate(counts)
        if count == 1 and _is_isolated(counts, index)
    ]

    if triplets:
        reasons.append(f"已有 {triplets} 组刻子，放弃成本较高")
    if sequences:
        reasons.append(f"已有 {sequences} 组顺子，放弃成本较高")
    if pairs:
        reasons.append(f"有 {pairs} 个对子，保留价值增加")
    if adjacent:
        reasons.append(f"有 {adjacent} 个相邻搭子")
    if isolated:
        reasons.append(f"孤张较多：{','.join(str(rank) for rank in isolated)}{label}")

    reasons.append(f"放弃成本评分 {structure_value}，越低越适合定缺")
    return reasons


def _is_isolated(counts: list[int], index: int) -> bool:
    for delta in (-2, -1, 1, 2):
        other = index + delta
        if 0 <= other < 9 and counts[other] > 0:
            return False
    return True

