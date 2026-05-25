from __future__ import annotations

from dataclasses import dataclass


SUIT_LABELS = {
    "m": "万",
    "p": "筒",
    "s": "条",
}

CHINESE_SUIT_ALIASES = {
    "万": "m",
    "萬": "m",
    "筒": "p",
    "饼": "p",
    "餅": "p",
    "条": "s",
    "條": "s",
    "索": "s",
}

SUIT_ORDER = {"m": 0, "p": 1, "s": 2}
ALL_TILE_IDS = tuple(range(27))


@dataclass(frozen=True, order=True)
class Tile:
    """A suited Sichuan Mahjong tile.

    Sichuan blood-battle rules use only 1-9 of characters, dots, and bamboos.
    Wind, dragon, and flower tiles are intentionally rejected by the parser.
    """

    suit: str
    rank: int

    def __post_init__(self) -> None:
        if self.suit not in SUIT_ORDER:
            raise ValueError(f"Unsupported suit: {self.suit}")
        if self.rank < 1 or self.rank > 9:
            raise ValueError(f"Tile rank must be 1-9: {self.rank}")

    @property
    def id(self) -> int:
        return SUIT_ORDER[self.suit] * 9 + self.rank - 1

    @classmethod
    def from_id(cls, tile_id: int) -> "Tile":
        if tile_id < 0 or tile_id >= 27:
            raise ValueError(f"Tile id must be 0-26: {tile_id}")
        suit_index, rank_index = divmod(tile_id, 9)
        suit = ("m", "p", "s")[suit_index]
        return cls(suit=suit, rank=rank_index + 1)

    @classmethod
    def parse(cls, value: str) -> "Tile":
        token = value.strip()
        if not token:
            raise ValueError("Empty tile token")

        normalized = token.lower()
        if len(normalized) == 2 and normalized[0].isdigit():
            return cls(suit=normalized[1], rank=int(normalized[0]))

        if len(token) >= 2 and token[0].isdigit():
            suit = CHINESE_SUIT_ALIASES.get(token[1:])
            if suit:
                return cls(suit=suit, rank=int(token[0]))

        if token in {"东", "南", "西", "北", "中", "发", "白", "E", "S", "W", "N", "C", "F", "P"}:
            raise ValueError("四川血战到底默认只使用万、筒、条三门牌，不使用字牌")

        raise ValueError(f"Cannot parse tile: {value}")

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"

    @property
    def label(self) -> str:
        return f"{self.rank}{SUIT_LABELS[self.suit]}"


def parse_tiles(text: str) -> list[Tile]:
    tokens = text.replace(",", " ").replace("，", " ").split()
    return [Tile.parse(token) for token in tokens]


def tile_label(tile_id: int) -> str:
    return Tile.from_id(tile_id).label


def parse_suit(value: str | None) -> str | None:
    if value is None:
        return None
    token = value.strip().lower()
    if not token:
        return None
    if token in SUIT_ORDER:
        return token
    if token in CHINESE_SUIT_ALIASES:
        return CHINESE_SUIT_ALIASES[token]
    raise ValueError(f"Unknown suit: {value}")

