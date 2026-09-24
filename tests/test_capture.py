import unittest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from knowte.capture import _ReadableHTML, preferred_capture_url, capture_source_content


class CaptureSelectionTests(unittest.TestCase):
    def test_native_pdf_download_does_not_parse_text(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b"%PDF-original document bytes"
        response.headers.get_content_type.return_value = "application/pdf"
        response.geturl.return_value = "https://example.org/paper.pdf"
        with tempfile.TemporaryDirectory() as directory, patch("knowte.capture.urlopen", return_value=response), patch("knowte.capture._extract_pdf") as extract:
            captured = capture_source_content({"url": response.geturl.return_value}, Path(directory), parse_pdf=False)
            extract.assert_not_called()
            self.assertEqual(captured["segments"], [])
            self.assertEqual(Path(captured["raw_path"]).read_bytes(), response.read.return_value)

    def test_html_capture_prefers_article_over_site_chrome(self):
        parser = _ReadableHTML()
        parser.feed(
            "<header><p>Account navigation should not appear here.</p></header>"
            "<main><div>Repository file list should be a fallback only.</div>"
            "<article><h1>Qwen README</h1>"
            "<p>" + ("Technical model documentation. " * 10) + "</p>"
            "<button>Copy code</button></article></main>"
        )
        parser.close()

        self.assertTrue(parser.segments[0].startswith("Qwen README"))
        self.assertTrue(all("navigation" not in text for text in parser.segments))
        self.assertTrue(all("file list" not in text for text in parser.segments))
        self.assertTrue(all("Copy code" not in text for text in parser.segments))

    def test_html_capture_uses_main_when_no_substantial_article_exists(self):
        parser = _ReadableHTML()
        parser.feed(
            "<header><p>Site navigation that should be skipped.</p></header>"
            "<main><h1>Article title long enough</h1><p>"
            + ("Main page content. " * 15)
            + "</p></main><footer>Footer links should be skipped.</footer>"
        )
        parser.close()

        self.assertTrue(any("Main page content" in text for text in parser.segments))
        self.assertTrue(all("navigation" not in text for text in parser.segments))

    def test_paper_prefers_pdf_for_faithful_inspection(self):
        self.assertEqual(
            preferred_capture_url(
                {
                    "source_type": "paper",
                    "paper_url": "https://arxiv.org/abs/2309.16609v1",
                    "pdf_url": "https://arxiv.org/pdf/2309.16609v1",
                }
            ),
            "https://arxiv.org/pdf/2309.16609v1",
        )

    def test_web_source_keeps_webpage_capture(self):
        self.assertEqual(
            preferred_capture_url(
                {
                    "source_type": "web",
                    "url": "https://example.test/article",
                }
            ),
            "https://example.test/article",
        )


if __name__ == "__main__":
    unittest.main()
