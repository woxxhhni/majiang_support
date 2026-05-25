from majiang_support.core.hand import Hand
from majiang_support.strategy.discard import recommend_discard


def test_missing_suit_discards_are_forced():
    hand = Hand.parse("1m 2m 3m 5m 6m 8m 8m 2p 3p 4p 6s 7s 9s 9s")

    recommendation = recommend_discard(hand, "p")

    assert recommendation.missing_suit_active is True
    assert {candidate.tile.suit for candidate in recommendation.candidates} == {"p"}
    for candidate in recommendation.candidates:
        assert all("筒" not in label for label in candidate.effective.labels)


def test_recommend_discard_returns_sorted_candidates():
    hand = Hand.parse("1m 2m 3m 5m 6m 8m 8m 2p 3p 4p 6s 7s 9s 9s")

    recommendation = recommend_discard(hand, None)
    scores = [candidate.score for candidate in recommendation.candidates]

    assert scores == sorted(scores, reverse=True)
    assert recommendation.best.tile_id == recommendation.candidates[0].tile_id
