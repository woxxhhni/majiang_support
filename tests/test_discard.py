from majiang_support.core.hand import Hand
from majiang_support.core.remaining import remaining_counts_after_discard
from majiang_support.core.tile import Tile
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
            candidate.score,
            -candidate.shanten,
            candidate.effective.remaining_total,
            candidate.structure_score,
            -candidate.discard_value,
            candidate.ev,
            candidate.tile_id,
        )
        for candidate in recommendation.candidates
    ]

    assert priorities == sorted(priorities, reverse=True)
    assert recommendation.best.tile_id == recommendation.candidates[0].tile_id


def test_recommend_discard_keeps_seven_pairs_route():
    hand = Hand.parse("1m 1m 2m 2m 4m 4m 6p 6p 8p 8p 3s 3s 5s 7s")

    recommendation = recommend_discard(hand, None)

    assert recommendation.best.tile.label == "7条"
    assert recommendation.best.best_route.name == "七对"
    assert recommendation.best.seven_pairs_shanten == 0
    assert recommendation.best.standard_shanten > recommendation.best.seven_pairs_shanten


def test_effective_tiles_do_not_count_discarded_tile_as_remaining():
    hand = Hand.parse("1m 1m 2m 3m 4m 5m 6m 7m 8m 2p 3p 4p 5s 6s")

    recommendation = recommend_discard(hand, None)
    candidate = next(item for item in recommendation.candidates if item.tile.label == "5条")

    assert candidate.effective.remaining_total == 45


def test_remaining_counts_after_discard_use_original_hand_counts():
    hand = Hand.parse("1m 1m 2m 3m 4m 5m 6m 7m 8m 2p 3p 4p 5s 6s")
    remaining = remaining_counts_after_discard(hand, 22)

    assert remaining[22] == 3
    assert remaining[0] == 2


def test_recommend_discard_prioritizes_shanten_before_route_ev():
    hand = Hand.parse("1m 4m 5m 7m 7m 9m 9m 1p 3p 3p 4p 5p 5p 9p")

    recommendation = recommend_discard(hand, None)

    assert recommendation.best.tile.label == "9筒"
    assert recommendation.best.shanten == 2
    assert all(candidate.tile.label != "4万" for candidate in recommendation.candidates[:2])


def test_visible_discards_reduce_effective_tiles():
    hand = Hand.parse("1m 4m 5m 7m 7m 9m 9m 1p 3p 3p 4p 5p 5p 9p")
    visible = [0] * 27
    visible[Tile.parse("1m").id] = 3

    recommendation = recommend_discard(hand, None, visible_counts=tuple(visible))
    discard_9p = next(candidate for candidate in recommendation.candidates if str(candidate.tile) == "9p")

    assert Tile.parse("1m").id not in discard_9p.effective.tile_ids


def test_visible_discards_do_not_inflate_route_ev():
    hand = Hand.parse("2p 2p 4p 5p 6p 6p 6p 7p 9p 9p 1s 1s 8s 8s")
    visible = [0] * 27
    for tile in ("8s", "8s", "1s", "1s", "6p"):
        visible[Tile.parse(tile).id] += 1

    base = recommend_discard(hand, None)
    with_visible = recommend_discard(hand, None, visible_counts=tuple(visible))

    for candidate in with_visible.candidates:
        base_candidate = next(item for item in base.candidates if item.tile_id == candidate.tile_id)
        assert candidate.ev <= base_candidate.ev
