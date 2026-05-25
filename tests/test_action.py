from majiang_support.core.hand import Hand
from majiang_support.core.meld import Meld
from majiang_support.core.tile import Tile
from majiang_support.strategy.action import recommend_action_after_discard, recommend_action_after_draw
from majiang_support.strategy.ev import evaluate_routes
from majiang_support.core.remaining import remaining_counts_for_waiting


def test_pong_candidate_exists_for_13_tile_hand():
    hand = Hand.parse("1m 1m 2m 3m 4m 5m 6m 7m 8m 2p 3p 4p 6s")
    incoming = Tile.parse("1m")

    recommendation = recommend_action_after_discard(hand, incoming.id)

    assert {candidate.action for candidate in recommendation.candidates} >= {"pass", "pong"}


def test_open_meld_disables_seven_pairs_route():
    hand = Hand.parse("1m 1m 2m 2m 4m 4m 6p 6p 8p 8p 3s")
    melds = (Meld("pong", Tile.parse("3s").id),)

    routes = evaluate_routes(hand, remaining_counts_for_waiting(hand, melds=melds), open_melds=melds)
    seven_pairs = next(route for route in routes if route.name == "七对")

    assert seven_pairs.ev == 0
    assert seven_pairs.shanten == 99


def test_concealed_kong_candidate_exists_after_draw():
    hand = Hand.parse("1m 1m 1m 1m 2m 3m 4m 5p 6p 7p 2s 3s 4s 8s")

    recommendation = recommend_action_after_draw(hand)

    assert "concealed_kong" in {candidate.action for candidate in recommendation.candidates}
