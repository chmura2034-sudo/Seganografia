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


Metoda przesunięć pionowych linii LSC (PDF)
---------------------------------------------
 
Uruchom `python Main.py` i wybierz zakładkę „Przesunięcia linii (PDF)”. W podzakładce „Kodowanie” wybierz plik PDF, wpisz wiadomość, wybierz tryb przesunięć (`0` lub `1`) i wskaż nowy plik wynikowy. W podzakładce „Dekodowanie” wybierz zapisany plik i ten sam tryb, aby odczytać wiadomość. Oryginalny plik nie jest potrzebny do odczytu.
 
Wykorzystywane są kolejne niepuste linie tekstu z warstwy tekstowej PDF-a. Część linii to nośniki, które program przesuwa w pionie o `DELTA = 10` pt: bit `1` oznacza przesunięcie w górę, bit `0` w dół. Pozostałe linie to kotwice i zostają na pozycjach nominalnych. W trybie `0` nośnikiem jest co druga linia, w trybie `1` trzy linie z pięciu (`i % 5` poza {0, 4}). Wiadomość może zawierać tylko znaki ASCII (8 bitów na znak), co daje około 16 linii na znak w trybie `0` i około 13 w trybie `1`. Nieużyte nośniki są wypełniane losowymi bitami, więc odczyt może zwrócić po wiadomości losowe znaki. Plik wynikowy jest generowany od nowa: zachowywany jest tekst, rozmiar czcionki i nazwa czcionki zmapowana na 14 standardowych czcionek PDF (tylko z pierwszego fragmentu linii), ale nie układ strony, grafiki, tabele, kolory ani kolumny. Wszystkie linie trafiają do jednej kolumny od lewego marginesu (`2 cm`).
 
Przy odczycie pozycja nominalna każdego nośnika jest interpolowana między sąsiednimi kotwicami na tej samej stronie i porównywana z pozycją rzeczywistą. Odczyt zakłada odstęp `LEADING = 12` pt i marginesy 60 pt, zgodne z zapisem. Odczyt odbywa się z tekstu PDF-a, bez OCR. Edycja, ponowny zapis lub rasteryzacja pliku może uszkodzić wiadomość. Przesunięcia są widoczne gołym okiem. Metoda nie szyfruje ukrytych danych.






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
