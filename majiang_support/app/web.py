from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from majiang_support.core.hand import Hand
from majiang_support.core.tile import parse_suit
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
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def _handle_recommend(self) -> None:
        try:
            payload = self._read_json_body()
            hand_text = " ".join(str(tile) for tile in payload.get("hand", []))
            missing_suit = parse_suit(payload.get("missing"))
            hand = Hand.parse(hand_text)
            recommendation = recommend_discard(hand, missing_suit)
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
            self._send_json(detect_screenshot_regions(str(image_data)))
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
