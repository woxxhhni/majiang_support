from majiang_support.core.effective import calculate_effective_tiles
from majiang_support.core.hand import Hand
from majiang_support.core.shanten import calculate_standard_shanten


def test_complete_hand_has_negative_one_shanten():
    hand = Hand.parse("1m 2m 3m 2p 3p 4p 5s 6s 7s 7m 8m 9m 9s 9s")

    assert calculate_standard_shanten(hand) == -1


def test_ready_hand_has_zero_shanten():
    hand = Hand.parse("1m 2m 3m 2p 3p 4p 5s 6s 7s 7m 8m 9m 9s")

    assert calculate_standard_shanten(hand) == 0


def test_effective_tiles_include_winning_draw():
    hand = Hand.parse("1m 2m 3m 2p 3p 4p 5s 6s 7s 7m 8m 9m 9s")
    effective = calculate_effective_tiles(hand)

    assert "9条" in effective.labels
    assert effective.remaining_total >= 1

