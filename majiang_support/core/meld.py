from __future__ import annotations

from dataclasses import dataclass

from majiang_support.core.tile import Tile


@dataclass(frozen=True)
class Meld:
    kind: str
    tile_id: int

    @property
    def tile(self) -> Tile:
        return Tile.from_id(self.tile_id)

    @property
    def is_triplet_like(self) -> bool:
        return self.kind in {"pong", "open_kong", "concealed_kong", "added_kong"}

