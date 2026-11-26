"""Feature coding from Brassil et al. (1995).

Upward vertical endlines of lowercase b, d and h are extended by two pixels
to store a one; an unchanged endline stores a zero. Pages are rendered at
300 dpi and saved losslessly. Decoding compares the marked PDF with the
original, as required by the feature-coding method described in the paper.
"""

from __future__ import annotations

import struct
import zlib

import pymupdf


DPI = 300
ZOOM = DPI / 72
EXTENSION = 2
DARK_LIMIT = 170
DECODE_THRESHOLD = 45
MAGIC = b"F5"
HEADER_SIZE = 10
LETTERS = frozenset("bdh")


def _bytes_to_bits(data: bytes):
    return [(byte >> bit) & 1 for byte in data for bit in range(7, -1, -1)]


def _bits_to_bytes(bits):
    return bytes(sum(bits[i + j] << (7 - j) for j in range(8))
                 for i in range(0, len(bits) - 7, 8))


def _packet(message: str) -> bytes:
    payload = message.encode("utf-8")
    return MAGIC + struct.pack(">II", len(payload), zlib.crc32(payload)) + payload


def _luma(samples, offset):
    return (samples[offset] * 299 + samples[offset + 1] * 587
            + samples[offset + 2] * 114) // 1000


def _characters(page):
    for block in page.get_text("rawdict").get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                for char in span.get("chars", []):
                    if char.get("c", "") in LETTERS:
                        yield char


def _feature(pix, char):
    """Find pixels immediately above the character's vertical ascender."""
    x0, y0, x1, y1 = char["bbox"]
    left = max(1, int(x0 * ZOOM))
    right = min(pix.width - 2, int(x1 * ZOOM + 0.999))
    top = max(EXTENSION + 1, int(y0 * ZOOM))
    bottom = min(pix.height - 1, int(y1 * ZOOM + 0.999))
    if right - left < 2 or bottom - top < 5:
        return None

    width = right - left
    if char["c"] == "d":
        search = range(left + width // 2, right)
    else:
        search = range(left, left + max(2, width // 2 + 1))
    upper_bottom = top + max(3, int((bottom - top) * 0.72))

    columns = []
    samples = pix.samples
    for x in search:
        dark_rows = []
        for y in range(top, upper_bottom):
            offset = (y * pix.width + x) * pix.n
            if _luma(samples, offset) < DARK_LIMIT:
                dark_rows.append(y)
        if dark_rows:
            columns.append((len(dark_rows), x, min(dark_rows)))
    if not columns:
        return None
    best_count = max(item[0] for item in columns)
    if best_count < max(2, (upper_bottom - top) // 4):
        return None
    best = max(columns, key=lambda item: (item[0], -item[2]))
    stem_top = best[2]
    if stem_top < EXTENSION:
        return None

    stem_columns = [item[1] for item in columns
                    if item[0] >= best_count - 1 and abs(item[1] - best[1]) <= 1]
    if not stem_columns:
        stem_columns = [best[1]]
    stem_columns = stem_columns[:2]
    targets = [(x, stem_top - dy) for x in stem_columns
               for dy in range(1, EXTENSION + 1)]
    sources = [(x, stem_top) for x in stem_columns]
    return targets, sources


def _page_features(page, pix):
    return [feature for char in _characters(page)
            if (feature := _feature(pix, char)) is not None]


def capacity(path: str) -> int:
    count = 0
    matrix = pymupdf.Matrix(ZOOM, ZOOM)
    with pymupdf.open(path) as doc:
        for page in doc:
            pix = page.get_pixmap(matrix=matrix, colorspace=pymupdf.csRGB,
                                  alpha=False)
            count += len(_page_features(page, pix))
    return max(0, count // 8 - HEADER_SIZE)


def _mark_feature(samples, pix, feature):
    targets, sources = feature
    original_samples = pix.samples
    for index, (x, y) in enumerate(targets):
        source_x, source_y = sources[min(index // EXTENSION, len(sources) - 1)]
        source_offset = (source_y * pix.width + source_x) * pix.n
        target_offset = (y * pix.width + x) * pix.n
        samples[target_offset:target_offset + 3] = original_samples[source_offset:source_offset + 3]


def encode(original_path: str, message: str, output_path: str) -> None:
    bits = _bytes_to_bits(_packet(message))
    matrix = pymupdf.Matrix(ZOOM, ZOOM)
    source = pymupdf.open(original_path)
    rendered = []
    available = 0
    try:
        for page in source:
            pix = page.get_pixmap(matrix=matrix, colorspace=pymupdf.csRGB,
                                  alpha=False)
            features = _page_features(page, pix)
            rendered.append((pix, features, page.rect))
            available += len(features)
        if len(bits) > available:
            raise ValueError(
                f"Wiadomość wymaga {len(bits)} znaków nośnych, a dokument ma "
                f"{available}. Maksymalna treść: "
                f"{max(0, available // 8 - HEADER_SIZE)} B.")

        output = pymupdf.open()
        bit_index = 0
        try:
            for pix, features, rect in rendered:
                samples = bytearray(pix.samples)
                for feature in features:
                    if bit_index >= len(bits):
                        break
                    if bits[bit_index]:
                        _mark_feature(samples, pix, feature)
                    bit_index += 1
                marked = pymupdf.Pixmap(pymupdf.csRGB, pix.width, pix.height,
                                        bytes(samples), False)
                page = output.new_page(width=rect.width, height=rect.height)
                page.insert_image(page.rect, pixmap=marked)
            output.save(output_path, garbage=4)
        finally:
            output.close()
    finally:
        source.close()


def _feature_score(original_pix, marked_pix, feature):
    if (original_pix.width, original_pix.height) != (marked_pix.width, marked_pix.height):
        raise ValueError("Oryginał i zakodowany PDF mają różne rozmiary stron.")
    targets, _ = feature
    differences = []
    for x, y in targets:
        original_offset = (y * original_pix.width + x) * original_pix.n
        marked_offset = (y * marked_pix.width + x) * marked_pix.n
        differences.append(_luma(original_pix.samples, original_offset)
                           - _luma(marked_pix.samples, marked_offset))
    return sum(differences) / len(differences)


def _embedded_page_pixmap(document, page):
    images = page.get_images(full=True)
    if len(images) != 1:
        raise ValueError("Zakodowana strona nie zawiera oczekiwanego obrazu rastrowego.")
    pix = pymupdf.Pixmap(document, images[0][0])
    if pix.alpha or pix.n != 3:
        converted = pymupdf.Pixmap(pymupdf.csRGB, pix)
        pix = converted
    return pix


def decode(original_path: str, marked_path: str) -> str:
    matrix = pymupdf.Matrix(ZOOM, ZOOM)
    bits = []
    with pymupdf.open(original_path) as original, pymupdf.open(marked_path) as marked:
        if len(original) != len(marked):
            raise ValueError("Oryginał i zakodowany PDF mają różną liczbę stron.")
        for page_number in range(len(original)):
            original_pix = original[page_number].get_pixmap(
                matrix=matrix, colorspace=pymupdf.csRGB, alpha=False)
            marked_pix = _embedded_page_pixmap(marked, marked[page_number])
            for feature in _page_features(original[page_number], original_pix):
                score = _feature_score(original_pix, marked_pix, feature)
                bits.append(1 if score >= DECODE_THRESHOLD else 0)

    raw = _bits_to_bytes(bits)
    if len(raw) < HEADER_SIZE or raw[:2] != MAGIC:
        raise ValueError("Nie znaleziono wiadomości Feature Coding w tym pliku.")
    length, expected_crc = struct.unpack(">II", raw[2:HEADER_SIZE])
    if length > len(raw) - HEADER_SIZE:
        raise ValueError("Wiadomość jest niepełna lub dokument został zmodyfikowany.")
    payload = raw[HEADER_SIZE:HEADER_SIZE + length]
    if zlib.crc32(payload) != expected_crc:
        raise ValueError("Suma kontrolna wiadomości jest niepoprawna.")
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Wiadomość nie jest poprawnym tekstem UTF-8.") from exc
