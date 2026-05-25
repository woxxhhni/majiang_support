from __future__ import annotations

from majiang_support.core.hand import Hand
from majiang_support.core.meld import Meld


def remaining_counts_after_discard(
    hand_before_discard: Hand,
    discard_tile_id: int,
    visible_counts: tuple[int, ...] | None = None,
    melds: tuple[Meld, ...] = (),
) -> tuple[int, ...]:
    """Return theoretical remaining counts after choosing a discard.

    The hand passed here is the 14-tile hand before discarding. Using the
    original hand counts is intentional: it removes all tiles currently in hand,
    including the copy that is about to be discarded. Later, visible discards and
    melds can be supplied through visible_counts and are subtracted as well.
    """

    visible = visible_counts or (0,) * 27
    counts = []
    for tile_id, hand_count in enumerate(hand_before_discard.counts):
        extra_visible = visible[tile_id]
        extra_visible += sum(_meld_visible_count(meld) for meld in melds if meld.tile_id == tile_id)
        counts.append(max(0, 4 - hand_count - extra_visible))
    return tuple(counts)


def remaining_counts_for_waiting(
    hand: Hand,
    visible_counts: tuple[int, ...] | None = None,
    melds: tuple[Meld, ...] = (),
) -> tuple[int, ...]:
    visible = visible_counts or (0,) * 27
    counts = []
    for tile_id, hand_count in enumerate(hand.counts):
        extra_visible = visible[tile_id]
        extra_visible += sum(_meld_visible_count(meld) for meld in melds if meld.tile_id == tile_id)
        counts.append(max(0, 4 - hand_count - extra_visible))
    return tuple(counts)


def _meld_visible_count(meld: Meld) -> int:
    if meld.kind in {"open_kong", "concealed_kong", "added_kong"}:
        return 4
    return 3
