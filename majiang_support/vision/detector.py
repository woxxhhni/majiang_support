from __future__ import annotations

import base64
from dataclasses import dataclass
from io import BytesIO
from typing import Any

from PIL import Image


@dataclass(frozen=True)
class RegionDetection:
    name: str
    tiles: tuple[str, ...]
    box: tuple[int, int, int, int]


def detect_screenshot_regions(data_url: str) -> dict[str, Any]:
    image = _decode_data_url(data_url)
    hand_region = _crop_ratio(image, (0.015, 0.790, 0.875, 0.205))
    discard_region = _crop_ratio(image, (0.245, 0.125, 0.540, 0.610))

    hand_tiles = _detect_tiles(hand_region)
    discard_tiles = _detect_tiles(discard_region)

    return {
        "hand": {
            "tiles": hand_tiles,
            "box": _ratio_box(image, (0.015, 0.790, 0.875, 0.205)),
        },
        "discards": {
            "tiles": discard_tiles,
            "box": _ratio_box(image, (0.245, 0.125, 0.540, 0.610)),
        },
    }


def _detect_tiles(image: Image.Image) -> list[str]:
    try:
        from mahjong_detector import detect_tiles
    except Exception as exc:  # pragma: no cover - depends on optional package install
        raise RuntimeError("未安装 mahjong-detector，请先安装依赖") from exc

    return [_normalize_detector_tile(tile) for tile in detect_tiles(image)]


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

