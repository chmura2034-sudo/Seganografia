import io
import statistics

import pdfplumber
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas as rl_canvas

# Font wstrzykiwany przez koder – dekoder identyfikuje bity właśnie po tym foncie.
_STEGO_FONT      = "Helvetica"
_STEGO_FONT_NORM = "helvetica"   # do porównań case-insensitive


# ──────────────────────────────────────────────────────────────────────────────
# Funkcje pomocnicze
# ──────────────────────────────────────────────────────────────────────────────

def _message_to_bits(message: str) -> str:
    data = message.encode("utf-8")
    if len(data) > 0xFFFF:
        raise ValueError("Wiadomość jest zbyt długa (limit: 65535 bajtów).")
    header = format(len(data), "016b")
    body   = "".join(format(b, "08b") for b in data)
    return header + body


def _space_width(line_chars):
    """Szacunkowa szerokość spacji dla danej linijki (w punktach)."""
    widths = [c["x1"] - c["x0"] for c in line_chars
              if c["text"] == " " and c["x1"] - c["x0"] > 0]
    if widths:
        return statistics.median(widths)
    sizes = [c["size"] for c in line_chars if c.get("size")]
    return 0.27 * statistics.median(sizes) if sizes else 3.0


def _visible_x1(line_chars):
    """Prawy koniec ostatniego widocznego (nie-spacja) znaku linijki."""
    visible = [c for c in line_chars if c["text"].strip()]
    return max((c["x1"] for c in visible), default=None)


def _detect_right_edge(x1_values, tol=1.5, min_lines=3):
    """Prawy margines tekstu: największe x1 powtarzające się w >= min_lines linijkach."""
    ends = sorted(x1_values, reverse=True)
    for cand in ends:
        if sum(1 for e in ends if abs(e - cand) <= tol) >= min_lines:
            return cand
    return ends[0] if ends else 0


def _group_into_lines(chars, y_tol=5.0):
    chars = sorted(chars, key=lambda c: (c["top"], c["x0"]))
    lines, current, current_top = [], [], None
    for c in chars:
        if current_top is None or abs(c["top"] - current_top) <= y_tol:
            current.append(c)
            if current_top is None:
                current_top = c["top"]
        else:
            lines.append(sorted(current, key=lambda c: c["x0"]))
            current, current_top = [c], c["top"]
    if current:
        lines.append(sorted(current, key=lambda c: c["x0"]))
    return [l for l in lines if any(c["text"].strip() for c in l)]


def _has_room(line_chars, edge):
    """Czy linijka ma miejsce na co najmniej jedną dopisaną spację."""
    vx1 = _visible_x1(line_chars)
    if vx1 is None:
        return False
    sw = _space_width(line_chars)
    return sw > 0 and (edge - vx1) >= sw * 0.9


# ──────────────────────────────────────────────────────────────────────────────
# Koder
# ──────────────────────────────────────────────────────────────────────────────

def _build_overlay(page_width, page_height, insertions):
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(page_width, page_height))
    for line_chars in insertions:
        x = _visible_x1(line_chars)
        last_visible = max(
            (ch for ch in line_chars if ch["text"].strip()),
            key=lambda ch: ch["x1"]
        )
        y    = page_height - last_visible["bottom"]
        size = last_visible.get("size", 10)
        c.setFont(_STEGO_FONT, size)
        c.drawString(x, y, " ")
    c.showPage()
    c.save()
    buf.seek(0)
    return PdfReader(buf).pages[0]


def encode(carrier_pdf: str, message: str, output_pdf: str) -> None:
    """
    Koduje wiadomość w pliku PDF, zapisując wynik do output_pdf.
    Rzuca ValueError gdy wiadomość nie mieści się w dokumencie.
    """
    bits  = _message_to_bits(message)
    bit_i = 0
    plan: dict = {}

    with pdfplumber.open(carrier_pdf) as pdf:
        for page_no, page in enumerate(pdf.pages, start=1):
            lines = _group_into_lines(page.chars)
            x1s   = [x for l in lines for x in [_visible_x1(l)] if x is not None]
            edge  = _detect_right_edge(x1s) if x1s else 0
            inserts = []
            for lc in lines:
                if not _has_room(lc, edge):
                    continue
                if bit_i >= len(bits):
                    break
                if bits[bit_i] == "1":
                    inserts.append(lc)
                bit_i += 1
            if inserts:
                plan[page_no] = inserts

    if bit_i < len(bits):
        brakuje = (len(bits) - bit_i + 7) // 8
        raise ValueError(
            f"Wiadomość jest zbyt długa – w dokumencie zmieściło się tylko "
            f"{bit_i} z {len(bits)} bitów (brakuje miejsca na ok. {brakuje} bajtów)."
        )

    reader = PdfReader(carrier_pdf)
    writer = PdfWriter()
    for i, page in enumerate(reader.pages, start=1):
        if i in plan:
            pw = float(page.mediabox.width)
            ph = float(page.mediabox.height)
            overlay = _build_overlay(pw, ph, plan[i])
            page.merge_page(overlay)
        writer.add_page(page)

    with open(output_pdf, "wb") as f:
        writer.write(f)


# ──────────────────────────────────────────────────────────────────────────────
# Dekoder
# ──────────────────────────────────────────────────────────────────────────────

def _has_stego_space(line_chars, vx1):
    for c in line_chars:
        if c["text"] != " ":
            continue
        font = (c.get("fontname") or "").lower()
        if _STEGO_FONT_NORM not in font:
            continue
        # Spacja w foncie Helvetica za ostatnim widocznym znakiem
        if c["x1"] > vx1 + 0.5:
            return True
    return False


def decode(carrier_pdf: str) -> str:
    """
    Odczytuje wiadomość ukrytą w pliku PDF przez encode().
    Rzuca ValueError gdy dane są niekompletne lub plik nie zawiera wiadomości.
    """
    bits   = []
    needed = None

    with pdfplumber.open(carrier_pdf) as pdf:
        for page in pdf.pages:
            lines = _group_into_lines(page.chars)
            x1s   = [x for l in lines for x in [_visible_x1(l)] if x is not None]
            edge  = _detect_right_edge(x1s) if x1s else 0

            for lc in lines:
                vx1 = _visible_x1(lc)
                if vx1 is None or not _has_room(lc, edge):
                    continue

                bit = "1" if _has_stego_space(lc, vx1) else "0"
                bits.append(bit)

                if needed is None and len(bits) >= 16:
                    byte_len = int("".join(bits[:16]), 2)
                    needed   = 16 + byte_len * 8

                if needed is not None and len(bits) >= needed:
                    break

            if needed is not None and len(bits) >= needed:
                break

    if needed is None or len(bits) < 16:
        raise ValueError("Za mało danych w pliku – brak nagłówka.")
    if len(bits) < needed:
        raise ValueError(
            f"Plik uszkodzony lub wiadomość nie była tu zakodowana "
            f"(oczekiwano {needed} bitów, odczytano {len(bits)})."
        )

    body_bits = "".join(bits[16:needed])
    data = bytearray(
        int(body_bits[i:i + 8], 2) for i in range(0, len(body_bits), 8)
    )
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(f"Nie udało się zdekodować wiadomości (UTF-8): {e}") from e