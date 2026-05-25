from __future__ import annotations

from dataclasses import dataclass

from majiang_support.core.hand import Hand
from majiang_support.core.meld import Meld
from majiang_support.core.remaining import remaining_counts_for_waiting
from majiang_support.core.tile import Tile
from majiang_support.strategy.discard import Recommendation, recommend_discard
from majiang_support.strategy.ev import RouteEvaluation, evaluate_routes


PONG_EXPOSURE_COST = 0.018
OPEN_KONG_EXPOSURE_COST = 0.025
CONCEALED_KONG_COST = 0.006
OPEN_KONG_IMMEDIATE_VALUE = 0.055
CONCEALED_KONG_IMMEDIATE_VALUE = 0.075
SUPPLEMENT_DRAW_VALUE = 0.035


@dataclass(frozen=True)
class ActionCandidate:
    action: str
    label: str
    ev_before: float
    ev_after: float
    delta: float
    route: RouteEvaluation
    discard: Recommendation | None
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ActionRecommendation:
    best: ActionCandidate
    candidates: tuple[ActionCandidate, ...]


def recommend_action_after_draw(
    hand: Hand,
    missing_suit: str | None = None,
    open_melds: tuple[Meld, ...] = (),
    visible_counts: tuple[int, ...] | None = None,
) -> ActionRecommendation:
    discard_rec = recommend_discard(hand, missing_suit, open_melds=open_melds, visible_counts=visible_counts)
    pass_candidate = ActionCandidate(
        action="discard",
        label=f"直接打 {discard_rec.best.tile.label}",
        ev_before=discard_rec.best.ev,
        ev_after=discard_rec.best.ev,
        delta=0.0,
        route=discard_rec.best.best_route,
        discard=discard_rec,
        reasons=(f"不杠时推荐打 {discard_rec.best.tile.label}", f"当前最佳路线为 {discard_rec.best.best_route.label}"),
    )
    candidates = [pass_candidate]

    for tile_id in hand.unique_tile_ids():
        if hand.count(tile_id) == 4:
            candidates.append(_evaluate_concealed_kong(hand, tile_id, discard_rec.best.ev, missing_suit, open_melds, visible_counts))

    return _rank_actions(candidates)


def recommend_action_after_discard(
    hand: Hand,
    incoming_tile_id: int,
    missing_suit: str | None = None,
    open_melds: tuple[Meld, ...] = (),
    visible_counts: tuple[int, ...] | None = None,
) -> ActionRecommendation:
    before_route = _best_waiting_route(hand, missing_suit, open_melds, visible_counts)
    pass_candidate = ActionCandidate(
        action="pass",
        label="过",
        ev_before=before_route.ev,
        ev_after=before_route.ev,
        delta=0.0,
        route=before_route,
        discard=None,
        reasons=(f"过牌后保持当前 {before_route.label} 路线",),
    )
    candidates = [pass_candidate]

    if missing_suit and Tile.from_id(incoming_tile_id).suit == missing_suit:
        return _rank_actions(candidates)

    if hand.count(incoming_tile_id) >= 2:
        candidates.append(_evaluate_pong(hand, incoming_tile_id, before_route.ev, missing_suit, open_melds, visible_counts))
    if hand.count(incoming_tile_id) >= 3:
        candidates.append(_evaluate_open_kong(hand, incoming_tile_id, before_route.ev, missing_suit, open_melds, visible_counts))

    return _rank_actions(candidates)


def _evaluate_pong(
    hand: Hand,
    tile_id: int,
    ev_before: float,
    missing_suit: str | None,
    open_melds: tuple[Meld, ...],
    visible_counts: tuple[int, ...] | None,
) -> ActionCandidate:
    after = hand.remove(tile_id).remove(tile_id)
    melds = open_melds + (Meld("pong", tile_id),)
    discard_rec = recommend_discard(after, missing_suit, open_melds=melds, visible_counts=visible_counts)
    ev_after = discard_rec.best.ev
    delta = ev_after - ev_before - PONG_EXPOSURE_COST
    tile = Tile.from_id(tile_id)
    return ActionCandidate(
        action="pong",
        label=f"碰 {tile.label}",
        ev_before=ev_before,
        ev_after=ev_after,
        delta=delta,
        route=discard_rec.best.best_route,
        discard=discard_rec,
        reasons=(
            f"碰后推荐打 {discard_rec.best.tile.label}",
            f"碰后最佳路线为 {discard_rec.best.best_route.label}",
            "碰牌会固定一副面子，但会暴露信息并失去七对路线",
        ),
    )


def _evaluate_open_kong(
    hand: Hand,
    tile_id: int,
    ev_before: float,
    missing_suit: str | None,
    open_melds: tuple[Meld, ...],
    visible_counts: tuple[int, ...] | None,
) -> ActionCandidate:
    after = hand.remove(tile_id).remove(tile_id).remove(tile_id)
    melds = open_melds + (Meld("open_kong", tile_id),)
    route = _best_waiting_route(after, missing_suit, melds, visible_counts)
    ev_after = route.ev + OPEN_KONG_IMMEDIATE_VALUE + SUPPLEMENT_DRAW_VALUE - OPEN_KONG_EXPOSURE_COST
    delta = ev_after - ev_before
    tile = Tile.from_id(tile_id)
    return ActionCandidate(
        action="open_kong",
        label=f"明杠 {tile.label}",
        ev_before=ev_before,
        ev_after=ev_after,
        delta=delta,
        route=route,
        discard=None,
        reasons=(
            f"明杠后最佳路线为 {route.label}",
            "杠牌有即时收益和补摸机会",
            "明杠会暴露信息，已扣除小幅暴露成本",
        ),
    )


def _evaluate_concealed_kong(
    hand: Hand,
    tile_id: int,
    ev_before: float,
    missing_suit: str | None,
    open_melds: tuple[Meld, ...],
    visible_counts: tuple[int, ...] | None,
) -> ActionCandidate:
    after = hand.remove(tile_id).remove(tile_id).remove(tile_id).remove(tile_id)
    melds = open_melds + (Meld("concealed_kong", tile_id),)
    route = _best_waiting_route(after, missing_suit, melds, visible_counts)
    ev_after = route.ev + CONCEALED_KONG_IMMEDIATE_VALUE + SUPPLEMENT_DRAW_VALUE - CONCEALED_KONG_COST
    delta = ev_after - ev_before
    tile = Tile.from_id(tile_id)
    return ActionCandidate(
        action="concealed_kong",
        label=f"暗杠 {tile.label}",
        ev_before=ev_before,
        ev_after=ev_after,
        delta=delta,
        route=route,
        discard=None,
        reasons=(
            f"暗杠后最佳路线为 {route.label}",
            "暗杠有即时收益和补摸机会",
            "若当前七对或龙七对潜力很高，仍需谨慎",
        ),
    )


def _best_waiting_route(
    hand: Hand,
    missing_suit: str | None,
    open_melds: tuple[Meld, ...],
    visible_counts: tuple[int, ...] | None,
) -> RouteEvaluation:
    forbidden_suit = missing_suit if missing_suit and hand.has_suit(missing_suit) else None
    routes = evaluate_routes(
        hand,
        remaining_counts_for_waiting(hand, visible_counts=visible_counts, melds=open_melds),
        forbidden_suit=forbidden_suit,
        open_melds=open_melds,
    )
    return routes[0]


def _rank_actions(candidates: list[ActionCandidate]) -> ActionRecommendation:
    ordered = tuple(sorted(candidates, key=lambda item: (item.delta, item.ev_after), reverse=True))
    return ActionRecommendation(best=ordered[0], candidates=ordered)
