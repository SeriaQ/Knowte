import tempfile
import unittest
import json
from importlib.metadata import version as package_version
from pathlib import Path

from knowte.companion import CompanionStore


class CompanionStoreTests(unittest.TestCase):
    def test_extension_manifest_matches_knowte_version(self):
        manifest_path = Path(__file__).resolve().parent.parent / "browser-extension" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], package_version("knowte"))

    def test_pairing_token_and_pending_capture_lifecycle(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = CompanionStore(Path(temp_dir))
            pairing = store.create_pairing("light")
            token = store.pair(pairing["code"], pairing["nonce"])

            self.assertTrue(store.authenticated(token))
            self.assertFalse(store.authenticated("wrong-token"))
            self.assertEqual(store.preferences()["theme"], "light")
            store.set_theme("dark")
            self.assertEqual(store.preferences()["theme"], "dark")

            item = store.add({
                "kind": "text",
                "source": {
                    "title": "Original article",
                    "url": "https://example.test/article",
                },
                "quote": "A precise statement from the original page.",
                "blocks": [{
                    "type": "paragraph",
                    "text": "A precise statement from the original page.",
                }],
            })

            self.assertEqual(store.list()[0]["id"], item["id"])
            self.assertTrue(store.remove(item["id"]))
            self.assertEqual(store.list(), [])

    def test_pairing_can_only_be_used_once(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = CompanionStore(Path(temp_dir))
            pairing = store.create_pairing()
            store.pair(pairing["code"], pairing["nonce"])

            with self.assertRaisesRegex(ValueError, "expired"):
                store.pair(pairing["code"], pairing["nonce"])


if __name__ == "__main__":
    unittest.main()
