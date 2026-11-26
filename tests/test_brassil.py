import tempfile
import unittest
from pathlib import Path

import pymupdf

import Brassil


class BrassilTests(unittest.TestCase):
    def _cover(self, path, line_count=481):
        doc = pymupdf.open()
        for page_no in range((line_count + 39) // 40):
            page = doc.new_page()
            for local in range(40):
                number = page_no * 40 + local
                if number >= line_count:
                    break
                page.insert_text((60, 60 + local * 18), f"Wiersz dokumentu numer {number:03d}")
        doc.save(path)
        doc.close()

    def test_round_trip_unicode(self):
        with tempfile.TemporaryDirectory() as directory:
            cover = Path(directory) / "cover.pdf"
            stego = Path(directory) / "stego.pdf"
            self._cover(cover)
            Brassil.encode(str(cover), "Zażółć 😀", str(stego))
            self.assertEqual(Brassil.decode(str(stego)), "Zażółć 😀")

    def test_rejects_message_above_capacity(self):
        with tempfile.TemporaryDirectory() as directory:
            cover = Path(directory) / "cover.pdf"
            stego = Path(directory) / "stego.pdf"
            self._cover(cover, 21)
            with self.assertRaises(ValueError):
                Brassil.encode(str(cover), "x", str(stego))


if __name__ == "__main__":
    unittest.main()
