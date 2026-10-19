"""Rekonstrukcja metody Roy i Manasmity dla dokumentów DOCX.

Jedna para bitów przypada na akapit. Format zawiera nagłówek RM01,
długość wiadomości i CRC32; nie jest zgodny z formatem innych programów.
"""

import re
import struct
import zlib
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt

MAGIC = b"RM01"
HEADER = struct.Struct(">4sII")


def _open_document(path):
    if Path(path).suffix.lower() != ".docx":
        raise ValueError("Wybierz dokument w formacie DOCX.")
    try:
        return Document(path)
    except Exception as exc:
        raise ValueError(f"Nie można otworzyć dokumentu DOCX: {exc}") from exc


def _style_size(style):
    seen = set()
    while style is not None:
        if style.style_id in seen:
            raise ValueError("Wykryto cykl w stylach dokumentu.")
        seen.add(style.style_id)
        if style.font.size is not None:
            return style.font.size.pt
        style = style.base_style
    return None


def _base_size(document, paragraph):
    size = _style_size(paragraph.style)
    if size is None:
        defaults = document.styles.element.xpath("./w:docDefaults/w:rPrDefault/w:rPr/w:sz")
        if defaults:
            try:
                size = int(defaults[0].get(qn("w:val"))) / 2
            except (ValueError, TypeError) as exc:
                raise ValueError("Nieprawidłowy domyślny rozmiar czcionki.") from exc
    if size is None or size <= 0.5:
        raise ValueError("Nie można ustalić odpowiedniego bazowego rozmiaru czcionki akapitu.")
    return size


def _normalize_spaces(runs):
    """Normalize ordinary spaces without moving characters between runs."""
    text = "".join(run.text for run in runs)
    removed = set()
    for match in re.finditer(r" +", text):
        start, end = match.span()
        if start == 0 or end == len(text) or text[end] in ",.;:!?":
            removed.update(range(start, end))
        else:
            removed.update(range(start + 1, end))
    offset = 0
    for run in runs:
        original = run.text
        normalized = "".join(char for i, char in enumerate(original, offset)
                             if i not in removed)
        if normalized != original:
            run.text = normalized
        offset += len(original)


def _inspect(document, paragraph, decoding=False, normalize=False):
    """Validate the supported paragraph subset and return text, runs and size."""
    for child in paragraph._p:
        if child.tag not in (qn("w:pPr"), qn("w:r")):
            raise ValueError("Akapit zawiera nieobsługiwane elementy, np. odnośnik lub pole.")
    runs = []
    for run in paragraph.runs:
        for child in run._r:
            if child.tag not in (qn("w:rPr"), qn("w:t")):
                raise ValueError("Akapit zawiera nieobsługiwany element, np. tabulator lub podział wiersza.")
        if not run.text:
            continue
        # Character styles can override the paragraph's base size.
        if run._r.rPr is not None and run._r.rPr.rStyle is not None:
            if _style_size(run.style) is not None:
                raise ValueError("Styl znaku nie może zmieniać rozmiaru czcionki.")
        if not decoding and run.font.size is not None:
            raise ValueError("Rozmiar tekstu musi wynikać ze stylu akapitu, bez ręcznych zmian.")
        runs.append(run)
    if normalize:
        _normalize_spaces(runs)
        runs = [run for run in runs if run.text]
    text = "".join(run.text for run in runs)
    if not text or text != text.strip() or re.search(r"\s", text.replace(" ", "")):
        raise ValueError("Akapit zawiera białe znaki inne niż zwykłe spacje albo spacje na brzegach.")
    if len(text.split()) < 2:
        raise ValueError("Każdy wykorzystywany akapit musi zawierać co najmniej dwa słowa.")
    return text, runs, _base_size(document, paragraph)


def _insert(runs, index, value):
    offset = 0
    for run in runs:
        end = offset + len(run.text)
        if index <= end:
            pos = index - offset
            run.text = run.text[:pos] + value + run.text[pos:]
            return
        offset = end
    raise ValueError("Nie można zmodyfikować tekstu akapitu.")


def _encode_pair(document, paragraph, pair):
    text, runs, base = _inspect(document, paragraph, normalize=True)
    if pair in (0, 3):
        size = base + (0.5 if pair == 3 else -0.5)
        for run in runs:
            run.font.size = Pt(size)
    elif pair == 1:
        _insert(runs, text.index(" "), " ")
    else:
        match = re.search(r"[,.;:!?]", text)
        if match:
            # A punctuation character at the start cannot be marked unambiguously.
            if match.start() == 0:
                match = re.search(r"(?<=\S)[,.;:!?]", text)
            if match:
                _insert(runs, match.start(), " ")
                return
        _insert(runs, len(text), " .")


def _decode_pair(document, paragraph):
    text, runs, base = _inspect(document, paragraph, decoding=True)
    sizes = [run.font.size.pt if run.font.size is not None else None for run in runs]
    doubled = list(re.finditer(r" {2}", text))
    special = list(re.finditer(r" (?=[,.;:!?])", text))
    if any(size is not None for size in sizes):
        if doubled or special or any(size is None for size in sizes) or len(set(sizes)) != 1:
            raise ValueError("Niejednoznaczny lub uszkodzony akapit.")
        if sizes[0] == base - 0.5:
            return 0
        if sizes[0] == base + 0.5:
            return 3
        raise ValueError("Nieprawidłowy rozmiar tekstu w zakodowanym akapicie.")
    if len(doubled) == 1 and not special and "   " not in text:
        return 1
    if len(special) == 1 and not doubled:
        return 2
    raise ValueError("Nie można jednoznacznie odczytać akapitu.")


def _paragraphs(document):
    # Treat spaces before punctuation as absent, just as normalization does.
    # This must produce the same selection before encoding and after decoding.
    return [p for p in document.paragraphs
            if len(re.sub(r" +(?=[,.;:!?])", "", p.text).split()) >= 2]


def encode(input_path, message, output_path):
    """Zapisz wiadomość w nowym DOCX. Zgłasza ValueError dla złego nośnika."""
    if not isinstance(message, str) or not message:
        raise ValueError("Wiadomość nie może być pusta.")
    if Path(output_path).suffix.lower() != ".docx":
        raise ValueError("Plik wynikowy musi mieć rozszerzenie DOCX.")
    if Path(input_path).resolve() == Path(output_path).resolve():
        raise ValueError("Wybierz inny plik wynikowy niż dokument źródłowy.")
    data = message.encode("utf-8")
    if len(data) > 0xFFFFFFFF:
        raise ValueError("Wiadomość jest zbyt długa.")
    payload = HEADER.pack(MAGIC, len(data), zlib.crc32(data)) + data
    doc = _open_document(input_path)
    paragraphs = _paragraphs(doc)
    needed = len(payload) * 4
    if len(paragraphs) < needed:
        raise ValueError(f"Za mało akapitów z co najmniej dwoma słowami: "
                         f"potrzeba {needed}, dostępnych {len(paragraphs)}.")
    for index in range(needed):
        pair = (payload[index // 4] >> (6 - 2 * (index % 4))) & 3
        try:
            _encode_pair(doc, paragraphs[index], pair)
        except ValueError as exc:
            raise ValueError(f"Akapit {index + 1}: {exc}") from exc
    doc.save(output_path)


def decode(input_path):
    """Odczytaj wiadomość z DOCX i sprawdź jej integralność."""
    doc = _open_document(input_path)
    paragraphs = _paragraphs(doc)
    if len(paragraphs) < HEADER.size * 4:
        raise ValueError("Dokument jest zbyt krótki lub nie zawiera wiadomości.")

    def read_bytes(start, count):
        output = bytearray()
        for i in range(start, start + count * 4, 4):
            byte = 0
            for j in range(4):
                try:
                    pair = _decode_pair(doc, paragraphs[i + j])
                except ValueError as exc:
                    raise ValueError(f"Akapit {i + j + 1}: {exc}") from exc
                byte = (byte << 2) | pair
            output.append(byte)
        return bytes(output)

    magic, length, checksum = HEADER.unpack(read_bytes(0, HEADER.size))
    if magic != MAGIC:
        raise ValueError("Dokument nie zawiera wiadomości w obsługiwanym formacie.")
    if length == 0 or length > (len(paragraphs) - HEADER.size * 4) // 4:
        raise ValueError("Nieprawidłowa długość wiadomości lub uszkodzony dokument.")
    data = read_bytes(HEADER.size * 4, length)
    if zlib.crc32(data) != checksum:
        raise ValueError("Suma kontrolna się nie zgadza: wiadomość została uszkodzona.")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Wiadomość nie jest poprawnym tekstem UTF-8.") from exc
