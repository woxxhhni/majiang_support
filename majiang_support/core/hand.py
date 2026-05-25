from __future__ import annotations

from dataclasses import dataclass

from majiang_support.core.tile import ALL_TILE_IDS, Tile, parse_tiles


@dataclass(frozen=True)
class Hand:
    counts: tuple[int, ...]

    def __post_init__(self) -> None:
        if len(self.counts) != 27:
            raise ValueError("Hand counts must have 27 entries")
        if any(count < 0 or count > 4 for count in self.counts):
            raise ValueError("Each tile count must be between 0 and 4")

    @classmethod
    def from_tiles(cls, tiles: list[Tile]) -> "Hand":
        counts = [0] * 27
        for tile in tiles:
            counts[tile.id] += 1
            if counts[tile.id] > 4:
                raise ValueError(f"Too many copies of {tile.label}")
        return cls(tuple(counts))

    @classmethod
    def parse(cls, text: str) -> "Hand":
        return cls.from_tiles(parse_tiles(text))

    @property
    def size(self) -> int:
        return sum(self.counts)

    def tiles(self) -> list[Tile]:
        result: list[Tile] = []
        for tile_id, count in enumerate(self.counts):
            result.extend(Tile.from_id(tile_id) for _ in range(count))
        return result

    def unique_tile_ids(self) -> list[int]:
        return [tile_id for tile_id, count in enumerate(self.counts) if count > 0]

    def count(self, tile_id: int) -> int:
        return self.counts[tile_id]

    def add(self, tile_id: int) -> "Hand":
        counts = list(self.counts)
        if counts[tile_id] >= 4:
            raise ValueError(f"Cannot add fifth copy of {Tile.from_id(tile_id).label}")
        counts[tile_id] += 1
        return Hand(tuple(counts))

    def remove(self, tile_id: int) -> "Hand":
        counts = list(self.counts)
        if counts[tile_id] <= 0:
            raise ValueError(f"Tile is not in hand: {Tile.from_id(tile_id).label}")
        counts[tile_id] -= 1
        return Hand(tuple(counts))

    def has_suit(self, suit: str) -> bool:
        start = {"m": 0, "p": 9, "s": 18}[suit]
        return any(self.counts[start + offset] > 0 for offset in range(9))

    def candidate_discards(self, missing_suit: str | None = None) -> list[int]:
        if missing_suit and self.has_suit(missing_suit):
            return [
                tile_id
                for tile_id in self.unique_tile_ids()
                if Tile.from_id(tile_id).suit == missing_suit
            ]
        return self.unique_tile_ids()

    def remaining_counts_without_visible(self) -> tuple[int, ...]:
        return tuple(4 - count for count in self.counts)

    def labels(self) -> list[str]:
        return [tile.label for tile in self.tiles()]


def all_suited_tile_ids() -> tuple[int, ...]:
    return ALL_TILE_IDS

