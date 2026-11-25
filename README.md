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
 
Uruchom `python Main.py` i wybierz zakładkę „LSC”. W podzakładce „Kodowanie” wybierz plik PDF, wpisz wiadomość, wybierz tryb przesunięć (`0` lub `1`) i wskaż nowy plik wynikowy. W podzakładce „Dekodowanie” wybierz zapisany plik i ten sam tryb, aby odczytać wiadomość. Oryginalny plik nie jest potrzebny do odczytu.
 
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





Metoda wolnych spacji na końcu linii (PDF)
----------------------
 
Uruchom `python Main.py` i wybierz zakładkę „Spacje na końcu linii". W podzakładce „Kodowanie" wybierz plik PDF, wpisz wiadomość i wskaż nowy plik wynikowy. W podzakładce „Dekodowanie" wybierz zapisany plik, aby odczytać wiadomość. Oryginalny plik nie jest potrzebny do odczytu.
 
Wykorzystywane są kolejne niepuste linie tekstu z warstwy tekstowej PDF-a, które posiadają wolne miejsce na końcu (tzn. odległość od ostatniego znaku do prawego marginesu tekstu wynosi co najmniej szerokość jednej spacji). Wiadomość kodowana jest binarnie: bit `1` oznacza dopisanie niewidocznej spacji za ostatnim znakiem linii, bit `0` pozostawia linię bez zmian. Linie bez wolnego miejsca są pomijane i nie zużywają żadnego bitu. Pojemność zależy od układu tekstu w dokumencie – im więcej linii kończy się przed prawym marginesem, tym więcej bitów można ukryć. Maksymalna długość wiadomości to 65 535 bajtów (nagłówek 16-bitowy przechowuje długość treści). Wiadomość może zawierać dowolne znaki Unicode kodowane w UTF-8.
 
Dopisana spacja jest prawdziwym znakiem tekstowym osadzonym w warstwie PDF-a (fontem Helvetica), niewidocznym wizualnie, lecz obecnym przy zaznaczaniu i kopiowaniu tekstu. Dekoder identyfikuje bity wyłącznie po spacjach w foncie Helvetica, dzięki czemu metoda działa poprawnie również na dokumentach zawierających naturalne spacje łamiące wiersze (np. PDF-y generowane przez edytory tekstu), które są całkowicie ignorowane. Prawy margines tekstu wyznaczany jest automatycznie jako pozycja, przy której kończy się największa liczba linii na danej stronie.
 
Oryginalny plik PDF pozostaje niezmieniony poza warstwą tekstową – układ strony, grafiki, tabele, kolory i czcionki są zachowane w całości. Metoda nie szyfruje ukrytych danych. Edycja, ponowny zapis w innym programie lub rasteryzacja pliku może usunąć dopisane spacje i uniemożliwić odczyt wiadomości. Przesunięcia nie są widoczne gołym okiem.


Metoda Taha, Hammad i Selim (arabski TXT)
------------------------------------------

Uruchom `python Main.py` i wybierz zakładkę „Taha, Hammad i Selim”. W podzakładce „Kodowanie” wybierz plik TXT zapisany w UTF-8, zawierający arabski tekst, wpisz wiadomość i wskaż plik wynikowy. W „Dekodowaniu” wybierz plik wynikowy, aby odczytać wiadomość.

Implementacja opiera się na artykule [A high capacity algorithm for information hiding in Arabic text](https://doi.org/10.1016/j.jksuci.2018.07.007). Po literze arabskiej, do której może zostać dołączona Kashida (`U+0640`), ukrywany jest jeden bit: Kashida oznacza `1`, jej brak `0`. Po zwykłej spacji między arabskimi wyrazami ukrywane są trzy bity w kolejności: Thin space (`U+2009`), Hair space (`U+200A`) i Six-per-em space (`U+2006`). Nośnik nie może zawierać tych czterech znaków przed kodowaniem.

Do bitów wiadomości program dodaje własny 12-bajtowy nagłówek z sygnaturą, długością i CRC32. Dzięki temu dekoder zna koniec wiadomości i wykrywa modyfikację tekstu; sam sposób rozmieszczania bitów pozostaje zgodny z algorytmem artykułu. Wiadomość jest kodowana w UTF-8. Zmiana tekstu, normalizacja znaków Unicode lub zapis w programie, który usuwa małe spacje, może uniemożliwić odczyt. Metoda nie szyfruje danych.

Testy modułu: `python -m unittest tests/test_taha.py -v`.

### Metoda Kornel i Radek: przesunięcie linii i spacje (DOCX)

Uruchom `python Main.py` i wybierz zakładkę „Kornel i Radek”. W podzakładce „Kodowanie” wybierz plik DOCX i wpisz wiadomość. Następnie wybierz liczbę bitów przesunięcia linii (od `1` do `4`, domyślnie `3`) i wskaż nowy plik wynikowy. Licznik pod polem wiadomości pokazuje jej długość i pojemność nośnika w bajtach, a za długa wiadomość zostaje odrzucona przed zapisem. W podzakładce „Dekodowanie” wybierz zapisany plik i ustaw tę samą liczbę bitów, aby odczytać wiadomość. Oryginalny plik nie jest potrzebny do odczytu.

Wykorzystywane są kolejne niepuste akapity dokumentu, także w tabelach. Każdy akapit niesie bity w trzech kanałach, zawsze w tej samej kolejności:

- **Przesunięcie linii:** cały akapit jest przesuwany w pionie przez właściwość Worda „położenie” (`w:position`). `k` bitów wybiera jeden z 2^k poziomów z pominięciem zera, np. dla `k = 3` od −2 pt do +2 pt co 0,5 pt.
- **Spacje między słowami:** każda spacja przed ostatnim słowem akapitu to jeden bit. Zwykła spacja (U+0020) oznacza `0`, a wąska spacja (U+2009) oznacza `1`.
- **Spacje końcowe:** oryginalne spacje końcowe są usuwane, a na ich miejsce trafia `TRAIL = 8` nowych, kodowanych tak samo jak spacje między słowami.

Strumień zaczyna się 16-bitową sygnaturą „KR” i 32-bitową długością wiadomości. Wiadomość jest zapisywana w UTF-8, więc może zawierać polskie znaki i emoji. Akapit daje `k + S + 8` bitów, gdzie `S` to liczba spacji między jego słowami. Przykładowo 40 krótkich akapitów mieści około 116 B przy `k = 3`. Nieużyte akapity pozostają bez zmian. Tekst, formatowanie, układ strony, grafiki i tabele są zachowane.

Przy odczycie dekoder dopasowuje przesunięcie każdego akapitu do najbliższego poziomu i czyta rodzaj każdej spacji. Brak sygnatury oznacza brak wiadomości albo inną liczbę bitów niż przy kodowaniu. Plik przetrwa ponowne zapisanie w LibreOffice. Edycja tekstu, autokorekta, „Znajdź i zamień” na spacjach albo eksport do PDF lub TXT może uszkodzić wiadomość. Przesunięcie ±0,5 pt jest praktycznie niewidoczne, ale od `k = 3` nierówne odstępy można zauważyć. Spacje końcowe widać po włączeniu znaków formatowania (¶). Metoda nie szyfruje ukrytych danych.