from PIL import Image

from majiang_support.vision.detector import _ratio_box


def test_ratio_box_uses_image_size():
    image = Image.new("RGB", (1000, 500))

    assert _ratio_box(image, (0.1, 0.2, 0.3, 0.4)) == (100, 100, 400, 300)
