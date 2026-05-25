from majiang_support.app.web import _recommendation_to_dict
from majiang_support.core.hand import Hand
from majiang_support.strategy.discard import recommend_discard


def test_web_recommendation_payload_contains_display_fields():
    hand = Hand.parse("1m 2m 3m 5m 6m 8m 8m 2p 3p 4p 6s 7s 9s 9s")
    recommendation = recommend_discard(hand, "p")

    payload = _recommendation_to_dict(recommendation)

    assert payload["best"]["label"] == "2筒"
    assert payload["missing_suit_active"] is True
    assert payload["candidates"][0]["effective_count"] >= 0
    assert payload["best"]["reasons"]
