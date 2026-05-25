from __future__ import annotations

from majiang_support.core.hand import Hand


def evaluate_structure(hand: Hand) -> int:
    counts = list(hand.counts)
    score = 0

    for tile_id, count in enumerate(counts):
        if count >= 3:
            score += 8
        elif count == 2:
            score += 5

    for suit_start in (0, 9, 18):
        suit_counts = counts[suit_start : suit_start + 9]
        for index in range(7):
            if suit_counts[index] and suit_counts[index + 1] and suit_counts[index + 2]:
                score += 8
        for index in range(8):
            if suit_counts[index] and suit_counts[index + 1]:
                score += 4 if 1 <= index <= 5 else 1
        for index in range(7):
            if suit_counts[index] and suit_counts[index + 2]:
                score += 2

    for tile_id, count in enumerate(counts):
        if count != 1:
            continue
        rank = tile_id % 9 + 1
        if _is_isolated(counts, tile_id):
            score += 0 if 2 <= rank <= 8 else -1

    return score


def _is_isolated(counts: list[int], tile_id: int) -> bool:
    suit_start = tile_id // 9 * 9
    rank_index = tile_id % 9
    for delta in (-2, -1, 1, 2):
        other_rank = rank_index + delta
        if 0 <= other_rank < 9 and counts[suit_start + other_rank] > 0:
            return False
    return True

