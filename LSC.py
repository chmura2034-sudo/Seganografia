from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

import pymupdf
import random

DELTA = 1


def get_PDF_Text(file_path):
    every_lines = []
    doc = pymupdf.open(file_path)
    for page in doc:
        text = page.get_text()
        for line in text.splitlines():
            if line.strip():
                every_lines.append(line)
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
    c.setFont("Helvetica", 12)

    y = height - MARGIN_TOP_OFFSET
    bit_index = 0

    for i, line in enumerate(input_lines):
        if y < MARGIN_BOTTOM:
            c.showPage()
            c.setFont("Helvetica", 12)
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


def decode(file_path, shift_options):
    doc = pymupdf.open(file_path)
    page_height = A4[1]

    all_lines = []
    for page in doc:
        lines_on_page = []
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                text = "".join(span["text"] for span in line["spans"])
                if not text.strip():
                    continue
                y_top = line["spans"][0]["origin"][1]
                y_bottom = page_height - y_top
                lines_on_page.append((y_top, text, y_bottom))

        lines_on_page.sort(key=lambda t: t[0])
        all_lines.extend(lines_on_page)

    nominal_positions = compute_nominal_positions(len(all_lines), page_height)

    all_bits = []
    for i, (_, text, y_actual) in enumerate(all_lines):
        y_nominal = nominal_positions[i]

        use_bit = False
        if shift_options == 0:
            use_bit = (i % 2 == 0)
        elif shift_options == 1:
            use_bit = (i % 5 not in (0, 4))

        if use_bit:
            all_bits.append(1 if y_actual > y_nominal else 0)

    secret_message = bits_to_string(all_bits)

    print("Hidden message:", secret_message)
    return secret_message


