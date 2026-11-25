# Metoda Kornel i Radek – dokumentacja

25.11.2026 · @Kornel

## Opis metody

Metoda Kornel i Radek ukrywa wiadomość w dokumencie Word (DOCX), wykorzystując jednocześnie trzy kanały: pionowe przesunięcie linii, wąskie spacje między słowami oraz spacje na końcu linii. Treść dokumentu pozostaje bez zmian, a różnice są na granicy dostrzegalności.

Metodę implementuje moduł `Kornel_I_Radek.py`, a w aplikacji „Steganografia” obsługuje ją zakładka „Kornel i Radek” z podzakładkami Kodowanie i Dekodowanie. Wiadomość może zawierać dowolne znaki Unicode (polskie litery, emoji), bo jest zapisywana w UTF-8.

## Kanały ukrywania danych

Każdy niepusty akapit dokumentu niesie bity w trzech kanałach, zawsze w tej samej kolejności.

### 1. Przesunięcie linii (wielobitowe)

Cały akapit jest podnoszony lub obniżany przez właściwość Worda „położenie” (`w:position`, w pół-punktach), ustawianą na każdym fragmencie tekstu akapitu. Jedna linia zapisuje *k* bitów (domyślnie 3), czyli jeden z 2^*k* poziomów. Poziom 0 jest pomijany, żeby niezakodowana linia nie była mylona z zakodowaną.

| Bity na linię (k) | Poziomy \[pół-punkty\] | Zakres przesunięcia |
| --- | --- | --- |
| 1 | −1, +1 | ±0,5 pt |
| 2 | −2 … −1, +1 … +2 | ±1 pt |
| 3 (domyślnie) | −4 … −1, +1 … +4 | ±2 pt |
| 4 | −8 … −1, +1 … +8 | ±4 pt |

Wartość bitów *v* (od 0 do 2^*k* − 1) wybiera poziom o indeksie *v* z listy w kolejności rosnącej. Dla k = 3 bity `000` dają −4 (w dół o 2 pt), a `111` dają +4 (w górę o 2 pt). Dekoder dopasowuje odczytaną wartość do najbliższego poziomu.

### 2. Spacje między słowami

Każda spacja przed ostatnim słowem akapitu to jeden bit.

| Znak | Kod Unicode | Bit |
| --- | --- | --- |
| zwykła spacja | U+0020 | 0 |
| wąska spacja (thin space) | U+2009 | 1 |

### 3. Spacje na końcu linii

Koder usuwa istniejące spacje końcowe akapitu i dopisuje dokładnie `TRAIL` = 8 nowych, kodowanych tak samo jak w kanale 2. Edytory nie zawijają linii z powodu spacji końcowych, więc „wiszą” one niewidocznie za prawym marginesem.

## Format strumienia bitów

Wiadomość jest zapisywana jako jeden ciągły strumień bitów (najstarszy bit pierwszy), poprzedzony 48-bitowym nagłówkiem.

| Pole | Rozmiar | Zawartość |
| --- | --- | --- |
| Sygnatura | 16 bitów | `0x4B52` (ASCII „KR”), pozwala odróżnić zakodowany plik od zwykłego |
| Długość | 32 bity | liczba bajtów wiadomości w UTF-8 |
| Treść | 8 × długość | wiadomość zakodowana w UTF-8 |

Bity są rozkładane na kolejne akapity w porządku dokumentu. W obrębie akapitu kolejność jest stała:

1. *k* bitów przesunięcia linii,
2. po jednym bicie na każdą spację między słowami, od lewej,
3. 8 bitów spacji końcowych.

Brane są pod uwagę wszystkie akapity treści, także w tabelach i w tekstach hiperłączy. Akapity puste lub zawierające same spacje są pomijane. Nagłówki i stopki strony nie są używane.

Gdy strumień kończy się w połowie akapitu, brakujące bity przesunięcia i spacji końcowych są dopełniane zerami, a pozostałe spacje między słowami zostają bez zmian. Kolejne akapity nie są modyfikowane.

## Pojemność nośnika

Każdy niepusty akapit daje k + S + 8 bitów, gdzie S to liczba spacji przed jego ostatnim słowem. Po odjęciu 48 bitów nagłówka pojemność w bajtach wynosi:

```latex
C = \left\lfloor \frac{\sum_{p} \left(k + S_p + 8\right) - 48}{8} \right\rfloor
```

Dla dokumentu testowego z 40 krótkimi akapitami (ok. 12 słów każdy) pojemność wyniosła:

| Bity przesunięcia (k) | Pojemność \[B\] |
| --- | --- |
| 1 | 105 |
| 2 | 110 |
| 3 | 116 |
| 4 | 121 |

Pojemność liczy się w bajtach UTF-8: litera ASCII zajmuje 1 B, polska litera 2 B, emoji 4 B. Najwięcej daje długi tekst ciągły, bo głównym kanałem są spacje między słowami. Zwiększenie k podnosi pojemność tylko o k bitów na akapit.

## API modułu Kornel_I_Radek

Moduł udostępnia trzy funkcje publiczne. Wszystkie błędy wynikające z danych zgłasza wyjątkiem `ValueError` z komunikatem po polsku.

| Funkcja | Zwraca | Opis |
| --- | --- | --- |
| `encode(carrier, message, out, shift_bits=3)` | `None` | Ukrywa `message` w pliku `carrier` i zapisuje wynik do `out`. Sprawdza pojemność przed zapisem. |
| `decode(carrier, shift_bits=3)` | `str` | Odczytuje ukrytą wiadomość. `shift_bits` musi być taki sam jak przy kodowaniu. |
| `capacity(carrier, shift_bits=3)` | `int` | Maksymalna długość wiadomości w bajtach UTF-8. |

Przykład użycia:

```python
import Kornel_I_Radek as KR

print(KR.capacity("nosnik.docx"))            # np. 116
KR.encode("nosnik.docx", "Tajna wiadomość", "wynik.docx", shift_bits=3)
print(KR.decode("wynik.docx", shift_bits=3))  # Tajna wiadomość
```

Stałe konfiguracyjne na początku pliku (zmiana wymaga użycia tych samych wartości przy kodowaniu i dekodowaniu):

| Stała | Wartość | Znaczenie |
| --- | --- | --- |
| `SHIFT_BITS` | 3 | domyślna liczba bitów przesunięcia linii (dozwolone 1–6) |
| `TRAIL` | 8 | liczba spacji dopisywanych na końcu akapitu |
| `SHORT` | `"\u2009"` | znak wąskiej spacji (bit 1) |
| `MAGIC` | `0x4B52` | sygnatura „KR” w nagłówku |
| `LEN_BITS` | 32 | rozmiar pola długości w bitach |

## Obsługa w aplikacji

W aplikacji metodę obsługuje zakładka „Kornel i Radek” z dwiema podzakładkami. Ikona „?” w prawym górnym rogu okna pokazuje skróconą instrukcję.

### Kodowanie

1. Kliknij „Wybierz…” i wskaż plik DOCX będący nośnikiem.
2. Wpisz wiadomość. Pod polem licznik pokazuje na bieżąco „Długość wiadomości: X B / pojemność nośnika: Y B”.
3. Wybierz liczbę bitów przesunięcia linii (1–4, domyślnie 3). Licznik przelicza pojemność po każdej zmianie.
4. Kliknij „Zakoduj” i wskaż miejsce zapisu pliku wynikowego.

Gdy wiadomość jest dłuższa niż pojemność, licznik zmienia kolor na czerwony z dopiskiem „za długa!”, a „Zakoduj” pokazuje błąd jeszcze przed oknem zapisu. Po udanym zapisie pole wyniku pokazuje ścieżkę pliku i liczbę ukrytych bajtów.

### Dekodowanie

1. Wybierz zakodowany plik DOCX.
2. Ustaw tę samą liczbę bitów przesunięcia co przy kodowaniu.
3. Kliknij „Odkoduj”. Wiadomość pojawi się w polu „Odczytana wiadomość”.

Liczba bitów przesunięcia nie jest zapisywana w pliku. Odbiorca musi ją znać, podobnie jak tryb przesunięcia w metodzie LSC.

## Komunikaty błędów i diagnostyka

Najczęstszą przyczyną nieudanego dekodowania jest inna liczba bitów przesunięcia niż przy kodowaniu.

| Komunikat | Kiedy | Co zrobić |
| --- | --- | --- |
| Wiadomość jest pusta. | kodowanie bez treści | wpisać wiadomość |
| Za mały nośnik: wiadomość ma X B, a zmieści się najwyżej Y B. | wiadomość przekracza pojemność | skrócić wiadomość, wybrać dłuższy dokument lub zwiększyć k |
| Liczba bitów przesunięcia musi być z zakresu 1–6. | błędny parametr `shift_bits` | podać wartość 1–6 |
| Nośnik nie zawiera ukrytej wiadomości (albo ustawiono inną liczbę bitów przesunięcia niż przy kodowaniu). | brak sygnatury „KR” | sprawdzić liczbę bitów i czy wybrano plik wynikowy, a nie oryginalny nośnik |
| Zapisana długość wiadomości wynosi 0 – plik jest uszkodzony. | nagłówek z zerową długością | zakodować ponownie |
| Zapisana długość wiadomości (X B) przekracza ilość danych w nośniku (Y B)… | część tekstu usunięto lub zmieniono po zakodowaniu | użyć nieedytowanego pliku wynikowego |
| Odczytane dane nie są poprawnym tekstem UTF-8… | bity treści zostały zmienione | użyć nieedytowanego pliku wynikowego |

Skrypt diagnostyczny próbuje wszystkich liczb bitów i pokazuje, który plik modułu jest faktycznie ładowany. Uruchomienie: `python diag.py zakodowany.docx`.

```python
import sys
import Kornel_I_Radek as KR

path = sys.argv[1]
print("Moduł:", KR.__file__)
for k in range(1, 7):
    try:
        print(f"bity={k}: OK ->", repr(KR.decode(path, k)))
    except Exception as e:
        print(f"bity={k}: {type(e).__name__}: {e}")
```

## Ograniczenia, odporność i wykrywalność

Metoda przetrwa otwarcie i zapisanie pliku w edytorze, ale nie przetrwa zmian w tekście ani konwersji do innego formatu.

**Odporność**

- Plik po ponownym zapisaniu w LibreOffice dekoduje się poprawnie (sprawdzone).
- Ponowne zapisanie w Wordzie nie było testowane.
- Autokorekta, „Znajdź i zamień” na spacjach albo usunięcie lub dopisanie akapitu przed końcem wiadomości niszczy dane.
- Eksport do PDF, kopiowanie tekstu do innego dokumentu lub zapis jako TXT gubi przesunięcie linii, a często także wąskie spacje.
- Liczba bitów przesunięcia nie jest zapisana w pliku. Odbiorca musi ją znać.

**Wykrywalność**

- Przesunięcie ±0,5 pt (k = 1) jest praktycznie niewidoczne. Przy ±2 pt (k = 3) nierówne odstępy między liniami można zauważyć przy uważnym oglądaniu, a przy k ≥ 4 są wyraźne.
- Wąska spacja jest nieco węższa od zwykłej. W tekście justowanym zwykłe spacje się rozciągają, a wąskie mogą nie, co zwiększa różnicę.
- Po włączeniu w Wordzie znaków formatowania (¶) widać kropki spacji końcowych za końcem tekstu. Zmniejszenie `TRAIL` do 2–4 ogranicza ten efekt kosztem pojemności.
- Analiza XML pliku od razu ujawnia nietypowe właściwości `w:position` i znaki U+2009. Metoda nie szyfruje wiadomości: przy potrzebie poufności treść należy zaszyfrować przed ukryciem.

**Inne ograniczenia**

- Kodowanie nadpisuje celowe przesunięcia tekstu („położenie”) w użytych akapitach.
- Nagłówki i stopki strony oraz pola tekstowe poza treścią nie są wykorzystywane.
- Usuwane są oryginalne spacje końcowe w akapitach użytych do kodowania.

## Instalacja i testy

Moduł wymaga tylko biblioteki `python-docx` w wersji co najmniej 1.1. Testowano go na wersji 1.2.0.

1. Umieść `Kornel_I_Radek.py` w tym samym folderze co `Main.py`.
2. Dopisz do `requirements.txt` linię `python-docx>=1.1` i uruchom `pip install -r requirements.txt`.
3. W `Main.py` zaimportuj moduł jako `import Kornel_I_Radek as KornelRadek`.

**Przeprowadzone testy**

| Test | Wynik |
| --- | --- |
| Kodowanie i dekodowanie wiadomości z polskimi znakami i emoji dla k = 1, 2, 3, 4 | wiadomość odczytana bez zmian |
| Zachowanie formatowania (pogrubienie) po zakodowaniu | zachowane |
| Dekodowanie niezakodowanego pliku | błąd „Nośnik nie zawiera ukrytej wiadomości” |
| Dekodowanie z inną liczbą bitów niż przy kodowaniu | ten sam błąd z podpowiedzią o liczbie bitów |
| Wiadomość dłuższa niż pojemność (5000 B) | błąd „Za mały nośnik” z maksymalną długością |
| Plik z usuniętą częścią akapitów | błąd zbyt dużej zapisanej długości (54 B wobec 9 B) |
| 80 akapitów kończących się przy prawym marginesie | liczba linii i stron bez zmian (LibreOffice) |
