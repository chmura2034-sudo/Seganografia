import tempfile
import unittest
from pathlib import Path

import Taha


COVER = ("البر حسن الخلق والاثم ما حاك في نفسك " * 40).strip()


class TahaTests(unittest.TestCase):
    def test_round_trip_preserves_unicode_message(self):
        message = "Zażółć gęślą jaźń 😀"
        stego = Taha.encode_text(COVER, message)

        self.assertEqual(Taha.decode_text(stego), message)
        self.assertIn(Taha.KASHIDA, stego)
        self.assertTrue(any(space in stego for space in Taha.SMALL_SPACES))

    def test_file_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            carrier = Path(directory) / "carrier.txt"
            stego = Path(directory) / "stego.txt"
            carrier.write_text(COVER, encoding="utf-8")

            Taha.encode(str(carrier), "sekret", str(stego))

            self.assertEqual(Taha.decode(str(stego)), "sekret")

    def test_rejects_cover_with_reserved_characters(self):
        with self.assertRaises(ValueError):
            Taha.encode_text(COVER + Taha.KASHIDA, "sekret")

    def test_rejects_too_small_cover(self):
        with self.assertRaises(ValueError):
            Taha.encode_text("البر حسن", "sekret")


if __name__ == "__main__":
    unittest.main()
