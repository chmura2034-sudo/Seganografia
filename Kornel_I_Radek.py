from collections import deque

import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

SPACE = " "
SHORT = "\u2009"     # wąska spacja (thin space)
WS = (SPACE, SHORT)
TRAIL = 8                 # liczba spacji dopisywanych na końcu akapitu
SHIFT_BITS = 3            # ile bitów zapisuje przesunięcie jednej linii


def _levels(k):
    """Przesunięcia (w pół-punktach) dla k bitów, bez zera."""
    half = 2 ** k // 2
    return list(range(-half, 0)) + list(range(1, half + 1))


MAGIC = 0x4B52            # sygnatura "KR" (16 bitów)
MAGIC_BITS = 16
LEN_BITS = 32
HEADER_BITS = MAGIC_BITS + LEN_BITS

XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

# elementy, które w schemacie w:rPr występują PO w:position
_POS_SUCCESSORS = (
    "w:sz", "w:szCs", "w:highlight", "w:u", "w:effect", "w:bdr", "w:shd",
    "w:fitText", "w:vertAlign", "w:rtl", "w:cs", "w:em", "w:lang",
    "w:eastAsianLayout", "w:specVanish", "w:oMath",
)


# ── pomocnicze: bity ──────────────────────────────────────────────────────────

def _int_to_bits(value, width):
    return [(value >> (width - 1 - i)) & 1 for i in range(width)]


def _bytes_to_bits(data):
    return [(b >> (7 - i)) & 1 for b in data for i in range(8)]


def _bits_to_int(bits):
    v = 0
    for b in bits:
        v = (v << 1) | b
    return v


def _bits_to_bytes(bits):
    return bytes(_bits_to_int(bits[i:i + 8]) for i in range(0, len(bits), 8))


# ── pomocnicze: struktura DOCX ────────────────────────────────────────────────

def _paragraphs(doc):
    """Wszystkie akapity treści (także w tabelach), w kolejności dokumentu."""
    return list(doc.element.body.iter(qn("w:p")))


def _text_nodes(p):
    return p.xpath("./w:r/w:t | ./w:hyperlink/w:r/w:t")


def _runs(p):
    return p.xpath("./w:r[w:t] | ./w:hyperlink/w:r[w:t]")


def _last_word_char(text):
    """Indeks ostatniego znaku niebędącego spacją lub -1."""
    for i in range(len(text) - 1, -1, -1):
        if text[i] not in WS:
            return i
    return -1


def _paragraph_capacity(p, k):
    text = "".join(t.text or "" for t in _text_nodes(p))
    last = _last_word_char(text)
    if last < 0:
        return 0
    return k + sum(ch in WS for ch in text[:last]) + TRAIL


def _set_shift(p, value, k):
    val = str(_levels(k)[value])
    for r in _runs(p):
        rPr = r.get_or_add_rPr()
        for old in rPr.findall(qn("w:position")):
            rPr.remove(old)
        pos = OxmlElement("w:position")
        pos.set(qn("w:val"), val)
        rPr.insert_element_before(pos, *_POS_SUCCESSORS)


def _get_shift(p, k):
    """Wartość (0 … 2^k-1) odczytana z przesunięcia linii."""
    levels = _levels(k)
    for r in _runs(p):
        pos = r.xpath("./w:rPr/w:position")
        if pos:
            try:
                val = int(pos[0].get(qn("w:val")))
            except (TypeError, ValueError):
                return 0
            # najbliższy poziom (odporność na drobne zmiany)
            return min(range(len(levels)), key=lambda i: abs(levels[i] - val))
    return 0


def _check_k(k):
    if not isinstance(k, int) or not 1 <= k <= 6:
        raise ValueError("Liczba bitów przesunięcia musi być z zakresu 1–6.")


# ── kodowanie ─────────────────────────────────────────────────────────────────

def _encode_paragraph(p, bits, k):
    nodes = _text_nodes(p)
    texts = [list(n.text or "") for n in nodes]
    chars = [(ni, ci, ch) for ni, t in enumerate(texts) for ci, ch in enumerate(t)]
    full = "".join(ch for _, _, ch in chars)
    last = _last_word_char(full)
    if last < 0:
        return

    # 1. przesunięcie linii (k bitów, brakujące uzupełniane zerami)
    value = 0
    for _ in range(k):
        value = (value << 1) | (bits.popleft() if bits else 0)
    _set_shift(p, value, k)

    # 2. spacje między słowami
    for ni, ci, ch in chars[:last]:
        if not bits:
            break
        if ch in WS:
            texts[ni][ci] = SHORT if bits.popleft() else SPACE

    # 3. spacje na końcu akapitu (stare usuwamy, dopisujemy dokładnie TRAIL)
    if bits:
        for ni, ci, _ in chars[last + 1:]:
            texts[ni][ci] = ""
        tail = []
        for _ in range(TRAIL):
            bit = bits.popleft() if bits else 0
            tail.append(SHORT if bit else SPACE)
        texts[-1].append("".join(tail))

    for node, t in zip(nodes, texts):
        new = "".join(t)
        if new != (node.text or ""):
            node.text = new
            node.set(XML_SPACE, "preserve")


def capacity(carrier, shift_bits=SHIFT_BITS):
    """Ile bajtów wiadomości zmieści się w nośniku."""
    doc = docx.Document(carrier)
    bits = sum(_paragraph_capacity(p, shift_bits) for p in _paragraphs(doc))
    return max(0, (bits - HEADER_BITS) // 8)


def encode(carrier, message, out, shift_bits=SHIFT_BITS):
    _check_k(shift_bits)
    data = message.encode("utf-8")
    if not data:
        raise ValueError("Wiadomość jest pusta.")
    if len(data) >= 2 ** LEN_BITS:
        raise ValueError("Wiadomość jest za długa.")

    doc = docx.Document(carrier)
    paragraphs = _paragraphs(doc)
    cap_bits = sum(_paragraph_capacity(p, shift_bits) for p in paragraphs)
    needed = HEADER_BITS + 8 * len(data)
    if needed > cap_bits:
        cap_bytes = max(0, (cap_bits - HEADER_BITS) // 8)
        raise ValueError(
            f"Za mały nośnik: wiadomość ma {len(data)} B, "
            f"a zmieści się najwyżej {cap_bytes} B.")

    bits = deque(_int_to_bits(MAGIC, MAGIC_BITS)
                 + _int_to_bits(len(data), LEN_BITS)
                 + _bytes_to_bits(data))
    for p in paragraphs:
        if not bits:
            break
        _encode_paragraph(p, bits, shift_bits)

    doc.save(out)


# ── dekodowanie ───────────────────────────────────────────────────────────────

def _paragraph_bits(p, k):
    text = "".join(t.text or "" for t in _text_nodes(p))
    last = _last_word_char(text)
    if last < 0:
        return
    value = _get_shift(p, k)
    for i in range(k - 1, -1, -1):
        yield (value >> i) & 1
    for ch in text[:last]:
        if ch in WS:
            yield 1 if ch == SHORT else 0
    for ch in text[last + 1:]:
        yield 1 if ch == SHORT else 0


def decode(carrier, shift_bits=SHIFT_BITS):
    _check_k(shift_bits)
    doc = docx.Document(carrier)
    stream = [b for p in _paragraphs(doc) for b in _paragraph_bits(p, shift_bits)]

    if len(stream) < HEADER_BITS or \
            _bits_to_int(stream[:MAGIC_BITS]) != MAGIC:
        raise ValueError("Nośnik nie zawiera ukrytej wiadomości "
                         "(albo ustawiono inną liczbę bitów przesunięcia "
                         "niż przy kodowaniu).")
    length = _bits_to_int(stream[MAGIC_BITS:HEADER_BITS])

    # sprawdzenie długości wiadomości zapisanej w nagłówku
    max_len = (len(stream) - HEADER_BITS) // 8
    if length == 0:
        raise ValueError("Zapisana długość wiadomości wynosi 0 – "
                         "plik jest uszkodzony.")
    if length > max_len:
        raise ValueError(
            f"Zapisana długość wiadomości ({length} B) przekracza ilość "
            f"danych w nośniku ({max_len} B) – plik jest uszkodzony "
            f"lub był edytowany po zakodowaniu.")

    body = stream[HEADER_BITS:HEADER_BITS + 8 * length]
    try:
        return _bits_to_bytes(body).decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError("Odczytane dane nie są poprawnym tekstem UTF-8 – "
                         "plik prawdopodobnie nie był zakodowany tą metodą.")