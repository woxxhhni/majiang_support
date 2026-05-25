from __future__ import annotations

from dataclasses import dataclass

from majiang_support.core.hand import Hand, all_suited_tile_ids
from majiang_support.core.shanten import calculate_best_shanten
from majiang_support.core.tile import tile_label


@dataclass(frozen=True)
class EffectiveTiles:
    tile_ids: tuple[int, ...]
    remaining_total: int

    @property
    def labels(self) -> list[str]:
        return [tile_label(tile_id) for tile_id in self.tile_ids]


def calculate_effective_tiles(
    hand: Hand,
    remaining_counts: tuple[int, ...] | None = None,
    forbidden_suit: str | None = None,
) -> EffectiveTiles:
    base_shanten = calculate_best_shanten(hand)
    remaining = remaining_counts or hand.remaining_counts_without_visible()
    useful: list[int] = []
    total = 0

    for tile_id in all_suited_tile_ids():
        if forbidden_suit and tile_id // 9 == {"m": 0, "p": 1, "s": 2}[forbidden_suit]:
            continue
        if remaining[tile_id] <= 0 or hand.count(tile_id) >= 4:
            continue
        next_hand = hand.add(tile_id)
        if calculate_best_shanten(next_hand) < base_shanten:
            useful.append(tile_id)
            total += remaining[tile_id]

    return EffectiveTiles(tuple(useful), total)
