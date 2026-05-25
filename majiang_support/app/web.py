from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from majiang_support.core.hand import Hand
from majiang_support.core.meld import Meld
from majiang_support.core.tile import Tile, parse_suit
from majiang_support.core.win import can_win
from majiang_support.strategy.action import recommend_action_after_discard, recommend_action_after_draw
from majiang_support.strategy.dingque import recommend_dingque
from majiang_support.strategy.discard import recommend_discard
from majiang_support.vision.detector import detect_screenshot_regions


STATIC_DIR = Path(__file__).resolve().parent.parent / "web"


class MahjongWebHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self) -> None:
        if self.path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self) -> None:
        if self.path == "/api/recommend":
            self._handle_recommend()
            return
        if self.path == "/api/recommend-dingque":
            self._handle_recommend_dingque()
            return
        if self.path == "/api/detect-screenshot":
            self._handle_detect_screenshot()
            return
        if self.path == "/api/recommend-action":
            self._handle_recommend_action()
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def _handle_recommend(self) -> None:
        try:
            payload = self._read_json_body()
            hand_text = " ".join(str(tile) for tile in payload.get("hand", []))
            missing_suit = parse_suit(payload.get("missing"))
            open_melds = _parse_open_melds(payload.get("melds", []))
            visible_counts = _parse_visible_counts(payload.get("discards", []))
            hand = Hand.parse(hand_text)
            if hand.size + 3 * len(open_melds) == 14 and can_win(hand, missing_suit, open_melds):
                self._send_json(_winning_hand_to_dict(hand, open_melds))
                return
            recommendation = recommend_discard(
                hand,
                missing_suit,
                open_melds=open_melds,
                visible_counts=visible_counts,
            )
            self._send_json(_recommendation_to_dict(recommendation))
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def _handle_recommend_dingque(self) -> None:
        try:
            payload = self._read_json_body()
            hand_text = " ".join(str(tile) for tile in payload.get("hand", []))
            hand = Hand.parse(hand_text)
            recommendation = recommend_dingque(hand)
            self._send_json(_dingque_to_dict(recommendation))
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def _handle_detect_screenshot(self) -> None:
        try:
            payload = self._read_json_body()
            image_data = payload.get("image")
            if not image_data:
                raise ValueError("缺少截图数据")
            self._send_json(detect_screenshot_regions(str(image_data), hand_captures=payload.get("hand_captures")))
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def _handle_recommend_action(self) -> None:
        try:
            payload = self._read_json_body()
            hand_text = " ".join(str(tile) for tile in payload.get("hand", []))
            hand = Hand.parse(hand_text)
            open_melds = _parse_open_melds(payload.get("melds", []))
            visible_counts = _parse_visible_counts(payload.get("discards", []))
            missing_suit = parse_suit(payload.get("missing"))
            scene = payload.get("scene")
            if scene == "after_discard":
                incoming = Tile.parse(str(payload.get("incoming")))
                recommendation = recommend_action_after_discard(
                    hand,
                    incoming.id,
                    missing_suit,
                    open_melds=open_melds,
                    visible_counts=visible_counts,
                )
            elif scene == "after_draw":
                recommendation = recommend_action_after_draw(
                    hand,
                    missing_suit,
                    open_melds=open_melds,
                    visible_counts=visible_counts,
                )
            else:
                raise ValueError("未知动作场景")
            self._send_json(_action_recommendation_to_dict(recommendation))
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def _read_json_body(self) -> dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length).decode("utf-8")
        return json.loads(raw_body)

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def translate_path(self, path: str) -> str:
        path = unquote(path.split("?", 1)[0].split("#", 1)[0])
        if path == "/":
            path = "/index.html"
        return str(STATIC_DIR / path.lstrip("/"))


def _recommendation_to_dict(recommendation: Any) -> dict[str, Any]:
    return {
        "best": _candidate_to_dict(recommendation.best),
        "missing_suit_active": recommendation.missing_suit_active,
        "candidates": [_candidate_to_dict(candidate) for candidate in recommendation.candidates],
    }


def _winning_hand_to_dict(hand: Hand, open_melds: tuple[Meld, ...]) -> dict[str, Any]:
    return {
        "won": True,
        "label": "已经胡了",
        "hand": hand.labels(),
        "melds": [_meld_to_dict(meld) for meld in open_melds],
        "message": "这副牌已经是胡牌形，不需要再推荐打哪张。",
    }


def _meld_to_dict(meld: Meld) -> dict[str, Any]:
    return {
        "kind": meld.kind,
        "label": meld.tile.label,
    }


def _parse_open_melds(raw_melds: Any) -> tuple[Meld, ...]:
    if not raw_melds:
        return ()

    melds = []
    for raw in raw_melds:
        if not isinstance(raw, dict):
            raise ValueError("副露数据格式不正确")
        kind = str(raw.get("kind", "")).strip()
        if kind not in {"pong", "open_kong", "concealed_kong", "added_kong"}:
            raise ValueError(f"未知副露类型: {kind}")
        tile = Tile.parse(str(raw.get("tile", "")))
        melds.append(Meld(kind=kind, tile_id=tile.id))
    return tuple(melds)


def _parse_visible_counts(raw_tiles: Any) -> tuple[int, ...]:
    counts = [0] * 27
    for raw in raw_tiles or []:
        tile = Tile.parse(str(raw))
        counts[tile.id] += 1
        if counts[tile.id] > 4:
            raise ValueError(f"{tile.label} 已打出数量超过 4 张")
    return tuple(counts)


def _candidate_to_dict(candidate: Any) -> dict[str, Any]:
    return {
        "tile": str(candidate.tile),
        "label": candidate.tile.label,
        "score": candidate.score,
        "shanten": candidate.shanten,
        "standard_shanten": candidate.standard_shanten,
        "seven_pairs_shanten": candidate.seven_pairs_shanten,
        "effective_count": candidate.effective.remaining_total,
        "effective_tiles": candidate.effective.labels,
        "tenpai_count": candidate.tenpai.remaining_total,
        "tenpai_tiles": candidate.tenpai.labels,
        "structure_score": candidate.structure_score,
        "discard_value": candidate.discard_value,
        "ev": round(candidate.ev, 6),
        "best_route": _route_to_dict(candidate.best_route),
        "routes": [_route_to_dict(route) for route in candidate.routes],
        "reasons": list(candidate.reasons),
    }


def _route_to_dict(route: Any) -> dict[str, Any]:
    return {
        "name": route.name,
        "label": route.label,
        "target_suit": route.target_suit,
        "shanten": route.shanten,
        "fan": route.fan,
        "effective_count": route.effective.remaining_total,
        "effective_tiles": route.effective.labels,
        "probability": round(route.probability, 6),
        "ev": round(route.ev, 6),
    }


def _dingque_to_dict(recommendation: Any) -> dict[str, Any]:
    return {
        "best": _dingque_candidate_to_dict(recommendation.best),
        "candidates": [_dingque_candidate_to_dict(candidate) for candidate in recommendation.candidates],
    }


def _dingque_candidate_to_dict(candidate: Any) -> dict[str, Any]:
    return {
        "suit": candidate.suit,
        "label": candidate.label,
        "score": candidate.score,
        "tile_count": candidate.tile_count,
        "structure_value": candidate.structure_value,
        "reasons": list(candidate.reasons),
    }


def _action_recommendation_to_dict(recommendation: Any) -> dict[str, Any]:
    return {
        "best": _action_candidate_to_dict(recommendation.best),
        "candidates": [_action_candidate_to_dict(candidate) for candidate in recommendation.candidates],
    }


def _action_candidate_to_dict(candidate: Any) -> dict[str, Any]:
    return {
        "action": candidate.action,
        "label": candidate.label,
        "ev_before": round(candidate.ev_before, 6),
        "ev_after": round(candidate.ev_after, 6),
        "delta": round(candidate.delta, 6),
        "route": _route_to_dict(candidate.route),
        "discard": _recommendation_to_dict(candidate.discard) if candidate.discard else None,
        "reasons": list(candidate.reasons),
    }


def main() -> None:
    parser = argparse.ArgumentParser(prog="majiang-web")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), MahjongWebHandler)
    print(f"Mahjong Support web UI: http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
