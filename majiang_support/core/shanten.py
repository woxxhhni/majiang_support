from __future__ import annotations

from functools import lru_cache

from majiang_support.core.hand import Hand


def calculate_standard_shanten(hand: Hand) -> int:
    """Return standard hand shanten.

    A complete 14-tile winning hand returns -1. A ready 13-tile hand returns 0.
    """

    best = 8
    counts = hand.counts

    for pair_id in range(27):
        if counts[pair_id] >= 2:
            mutable = list(counts)
            mutable[pair_id] -= 2
            melds, taatsu = _best_blocks(tuple(mutable))
            best = min(best, _shanten_from_blocks(melds, taatsu, has_pair=True))

    melds, taatsu = _best_blocks(counts)
    best = min(best, _shanten_from_blocks(melds, taatsu, has_pair=False))
    return best


def calculate_seven_pairs_shanten(hand: Hand) -> int:
    """Return seven-pairs shanten.

    A complete seven-pairs hand returns -1. A ready 13-tile hand returns 0.
    """

    pairs = sum(1 for count in hand.counts if count >= 2)
    unique_tiles = sum(1 for count in hand.counts if count > 0)
    missing_unique = max(0, 7 - unique_tiles)
    return 6 - pairs + missing_unique


def calculate_best_shanten(hand: Hand) -> int:
    return min(calculate_standard_shanten(hand), calculate_seven_pairs_shanten(hand))


def _shanten_from_blocks(melds: int, taatsu: int, has_pair: bool) -> int:
    if melds + taatsu > 4:
        taatsu = 4 - melds
    return 8 - 2 * melds - taatsu - (1 if has_pair else 0)


@lru_cache(maxsize=None)
def _best_blocks(counts: tuple[int, ...]) -> tuple[int, int]:
    best = (0, 0)

    def better(left: tuple[int, int], right: tuple[int, int]) -> tuple[int, int]:
        left_value = left[0] * 2 + left[1]
        right_value = right[0] * 2 + right[1]
        if right_value > left_value:
            return right
        if right_value == left_value and right[0] > left[0]:
            return right
        return left

    first = next((index for index, count in enumerate(counts) if count), None)
    if first is None:
        return best

    mutable = list(counts)

    if mutable[first] >= 3:
        mutable[first] -= 3
        melds, taatsu = _best_blocks(tuple(mutable))
        best = better(best, (melds + 1, taatsu))
        mutable[first] += 3

    rank = first % 9
    if rank <= 6 and mutable[first + 1] > 0 and mutable[first + 2] > 0:
        mutable[first] -= 1
        mutable[first + 1] -= 1
        mutable[first + 2] -= 1
        melds, taatsu = _best_blocks(tuple(mutable))
        best = better(best, (melds + 1, taatsu))
        mutable[first] += 1
        mutable[first + 1] += 1
        mutable[first + 2] += 1

    if mutable[first] >= 2:
        mutable[first] -= 2
        melds, taatsu = _best_blocks(tuple(mutable))
        best = better(best, (melds, taatsu + 1))
        mutable[first] += 2

    if rank <= 7 and mutable[first + 1] > 0:
        mutable[first] -= 1
        mutable[first + 1] -= 1
        melds, taatsu = _best_blocks(tuple(mutable))
        best = better(best, (melds, taatsu + 1))
        mutable[first] += 1
        mutable[first + 1] += 1

    if rank <= 6 and mutable[first + 2] > 0:
        mutable[first] -= 1
        mutable[first + 2] -= 1
        melds, taatsu = _best_blocks(tuple(mutable))
        best = better(best, (melds, taatsu + 1))
        mutable[first] += 1
        mutable[first + 2] += 1

    mutable[first] -= 1
    best = better(best, _best_blocks(tuple(mutable)))
    return best
