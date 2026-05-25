from PIL import Image

from majiang_support.vision.detector import _load_hand_templates, _match_hand_tile, _ratio_box


def test_ratio_box_uses_image_size():
    image = Image.new("RGB", (1000, 500))

    assert _ratio_box(image, (0.1, 0.2, 0.3, 0.4)) == (100, 100, 400, 300)


def test_hand_template_matches_itself():
    templates = _load_hand_templates()
    name, score = _match_hand_tile(templates["1m"], templates)

    assert name == "1m"
    assert score > 0.99
