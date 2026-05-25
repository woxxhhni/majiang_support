from majiang_support.core.hand import Hand
from majiang_support.strategy.dingque import recommend_dingque


def test_recommend_dingque_prefers_empty_suit():
    hand = Hand.parse("1m 2m 3m 5m 6m 8m 8m 1p 2p 3p 7p 8p 9p 9p")

    recommendation = recommend_dingque(hand)

    assert recommendation.best.suit == "s"


def test_recommend_dingque_uses_structure_not_only_count():
    hand = Hand.parse("1m 9m 2p 3p 4p 5p 6p 7p 1s 2s 3s 7s 8s 9s")

    recommendation = recommend_dingque(hand)

    assert recommendation.best.suit == "m"
    assert recommendation.best.tile_count == 2
