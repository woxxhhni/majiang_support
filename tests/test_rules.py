from majiang_support.core.hand import Hand
from majiang_support.core.win import can_win_with_missing_suit


def test_standard_win_without_missing_suit_tiles():
    hand = Hand.parse("1m 2m 3m 2p 3p 4p 5s 6s 7s 7m 8m 9m 9s 9s")

    assert can_win_with_missing_suit(hand, "p") is False
    assert can_win_with_missing_suit(hand, None) is True


def test_missing_suit_is_required_to_win():
    hand = Hand.parse("1m 2m 3m 2p 3p 4p 5s 6s 7s 7m 8m 9m 9s 9s")

    assert can_win_with_missing_suit(hand, "s") is False

