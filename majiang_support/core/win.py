from __future__ import annotations

from functools import lru_cache

from majiang_support.core.hand import Hand
from majiang_support.core.meld import Meld
from majiang_support.core.shanten import calculate_seven_pairs_shanten, calculate_standard_shanten


def can_standard_win(hand: Hand) -> bool:
    if hand.size % 3 != 2:
        return False
    for pair_id, count in enumerate(hand.counts):
        if count >= 2:
            counts = list(hand.counts)
            counts[pair_id] -= 2
            if _can_form_melds(tuple(counts)):
                return True
    return False


def can_win_with_missing_suit(hand: Hand, missing_suit: str | None) -> bool:
    if missing_suit and hand.has_suit(missing_suit):
        return False
    return can_standard_win(hand)


def can_win(
    hand: Hand,
    missing_suit: str | None = None,
    open_melds: tuple[Meld, ...] = (),
) -> bool:
    if missing_suit:
        if hand.has_suit(missing_suit):
            return False
        if any(meld.tile.suit == missing_suit for meld in open_melds):
            return False

    open_count = len(open_melds)
    if calculate_standard_shanten(hand, open_meld_count=open_count) == -1:
        return True
    return open_count == 0 and calculate_seven_pairs_shanten(hand) == -1


@lru_cache(maxsize=None)
def _can_form_melds(counts: tuple[int, ...]) -> bool:
    first = next((index for index, count in enumerate(counts) if count), None)
    if first is None:
        return True

    mutable = list(counts)
    if mutable[first] >= 3:
        mutable[first] -= 3
        if _can_form_melds(tuple(mutable)):
            return True
        mutable[first] += 3

    suit_start = first // 9 * 9
    rank = first % 9
    if rank <= 6 and first + 2 < suit_start + 9:
        if mutable[first + 1] > 0 and mutable[first + 2] > 0:
            mutable[first] -= 1
            mutable[first + 1] -= 1
            mutable[first + 2] -= 1
            if _can_form_melds(tuple(mutable)):
                return True

    return False
