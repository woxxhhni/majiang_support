from __future__ import annotations

import base64
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageOps
import numpy as np


TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "assets" / "templates" / "hand"
TEMPLATE_SIZE = (64, 88)


@dataclass(frozen=True)
class RegionDetection:
    name: str
    tiles: tuple[str, ...]
    box: tuple[int, int, int, int]


def detect_screenshot_regions(data_url: str, hand_captures: list[str] | None = None) -> dict[str, Any]:
    image = _decode_data_url(data_url)
    hand_region = _crop_ratio(image, (0.015, 0.790, 0.940, 0.205))
    discard_region = _crop_ratio(image, (0.245, 0.125, 0.540, 0.610))

    hand_matches = _scan_hand_region(hand_region)
    hand_tiles = [match["tile"] for match in hand_matches]
    if len(hand_tiles) < 8 and hand_captures:
        hand_tiles = _detect_hand_tiles_from_captures(hand_captures)
        hand_matches = []
    discard_tiles = _detect_tiles(discard_region)

    return {
        "hand": {
            "tiles": hand_tiles,
            "matches": hand_matches,
            "box": _ratio_box(image, (0.015, 0.790, 0.940, 0.205)),
        },
        "discards": {
            "tiles": discard_tiles,
            "box": _ratio_box(image, (0.245, 0.125, 0.540, 0.610)),
        },
    }


def _scan_hand_region(image: Image.Image, threshold: float = 0.95) -> list[dict[str, Any]]:
    templates = _load_hand_templates(raw=True)
    region = _prepare_scan_image(image)
    candidates: list[dict[str, Any]] = []

    for tile, template in templates.items():
        for match in _scan_template(region, template):
            if match["score"] >= threshold:
                candidates.append({"tile": tile, **match})

    return _dedupe_template_matches(candidates)


def _detect_hand_tiles_from_captures(captures: list[str]) -> list[str]:
    templates = _load_hand_templates()
    return [_match_hand_tile(_decode_data_url(capture), templates)[0] for capture in captures]


def _detect_hand_tiles(image: Image.Image) -> list[str]:
    try:
        return [_normalize_detector_tile(tile) for tile in _detect_tiles(image)]
    except Exception:
        return []


def _detect_tiles(image: Image.Image) -> list[str]:
    try:
        from mahjong_detector import detect_tiles
    except Exception as exc:  # pragma: no cover - depends on optional package install
        raise RuntimeError("未安装 mahjong-detector，请先安装依赖") from exc

    return [_normalize_detector_tile(tile) for tile in detect_tiles(image)]


def _load_hand_templates(raw: bool = False) -> dict[str, Image.Image]:
    templates: dict[str, Image.Image] = {}
    for path in sorted(TEMPLATE_DIR.glob("*.png")):
        image = Image.open(path).convert("RGB")
        templates[path.stem] = _prepare_scan_image(image) if raw else _prepare_match_image(image)
    if not templates:
        raise RuntimeError(f"手牌模板目录为空: {TEMPLATE_DIR}")
    return templates


def _prepare_scan_image(image: Image.Image) -> Image.Image:
    gray = ImageOps.grayscale(image)
    gray = ImageOps.autocontrast(gray)
    return gray


def _scan_template(region: Image.Image, template: Image.Image) -> list[dict[str, Any]]:
    region_array = np.asarray(region, dtype=np.float32)
    template_array = np.asarray(template, dtype=np.float32)
    template_height, template_width = template_array.shape
    region_height, region_width = region_array.shape
    if template_height > region_height or template_width > region_width:
        return []

    matches: list[dict[str, Any]] = []
    stride = max(2, template_width // 16)
    for y in range(0, region_height - template_height + 1, stride):
        for x in range(0, region_width - template_width + 1, stride):
            patch = region_array[y : y + template_height, x : x + template_width]
            mse = np.mean((patch - template_array) ** 2)
            score = 1.0 - float(mse) / (255**2)
            if score >= 0.82:
                matches.append({"x": x, "y": y, "width": template_width, "height": template_height, "score": score})
    return matches


def _dedupe_template_matches(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(candidates, key=lambda item: item["score"], reverse=True)
    kept: list[dict[str, Any]] = []
    for candidate in ordered:
        if any(_overlaps(candidate, item) for item in kept):
            continue
        kept.append(candidate)
    kept.sort(key=lambda item: item["x"])
    return kept[:14]


def _overlaps(left: dict[str, Any], right: dict[str, Any]) -> bool:
    dx = abs((left["x"] + left["width"] / 2) - (right["x"] + right["width"] / 2))
    dy = abs((left["y"] + left["height"] / 2) - (right["y"] + right["height"] / 2))
    return dx < min(left["width"], right["width"]) * 0.55 and dy < min(left["height"], right["height"]) * 0.55


def _match_hand_tile(image: Image.Image, templates: dict[str, Image.Image]) -> tuple[str, float]:
    prepared = _prepare_match_image(image.convert("RGB"))
    best_name = ""
    best_score = -1.0
    for name, template in templates.items():
        score = _similarity(prepared, template)
        if score > best_score:
            best_name = name
            best_score = score
    return best_name, best_score


def _prepare_match_image(image: Image.Image) -> Image.Image:
    gray = ImageOps.grayscale(image)
    gray = ImageOps.autocontrast(gray)
    return gray.resize(TEMPLATE_SIZE, Image.Resampling.LANCZOS)


def _similarity(left: Image.Image, right: Image.Image) -> float:
    diff = ImageChops.difference(left, right)
    histogram = diff.histogram()
    squared_error = sum(count * (value**2) for value, count in enumerate(histogram))
    max_error = left.size[0] * left.size[1] * (255**2)
    return 1.0 - squared_error / max_error


def _normalize_detector_tile(tile: str) -> str:
    honor_map = {
        "chun": "C",
        "haku": "P",
        "hatsu": "F",
        "nan": "S",
        "pe": "N",
        "sha": "W",
        "tou": "E",
    }
    return honor_map.get(tile, tile)


def _decode_data_url(data_url: str) -> Image.Image:
    if "," in data_url:
        _, encoded = data_url.split(",", 1)
    else:
        encoded = data_url
    data = base64.b64decode(encoded)
    return Image.open(BytesIO(data)).convert("RGB")


def _crop_ratio(image: Image.Image, ratio_box: tuple[float, float, float, float]) -> Image.Image:
    return image.crop(_ratio_box(image, ratio_box))


def _ratio_box(image: Image.Image, ratio_box: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    left, top, width, height = ratio_box
    image_width, image_height = image.size
    x1 = round(image_width * left)
    y1 = round(image_height * top)
    x2 = round(image_width * (left + width))
    y2 = round(image_height * (top + height))
    return (x1, y1, x2, y2)
