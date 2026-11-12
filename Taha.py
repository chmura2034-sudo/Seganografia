"""Metoda Taha, Hammad i Selim dla arabskich plików tekstowych UTF-8.

Implementacja odwzorowuje algorytm opisany w artykule *A high capacity
algorithm for information hiding in Arabic text* (2018): po literze, do której
można dołączyć Kashidę, ukrywany jest jeden bit, a po zwykłej spacji między
arabskimi wyrazami ukrywane są trzy bity za pomocą małych spacji Unicode.

Własny nagłówek ``TA01`` z długością i CRC32 pozwala dekoderowi zatrzymać się
dokładnie po wiadomości. Nie zmienia to sposobu ukrywania bitów opisanego w
artykule, lecz czyni odczyt z pliku możliwym bez podawania długości wiadomości.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path
from typing import Iterator, Literal


KASHIDA = "\u0640"
THIN_SPACE = "\u2009"
HAIR_SPACE = "\u200a"
SIX_PER_EM_SPACE = "\u2006"
SMALL_SPACES = (THIN_SPACE, HAIR_SPACE, SIX_PER_EM_SPACE)

MAGIC = b"TA01"
HEADER = struct.Struct(">4sII")

# Litery podstawowego alfabetu arabskiego, po których nie można dołączyć
# Kashidy. Pozostałe litery z zakresu podstawowego mogą być nośnikiem, o ile
# nie są ostatnią literą wyrazu.
NON_CONNECTING = frozenset("ءآأؤإاةدذرزوى")

SlotKind = Literal["kashida", "space"]


def _is_arabic_letter(char: str) -> bool:
    """Czy znak jest podstawową literą arabską (bez cyfr i znaków diakrytycznych)."""
    return char != KASHIDA and "\u0621" <= char <= "\u064a"


def _is_mark(char: str) -> bool:
    return "\u0610" <= char <= "\u061a" or "\u064b" <= char <= "\u065f" or char == "\u0670"


def _after_marks(text: str, index: int) -> int:
    while index < len(text) and _is_mark(text[index]):
        index += 1
    return index


def _next_arabic_letter(text: str, index: int, *, allow_stego: bool) -> int | None:
    """Zwraca indeks następnej litery w tym samym wyrazie albo ``None``."""
    index = _after_marks(text, index)
    if allow_stego and index < len(text) and text[index] == KASHIDA:
        index = _after_marks(text, index + 1)
    if index < len(text) and _is_arabic_letter(text[index]):
        return index
    return None


def _previous_arabic_letter(text: str, index: int) -> int | None:
    index -= 1
    while index >= 0 and _is_mark(text[index]):
        index -= 1
    return index if index >= 0 and _is_arabic_letter(text[index]) else None


def _space_suffix_end(text: str, index: int) -> int:
    """Pomija małe spacje w jedynym porządku dopuszczonym przez artykuł."""
    for space in SMALL_SPACES:
        if index < len(text) and text[index] == space:
            index += 1
    return index


def _slots(text: str, *, stego: bool) -> Iterator[tuple[SlotKind, int]]:
    """Kolejne pozycje nośnikowe w logicznym porządku tekstu arabskiego.

    Unicode zapisuje arabski tekst w kolejności logicznej; dla tekstu RTL jest
    to kolejność od jego wizualnego prawego brzegu, używana w pseudokodzie pracy.
    """
    for index, char in enumerate(text):
        if _is_arabic_letter(char) and char not in NON_CONNECTING:
            next_index = _after_marks(text, index + 1)
            if stego and next_index < len(text) and text[next_index] == KASHIDA:
                next_index = _after_marks(text, next_index + 1)
            if _next_arabic_letter(text, next_index, allow_stego=False) is not None:
                yield "kashida", index
        elif char == " ":
            if _previous_arabic_letter(text, index) is None:
                continue
            next_index = _space_suffix_end(text, index + 1) if stego else index + 1
            if _next_arabic_letter(text, next_index, allow_stego=False) is not None:
                yield "space", index


def _bits_from_bytes(data: bytes) -> list[int]:
    return [(byte >> shift) & 1 for byte in data for shift in range(7, -1, -1)]


def _bytes_from_bits(bits: list[int]) -> bytes:
    if len(bits) % 8:
        raise ValueError("Liczba odczytanych bitów nie jest wielokrotnością ośmiu.")
    return bytes(
        sum(bit << (7 - shift) for shift, bit in enumerate(bits[offset:offset + 8]))
        for offset in range(0, len(bits), 8)
    )


def _payload_bits(message: str) -> list[int]:
    data = message.encode("utf-8")
    if len(data) > 0xFFFFFFFF:
        raise ValueError("Wiadomość jest zbyt długa.")
    header = HEADER.pack(MAGIC, len(data), zlib.crc32(data))
    return _bits_from_bytes(header + data)


def _check_cover(text: str) -> None:
    reserved = {KASHIDA, *SMALL_SPACES}
    present = reserved.intersection(text)
    if present:
        names = {
            KASHIDA: "Kashida (U+0640)",
            THIN_SPACE: "Thin space (U+2009)",
            HAIR_SPACE: "Hair space (U+200A)",
            SIX_PER_EM_SPACE: "Six-per-em space (U+2006)",
        }
        raise ValueError(
            "Tekst nośnika zawiera znaki używane przez algorytm: "
            + ", ".join(names[char] for char in sorted(present))
            + ". Wybierz tekst bez tych znaków."
        )


def capacity_bits(text: str) -> int:
    """Zwraca pojemność nośnika w bitach, bez naruszania tekstu."""
    _check_cover(text)
    return sum(1 if kind == "kashida" else 3 for kind, _ in _slots(text, stego=False))


def encode_text(carrier: str, message: str) -> str:
    """Zwraca tekst nośnika z ukrytą wiadomością UTF-8."""
    _check_cover(carrier)
    bits = _payload_bits(message)
    capacity = capacity_bits(carrier)
    if len(bits) > capacity:
        available_bytes = max(0, (capacity - HEADER.size * 8) // 8)
        raise ValueError(
            "Wiadomość jest zbyt długa dla tego tekstu arabskiego "
            f"(pojemność na treść: ok. {available_bytes} B, wymagane: "
            f"{len(message.encode('utf-8'))} B)."
        )

    insertions: dict[int, str] = {}
    bit_index = 0
    for kind, index in _slots(carrier, stego=False):
        if bit_index >= len(bits):
            break
        if kind == "kashida":
            if bits[bit_index]:
                insertions[_after_marks(carrier, index + 1)] = KASHIDA
            bit_index += 1
            continue

        group = bits[bit_index:bit_index + 3]
        insertions[index + 1] = "".join(
            space for bit, space in zip(group, SMALL_SPACES) if bit
        )
        bit_index += len(group)

    if bit_index < len(bits):  # zabezpieczenie spójności obliczonej pojemności
        raise RuntimeError("Nie udało się wykorzystać całej obliczonej pojemności nośnika.")

    return "".join(
        char + insertions.get(index + 1, "") for index, char in enumerate(carrier)
    )


def _extract_bits(stego: str) -> list[int]:
    bits: list[int] = []
    for kind, index in _slots(stego, stego=True):
        if kind == "kashida":
            marker_index = _after_marks(stego, index + 1)
            bits.append(int(marker_index < len(stego) and stego[marker_index] == KASHIDA))
            continue

        cursor = index + 1
        for space in SMALL_SPACES:
            if cursor < len(stego) and stego[cursor] == space:
                bits.append(1)
                cursor += 1
            else:
                bits.append(0)
    return bits


def decode_text(stego: str) -> str:
    """Odczytuje wiadomość z tekstu wygenerowanego przez :func:`encode_text`."""
    bits = _extract_bits(stego)
    header_bits = HEADER.size * 8
    if len(bits) < header_bits:
        raise ValueError("Za mało danych w tekście – brak nagłówka wiadomości.")

    magic, length, expected_crc = HEADER.unpack(_bytes_from_bits(bits[:header_bits]))
    if magic != MAGIC:
        raise ValueError("Tekst nie zawiera wiadomości zakodowanej metodą Taha, Hammad i Selim.")

    required = header_bits + length * 8
    if len(bits) < required:
        raise ValueError(
            f"Wiadomość jest niekompletna (wymagane {required} bitów, odczytane {len(bits)})."
        )
    data = _bytes_from_bits(bits[header_bits:required])
    if zlib.crc32(data) != expected_crc:
        raise ValueError("Suma kontrolna wiadomości jest nieprawidłowa – tekst został zmieniony.")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Odczytane dane nie są poprawnym tekstem UTF-8.") from exc


def _read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as file:
            return file.read()
    except OSError as exc:
        raise ValueError(f"Nie można odczytać pliku TXT: {exc}") from exc
    except UnicodeDecodeError as exc:
        raise ValueError("Plik TXT musi być zapisany w kodowaniu UTF-8.") from exc


def encode(carrier_path: str, message: str, output_path: str) -> None:
    """Koduje wiadomość w pliku UTF-8 TXT."""
    carrier = _read_text(carrier_path)
    stego = encode_text(carrier, message)
    try:
        with open(output_path, "w", encoding="utf-8", newline="") as file:
            file.write(stego)
    except OSError as exc:
        raise ValueError(f"Nie można zapisać pliku TXT: {exc}") from exc


def decode(stego_path: str) -> str:
    """Odczytuje wiadomość z pliku UTF-8 TXT."""
    return decode_text(_read_text(stego_path))
