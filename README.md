Przed uruchomieniem !!!
-----------------------------------------

python -m venv venv

source venv/bin/activate

pip install -r requirements.txt

Lista literatury i każdej metody steganogrficznej:
--------------------------------------------------
I: https://ieeexplore.ieee.org/abstract/document/8628471

II: https://www.researchgate.net/publication/268515701_A_New_Property_Coding_in_Text_Steganography_of_Microsoft_Word_Documents

III: https://www.researchgate.net/publication/220846511_A_novel_approach_to_format_based_text_steganography

IV: https://www.sciencedirect.com/science/article/pii/S1319157818302945

V: https://www.researchgate.net/publication/3233597_Electronic_marking_and_identification_techniques_to_discourage_document_copying

Metoda Roy i Manasmity (DOCX)
-----------------------------------------

Uruchom `python Main.py` i wybierz zakładkę „Roy i Manasmita”. W podzakładce
„Kodowanie” wybierz plik DOCX, wpisz wiadomość i wskaż nowy plik wynikowy.
W podzakładce „Dekodowanie” wybierz zapisany plik, aby odczytać wiadomość.
Oryginalny plik nie jest potrzebny do odczytu.

Wykorzystywane są kolejne akapity głównej części dokumentu, zawierające po
normalizacji co najmniej dwa słowa (bez tekstów w tabelach, nagłówkach i
stopkach). Puste i jednowyrazowe akapity są pomijane przy zapisie i odczycie.
Rozmiar czcionki musi wynikać ze stylu akapitu, bez indywidualnych zmian
rozmiaru w tekście lub stylu znaku. Akapity nie mogą zawierać m.in.
tabulatorów, ręcznych podziałów wiersza, pól ani odnośników. Jeżeli brakuje
interpunkcji, kodowanie może dodać kropkę. W wykorzystywanych akapitach
program usuwa nadmiarowe zwykłe spacje, w tym spacje na brzegach oraz przed
znakami `, . ; : ! ?`. Zmiany trafiają tylko do pliku wynikowego. Pozostałe
formatowanie jest zachowywane. Wymagane akapity: `4 × (12 + liczba bajtów wiadomości UTF-8)`;
12 bajtów zajmuje nagłówek z długością i sumą kontrolną.

Jest to praktyczna rekonstrukcja algorytmu z pracy Roy i Manasmity: akapity
zastępują wizualne wiersze, a szczegóły formatu i nagłówka są własne. Odczyt
odbywa się z pliku DOCX, bez OCR. Edycja tekstu lub formatowania po zapisaniu
może uszkodzić wiadomość. Metoda nie szyfruje ukrytych danych.

Testy modułu: `python -m unittest discover -s tests -v`.
