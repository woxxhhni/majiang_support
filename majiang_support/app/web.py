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
from majiang_support.strategy.discard import recommend_discard


STATIC_DIR = Path(__file__).resolve().parent.parent / "web"


class MahjongWebHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self) -> None:
        if self.path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self) -> None:
        if self.path != "/api/recommend":
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length).decode("utf-8")
            payload = json.loads(raw_body)
            hand_text = " ".join(str(tile) for tile in payload.get("hand", []))
            missing_suit = parse_suit(payload.get("missing"))
            hand = Hand.parse(hand_text)
            recommendation = recommend_discard(hand, missing_suit)
            self._send_json(_recommendation_to_dict(recommendation))
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def translate_path(self, path: str) -> str:
        path = unquote(path.split("?", 1)[0].split("#", 1)[0])
        if path == "/":
            path = "/index.html"
        return str(STATIC_DIR / path.lstrip("/"))

    def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


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
        "effective_count": candidate.effective.remaining_total,
        "effective_tiles": candidate.effective.labels,
        "structure_score": candidate.structure_score,
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

