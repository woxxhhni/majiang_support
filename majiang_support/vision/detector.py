from __future__ import annotations

import base64
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps
import numpy as np


TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "assets" / "templates" / "hand"
TEMPLATE_SIZE = (64, 88)
SYMBOL_SIZE = (96, 120)
RANK_SIZE = (96, 56)


@dataclass(frozen=True)
class RegionDetection:
    name: str
    tiles: tuple[str, ...]
    box: tuple[int, int, int, int]


@dataclass(frozen=True)
class TileFeature:
    symbol_gray: np.ndarray
    symbol_mask: np.ndarray
    rank_mask: np.ndarray
    suit_hint: str | None


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
        templates[path.stem] = _prepare_scan_image(image) if raw else image
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
    prepared = _extract_tile_feature(image.convert("RGB"))
    best_name = ""
    best_score = -1.0
    candidates = templates
    if prepared.suit_hint:
        same_suit = {name: template for name, template in templates.items() if name.endswith(prepared.suit_hint)}
        if same_suit:
            candidates = same_suit
    for name, template in candidates.items():
        score = _tile_similarity(prepared, _extract_tile_feature(template), name)
        if score > best_score:
            best_name = name
            best_score = score
    return best_name, best_score


def _extract_tile_feature(image: Image.Image) -> TileFeature:
    foreground = _foreground_mask(image)
    symbol = _crop_by_mask(image, foreground)
    symbol_gray = _prepare_feature_gray(symbol, SYMBOL_SIZE)
    symbol_mask = _prepare_feature_mask(_foreground_mask(symbol), SYMBOL_SIZE)

    rank_source = _rank_area(image)
    black = _black_mask(rank_source)
    rank = _crop_by_mask(rank_source, black)
    rank_mask = _prepare_feature_mask(_black_mask(rank), RANK_SIZE)
    return TileFeature(
        symbol_gray=symbol_gray,
        symbol_mask=symbol_mask,
        rank_mask=rank_mask,
        suit_hint=_guess_suit(image),
    )


def _tile_similarity(left: TileFeature, right: TileFeature, template_name: str) -> float:
    symbol_score = 0.65 * _array_similarity(left.symbol_gray, right.symbol_gray) + 0.35 * _mask_iou(
        left.symbol_mask, right.symbol_mask
    )
    if template_name.endswith("m"):
        rank_score = _projection_score(left.rank_mask, right.rank_mask)
        return 0.78 * rank_score + 0.22 * symbol_score
    return symbol_score


def _prepare_feature_gray(image: Image.Image, size: tuple[int, int]) -> np.ndarray:
    gray = ImageOps.grayscale(image)
    gray = ImageOps.autocontrast(gray)
    return np.asarray(gray.resize(size, Image.Resampling.LANCZOS), dtype=np.float32) / 255.0


def _prepare_feature_mask(mask: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    if mask.size == 0:
        return np.zeros((size[1], size[0]), dtype=bool)
    image = Image.fromarray((mask.astype(np.uint8) * 255), mode="L")
    resized = image.resize(size, Image.Resampling.NEAREST)
    return np.asarray(resized) > 0


def _foreground_mask(image: Image.Image) -> np.ndarray:
    array = np.asarray(image.convert("RGB"), dtype=np.int16)
    channel_min = array.min(axis=2)
    channel_max = array.max(axis=2)
    saturation = channel_max - channel_min
    return (channel_min < 205) | (saturation > 28)


def _black_mask(image: Image.Image) -> np.ndarray:
    array = np.asarray(image.convert("RGB"), dtype=np.int16)
    red, green, blue = array[:, :, 0], array[:, :, 1], array[:, :, 2]
    return (red < 120) & (green < 120) & (blue < 120)


def _rank_area(image: Image.Image) -> Image.Image:
    foreground = _foreground_mask(image)
    tile = _crop_by_mask(image, foreground, padding=8)
    left = round(tile.width * 0.08)
    top = round(tile.height * 0.02)
    right = round(tile.width * 0.92)
    bottom = round(tile.height * 0.45)
    return tile.crop((left, top, right, bottom))


def _guess_suit(image: Image.Image) -> str | None:
    array = np.asarray(image.convert("RGB"), dtype=np.int16)
    foreground = _foreground_mask(image)
    if foreground.sum() == 0:
        return None
    red, green, blue = array[:, :, 0], array[:, :, 1], array[:, :, 2]
    red_ratio = (((red > 120) & (green < 125) & (blue < 125) & foreground).sum() / foreground.sum())
    green_ratio = (((green > red + 24) & (green > blue + 18) & foreground).sum() / foreground.sum())
    black_ratio = (_black_mask(image).sum() / foreground.sum())
    if red_ratio > 0.12 and green_ratio < 0.04 and black_ratio > 0.10:
        return "m"
    if green_ratio > 0.28 and red_ratio < 0.07:
        return "s"
    if green_ratio > 0.06 and red_ratio > 0.04:
        return "p"
    return None


def _crop_by_mask(image: Image.Image, mask: np.ndarray, padding: int = 5) -> Image.Image:
    ys, xs = np.where(mask)
    if len(xs) == 0 or len(ys) == 0:
        return image
    left = max(int(xs.min()) - padding, 0)
    top = max(int(ys.min()) - padding, 0)
    right = min(int(xs.max()) + padding + 1, image.width)
    bottom = min(int(ys.max()) + padding + 1, image.height)
    return image.crop((left, top, right, bottom))


def _array_similarity(left: np.ndarray, right: np.ndarray) -> float:
    return 1.0 - float(np.mean((left - right) ** 2))


def _mask_iou(left: np.ndarray, right: np.ndarray) -> float:
    union = np.logical_or(left, right).sum()
    if union == 0:
        return 0.0
    return float(np.logical_and(left, right).sum() / union)


def _projection_score(left: np.ndarray, right: np.ndarray) -> float:
    row_score = _best_shifted_correlation(left.sum(axis=1), right.sum(axis=1), max_shift=24)
    column_score = _best_shifted_correlation(left.sum(axis=0), right.sum(axis=0), max_shift=18)
    segment_penalty = 0.08 * abs(_segment_count(left.sum(axis=1)) - _segment_count(right.sum(axis=1)))
    component_penalty = 0.16 * abs(_component_count(left) - _component_count(right))
    return max(0.0, (0.65 * row_score + 0.35 * column_score) - segment_penalty - component_penalty)


def _best_shifted_correlation(left: np.ndarray, right: np.ndarray, max_shift: int) -> float:
    left = left.astype(np.float32)
    right = right.astype(np.float32)
    best = 0.0
    for shift in range(-max_shift, max_shift + 1):
        if shift < 0:
            left_window = left[-shift:]
            right_window = right[: len(left_window)]
        elif shift > 0:
            left_window = left[:-shift]
            right_window = right[shift:]
        else:
            left_window = left
            right_window = right
        if len(left_window) < 8 or left_window.std() == 0 or right_window.std() == 0:
            continue
        score = float(np.corrcoef(left_window, right_window)[0, 1])
        best = max(best, score)
    return best


def _segment_count(projection: np.ndarray) -> int:
    if projection.max() <= 0:
        return 0
    active = projection > projection.max() * 0.25
    count = 0
    in_segment = False
    for value in active:
        if value and not in_segment:
            count += 1
            in_segment = True
        elif not value:
            in_segment = False
    return count


def _component_count(mask: np.ndarray, min_pixels: int = 100) -> int:
    visited = np.zeros(mask.shape, dtype=bool)
    height, width = mask.shape
    count = 0
    for y in range(height):
        for x in range(width):
            if not mask[y, x] or visited[y, x]:
                continue
            pixels = 0
            stack = [(y, x)]
            visited[y, x] = True
            while stack:
                current_y, current_x = stack.pop()
                pixels += 1
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        next_y = current_y + dy
                        next_x = current_x + dx
                        if (
                            0 <= next_y < height
                            and 0 <= next_x < width
                            and mask[next_y, next_x]
                            and not visited[next_y, next_x]
                        ):
                            visited[next_y, next_x] = True
                            stack.append((next_y, next_x))
            if pixels >= min_pixels:
                count += 1
    return count


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
