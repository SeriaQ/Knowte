import base64
import io
import unittest
from unittest.mock import MagicMock, patch

from knowte.capture import _ImageDirectory, capture_evidence_image, CaptureError


class ImageDirectoryTests(unittest.TestCase):
    def test_figure_captions_and_sphinx_captions(self):
        parser = _ImageDirectory("https://example.org/docs/intro")
        parser.feed('<figure><img src="../a.jpg" alt="Algorithm"><figcaption>Figure <b>one</b>.</figcaption></figure>'
                    '<div class="figure align-center"><img src="/b.webp"><p class="caption"><span>Diagram two</span></p></div>'
                    '<img src="data:image/png;base64,foo"><img data-src="/lazy.png">')
        self.assertEqual(len(parser.images), 3)
        self.assertEqual(parser.images[0]["image_url"], "https://example.org/a.jpg")
        self.assertEqual(parser.images[0]["caption"], "Figure one .")
        self.assertEqual(parser.images[1]["caption"], "Diagram two")

    def test_original_jpeg_is_converted_to_png(self):
        from PIL import Image
        raw = io.BytesIO()
        Image.new("RGB", (3, 2), "red").save(raw, "JPEG")
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = raw.getvalue()
        with patch("knowte.capture.urlopen", return_value=response):
            result = capture_evidence_image("https://example.org/original.jpg")
        decoded = base64.b64decode(result.split(",", 1)[1])
        with Image.open(io.BytesIO(decoded)) as image:
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.size, (3, 2))
        response.read.return_value = b"<svg></svg>"
        with patch("knowte.capture.urlopen", return_value=response), self.assertRaises(CaptureError):
            capture_evidence_image("https://example.org/vector.svg")
