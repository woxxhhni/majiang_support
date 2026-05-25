import pytest

from majiang_support.core.tile import Tile, parse_suit, parse_tiles


def test_parse_suited_tiles():
    tiles = parse_tiles("1m 2p 3s")

    assert [tile.label for tile in tiles] == ["1万", "2筒", "3条"]


def test_reject_honor_tiles_for_sichuan_blood_battle():
    with pytest.raises(ValueError, match="不使用字牌"):
        Tile.parse("东")


def test_parse_suit_aliases():
    assert parse_suit("万") == "m"
    assert parse_suit("p") == "p"
