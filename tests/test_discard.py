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
    priorities = [
        (
            -candidate.shanten,
            candidate.effective.remaining_total,
            candidate.structure_score,
            -candidate.discard_value,
            candidate.score,
            -candidate.tile_id,
        )
        for candidate in recommendation.candidates
    ]

    assert priorities == sorted(priorities, reverse=True)
    assert recommendation.best.tile_id == recommendation.candidates[0].tile_id


def test_recommend_discard_keeps_seven_pairs_route():
    hand = Hand.parse("1m 1m 2m 2m 4m 4m 6p 6p 8p 8p 3s 3s 5s 7s")

    recommendation = recommend_discard(hand, None)

    assert recommendation.best.tile.label == "7条"
    assert recommendation.best.seven_pairs_shanten == 0
    assert recommendation.best.standard_shanten > recommendation.best.seven_pairs_shanten


def test_effective_tiles_do_not_count_discarded_tile_as_remaining():
    hand = Hand.parse("1m 1m 2m 3m 4m 5m 6m 7m 8m 2p 3p 4p 5s 6s")

    recommendation = recommend_discard(hand, None)
    candidate = next(item for item in recommendation.candidates if item.tile.label == "5条")

    assert candidate.effective.remaining_total == 44
