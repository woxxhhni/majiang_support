from majiang_support.app.web import _dingque_to_dict, _recommendation_to_dict
from majiang_support.app.web import _action_recommendation_to_dict
from majiang_support.core.hand import Hand
from majiang_support.core.tile import Tile
from majiang_support.strategy.action import recommend_action_after_discard
from majiang_support.strategy.dingque import recommend_dingque
from majiang_support.strategy.discard import recommend_discard


def test_web_recommendation_payload_contains_display_fields():
    hand = Hand.parse("1m 2m 3m 5m 6m 8m 8m 2p 3p 4p 6s 7s 9s 9s")
    recommendation = recommend_discard(hand, "p")

    payload = _recommendation_to_dict(recommendation)

    assert payload["best"]["label"] == "2筒"
    assert payload["missing_suit_active"] is True
    assert payload["candidates"][0]["effective_count"] >= 0
    assert payload["candidates"][0]["best_route"]["label"]
    assert payload["candidates"][0]["routes"]
    assert payload["best"]["reasons"]


def test_web_dingque_payload_contains_display_fields():
    hand = Hand.parse("1m 9m 2p 3p 4p 5p 6p 7p 1s 2s 3s 7s 8s 9s")
    recommendation = recommend_dingque(hand)

    payload = _dingque_to_dict(recommendation)

    assert payload["best"]["label"] == "万"
    assert payload["candidates"][0]["score"] <= payload["candidates"][-1]["score"]


def test_web_action_payload_contains_display_fields():
    hand = Hand.parse("1m 1m 2m 3m 4m 5m 6m 7m 8m 2p 3p 4p 6s")
    recommendation = recommend_action_after_discard(hand, Tile.parse("1m").id)

    payload = _action_recommendation_to_dict(recommendation)

    assert payload["best"]["label"]
    assert payload["candidates"]
    assert "delta" in payload["best"]
