from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

import pymupdf
import random

DELTA = 10
LEADING = 12

BASE14_FONTS = {
    "Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Helvetica-BoldOblique",
    "Times-Roman", "Times-Bold", "Times-Italic", "Times-BoldItalic",
    "Courier", "Courier-Bold", "Courier-Oblique", "Courier-BoldOblique",
}


def map_font(font_name: str) -> str:
    if not font_name:
        return "Helvetica"

    if font_name in BASE14_FONTS:
        return font_name

    name = font_name.lower()
    bold = "bold" in name
    italic = "italic" in name or "oblique" in name

    if "courier" in name or "mono" in name:
        base = "Courier"
        if bold and italic:
            return "Courier-BoldOblique"
        if bold:
            return "Courier-Bold"
        if italic:
            return "Courier-Oblique"
        return base

    if "times" in name or "serif" in name or "georgia" in name or "garamond" in name:
        if bold and italic:
            return "Times-BoldItalic"
        if bold:
            return "Times-Bold"
        if italic:
            return "Times-Italic"
        return "Times-Roman"

    # domyślnie traktujemy jako font bezszeryfowy (Arial, Calibri, Helvetica, itd.)
    if bold and italic:
        return "Helvetica-BoldOblique"
    if bold:
        return "Helvetica-Bold"
    if italic:
        return "Helvetica-Oblique"
    return "Helvetica"


def get_PDF_Text(file_path):
    every_lines = []
    doc = pymupdf.open(file_path)
    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                text = "".join(span["text"] for span in spans)
                if not text.strip():
                    continue
                first_span = spans[0]
                font = map_font(first_span.get("font", ""))
                size = first_span.get("size", 12)
                every_lines.append((text, font, size))
    return every_lines


def string_to_bits(s: str, encoding="ASCII"):
    data = s.encode(encoding)
    bits = []
    for byte in data:
        for i in range(7, -1, -1):
            bits.append((byte >> i) & 1)
    return bits


def bits_to_string(bits, encoding="ASCII"):
    bytes_list = []
    for i in range(0, len(bits), 8):
        byte = 0
        for j in range(8):
            if i + j < len(bits):
                byte = (byte << 1) | bits[i + j]
        bytes_list.append(byte)
    return bytes(bytes_list).decode(encoding, errors="replace")


def compute_nominal_positions(n_lines, page_height=A4[1],
                               margin_top_offset=60, margin_bottom=60, leading=12):
    positions = []
    y = page_height - margin_top_offset
    for _ in range(n_lines):
        if y < margin_bottom:
            y = page_height - margin_top_offset
        positions.append(y)
        y -= leading
    return positions


def create_pdf_with_hidden_message(input_lines, secret_bits, output_file_path, options):
    c = canvas.Canvas(output_file_path, pagesize=A4)
    width, height = A4
    MARGIN_BOTTOM = 60
    MARGIN_TOP_OFFSET = 60
    LEADING = 12

    y = height - MARGIN_TOP_OFFSET
    bit_index = 0

    for i, (line, font, size) in enumerate(input_lines):
        if y < MARGIN_BOTTOM:
            c.showPage()
            y = height - MARGIN_TOP_OFFSET

        shift = 0

        if options == 0:
            if i % 2 == 0 and bit_index < len(secret_bits):
                shift = DELTA if secret_bits[bit_index] else -DELTA
                bit_index += 1

        elif options == 1:
            if i % 5 not in (0, 4) and bit_index < len(secret_bits):
                shift = DELTA if secret_bits[bit_index] else -DELTA
                bit_index += 1

        c.setFont(font, size)
        c.drawString(2 * cm, y + shift, line)
        y -= LEADING

    c.save()


def encode(file_path, secret_message, shift_options, output_file_path):
    input_lines = get_PDF_Text(file_path)
    print(f"Linii dostępnych: {len(input_lines)}")

    secret_bits = string_to_bits(secret_message)

    if shift_options == 0:
        max_capacity = (len(input_lines) + 1) // 2
    elif shift_options == 1:
        max_capacity = sum(1 for i in range(len(input_lines)) if i % 5 not in (0, 4))

    if len(secret_bits) > max_capacity:
        raise ValueError("message too long for the given PDF")

    secret_bits += [random.randint(0, 1) for _ in range(max_capacity - len(secret_bits))]

    create_pdf_with_hidden_message(input_lines, secret_bits, output_file_path, shift_options)


def is_carrier(i, shift_options):
    if shift_options == 0:
        return i % 2 == 0
    return i % 5 not in (0, 4)


def decode(file_path, shift_options):
    doc = pymupdf.open(file_path)

    pages = []
    idx = 0
    for page in doc:
        raw = []
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                text = "".join(span["text"] for span in line["spans"])
                if not text.strip():
                    continue
                y = line["spans"][0]["origin"][1]
                raw.append((y, text))

        raw.sort(key=lambda t: t[0])

        page_lines = []
        for y, _ in raw:
            page_lines.append((idx, y))
            idx += 1
        pages.append(page_lines)

    all_bits = []
    for page_lines in pages:
        anchors = [(i, y) for i, y in page_lines if not is_carrier(i, shift_options)]

        for i, y in page_lines:
            if not is_carrier(i, shift_options):
                continue

            prev = [a for a in anchors if a[0] < i]
            nxt = [a for a in anchors if a[0] > i]
            p = prev[-1] if prev else None
            n = nxt[0] if nxt else None

            if p and n:
                y_nominal = p[1] + (n[1] - p[1]) * (i - p[0]) / (n[0] - p[0])
            elif p:
                y_nominal = p[1] + (i - p[0]) * LEADING
            elif n:
                y_nominal = n[1] - (n[0] - i) * LEADING
            else:
                all_bits.append(0)
                continue

            all_bits.append(1 if y < y_nominal else 0)

    return bits_to_string(all_bits)