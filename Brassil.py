"""Differential line-shift coding based on Brassil et al. (1995).

The implementation operates on the text layer of a PDF.  On every page the
first, third, fifth... text lines are reference lines.  Each line between two
reference lines is shifted up (bit 1) or down (bit 0).  The decoder compares
the carrier baseline with the midpoint of its neighbouring reference lines,
so the original PDF is not needed.
"""

from __future__ import annotations

import struct
import zlib

import pymupdf


MAGIC = b"B5"
HEADER_SIZE = 10                 # magic + uint32 length + uint32 CRC32
SHIFT_POINTS = 1.5               # about 6 pixels on a 300 dpi printer

BASE14_FONTS = {
    "Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Helvetica-BoldOblique",
    "Times-Roman", "Times-Bold", "Times-Italic", "Times-BoldItalic",
    "Courier", "Courier-Bold", "Courier-Oblique", "Courier-BoldOblique",
}


def _font(name: str) -> str:
    """Map an embedded PDF font name to one of PyMuPDF's built-in fonts."""
    raw = (name or "").split("+")[-1]
    low = raw.lower()
    bold = "bold" in low
    italic = "italic" in low or "oblique" in low
    if "courier" in low or "mono" in low:
        family = "Courier"
        italic_suffix = "Oblique"
    elif any(part in low for part in ("times", "serif", "georgia", "garamond")):
        family = "Times"
        italic_suffix = "Italic"
    else:
        family = "Helvetica"
        italic_suffix = "Oblique"
    if family == "Times" and not bold and not italic:
        return "Times-Roman"
    suffix = ("-Bold" if bold else "") + (italic_suffix if bold and italic else
             (f"-{italic_suffix}" if italic else ""))
    result = family + suffix
    return result if result in BASE14_FONTS else "Helvetica"


def _page_lines(page):
    lines = []
    for block in page.get_text("dict").get("blocks", []):
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            text = "".join(span.get("text", "") for span in spans)
            if spans and text.strip():
                lines.append({"spans": spans, "y": float(spans[0]["origin"][1])})
    # This is also the order used after reconstructing the text layer.
    lines.sort(key=lambda item: (round(item["y"], 2), item["spans"][0]["origin"][0]))
    return lines


def _carrier_count(line_counts):
    # A carrier must have an unchanged reference line on both sides.
    return sum(max(0, (count - 1) // 2) for count in line_counts)


def capacity(path: str) -> int:
    """Return maximum UTF-8 payload size in bytes."""
    with pymupdf.open(path) as doc:
        carriers = _carrier_count([len(_page_lines(page)) for page in doc])
    return max(0, carriers // 8 - HEADER_SIZE)


def _bytes_to_bits(data: bytes):
    return [(byte >> bit) & 1 for byte in data for bit in range(7, -1, -1)]


def _bits_to_bytes(bits):
    return bytes(sum(bits[i + j] << (7 - j) for j in range(8))
                 for i in range(0, len(bits) - 7, 8))


def _packet(message: str) -> bytes:
    payload = message.encode("utf-8")
    return MAGIC + struct.pack(">II", len(payload), zlib.crc32(payload)) + payload


def encode(input_path: str, message: str, output_path: str) -> None:
    bits = _bytes_to_bits(_packet(message))
    source = pymupdf.open(input_path)
    pages = [_page_lines(page) for page in source]
    available = _carrier_count(map(len, pages))
    if len(bits) > available:
        source.close()
        raise ValueError(
            f"Wiadomość wymaga {len(bits)} linii nośnych, a dokument ma {available}. "
            f"Maksymalna treść: {max(0, available // 8 - HEADER_SIZE)} B.")

    output = pymupdf.open()
    bit_index = 0
    try:
        for page_no, lines in enumerate(pages):
            old_page = source[page_no]
            new_page = output.new_page(width=old_page.rect.width, height=old_page.rect.height)
            for index, line in enumerate(lines):
                shift = 0.0
                if index % 2 == 1 and index + 1 < len(lines) and bit_index < len(bits):
                    shift = -SHIFT_POINTS if bits[bit_index] else SHIFT_POINTS
                    bit_index += 1
                for span in line["spans"]:
                    text = span.get("text", "")
                    if not text:
                        continue
                    x, y = span["origin"]
                    color_int = int(span.get("color", 0))
                    color = ((color_int >> 16 & 255) / 255,
                             (color_int >> 8 & 255) / 255,
                             (color_int & 255) / 255)
                    new_page.insert_text((x, y + shift), text,
                                         fontsize=float(span.get("size", 12)),
                                         fontname=_font(span.get("font", "")),
                                         color=color)
        output.save(output_path, garbage=4, deflate=True)
    finally:
        output.close()
        source.close()


def decode(path: str) -> str:
    bits = []
    with pymupdf.open(path) as doc:
        for page in doc:
            lines = _page_lines(page)
            for index in range(1, len(lines) - 1, 2):
                expected = (lines[index - 1]["y"] + lines[index + 1]["y"]) / 2
                bits.append(1 if lines[index]["y"] < expected else 0)

    raw = _bits_to_bytes(bits)
    if len(raw) < HEADER_SIZE or raw[:2] != MAGIC:
        raise ValueError("Nie znaleziono wiadomości Brassila w tym pliku PDF.")
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
