# Raport do inżynierki

Kompendium wiedzy o projekcie harmonizatora melodii z MusicXML, przygotowane jako materiał do pisania rozdziału projektowo-implementacyjnego pracy inżynierskiej.

## 1. Charakter projektu

Projekt realizuje automatyczną harmonizację jednogłosowej melodii zapisanej w formacie MusicXML. System pobiera plik wejściowy, parsuje jego strukturę, buduje wewnętrzną reprezentację danych, wykrywa tonację i frazy, tworzy siatkę miejsc decyzji harmonicznych, generuje kandydatów akordowych, ocenia ich według zestawu heurystyk muzycznych, wybiera najlepsze rozwiązania, a na końcu eksportuje wynik w postaci pliku MusicXML, opcjonalnie PDF oraz opcjonalnej realizacji głosów.

Najkrótszy opis pipeline'u jest zapisany wprost w kodzie:

> `Uruchamia cały pipeline: parsowanie → tonacja → frazy → harmonizacja → eksport.`  
Źródło: [main.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/main.py:17)

oraz:

> `Pipeline:`  
> `1. Utwórz sloty harmoniczne.`  
> `2. Przypisz do nich nuty melodii i kontekst frazowy.`  
> `3. Zbuduj prosty plan harmoniczny (kadencje, początek utworu).`  
> `4. Wygeneruj kandydatów diatonicznych.`  
> `5. Oceń kandydatów z użyciem jawnych reguł.`  
> `6. Wybierz najlepszy akord i zapisz go do kontekstu.`  
Źródło: [harmonizer.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/harmonizer.py:1)

To bardzo dobrze porządkuje opis projektu, bo pokazuje, że system ma architekturę etapową, a nie zbiór niezależnych heurystyk uruchamianych ad hoc.

## 2. Pipeline i przepływ danych

### 2.1. Ogólny przebieg

Przepływ danych w systemie wygląda następująco:

1. `parse_musicxml()` wczytuje plik wejściowy i buduje obiekt `PieceModel`.
2. `detect_key()` weryfikuje tryb i ustala bazową tonację roboczą.
3. `detect_phrases()` wyznacza granice i kształty fraz.
4. `harmonize()` tworzy sloty harmoniczne, wiąże z nimi nuty i kontekst formalny, a następnie wybiera akord dla każdego slotu.
5. `export_harmonized()` zapisuje wynik do formatu wyjściowego.

W kodzie jest to zrealizowane liniowo:

- parsowanie: [main.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/main.py:26)
- tonacja: [main.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/main.py:32)
- frazy: [main.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/main.py:37)
- harmonizacja: [main.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/main.py:43)
- eksport: [main.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/main.py:49)

### 2.2. Przepływ danych między modułami

Najważniejszym kontenerem danych jest `PieceModel`, który jest stopniowo uzupełniany o kolejne poziomy kontekstu:

- po parsowaniu zawiera takty i nuty,
- po analizie tonacji zawiera zweryfikowaną tonikę i tryb,
- po analizie fraz zawiera listę `PhraseInfo`,
- po harmonizacji zawiera listę `HarmonicSlot`, a w nich wybrane akordy.

To odpowiada idei „zunifikowanego systemu przechowywania i reprezentacji danych”. Kod nie przekazuje między funkcjami wielu luźnych struktur, tylko jeden wspólny model utworu.

Dobry cytat do pracy:

> `Algorytm pobiera konieczne informacje z wejściowego pliku ... a następnie w miarę postępowania procesu, uzupełnia go o potrzebne do harmonizacji informacje (kontekst).`

W implementacji dokładnie temu odpowiada zestaw pól w `PieceModel`:

- `measures`
- `all_notes`
- `key_tonic`
- `key_mode`
- `phrases`
- `harmonic_slots`

Źródło: [models.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/models.py:117)

## 3. Odpowiedzi do rozdziału 3

### 3.1 Założenia projektowe

Projekt został świadomie zaprojektowany jako system prosty, czytelny i obronialny metodologicznie. Nie celem było stworzenie pełnego systemu harmonii czterogłosowej, lecz algorytmu, który:

1. korzysta z jawnych i interpretowalnych reguł muzycznych,
2. działa deterministycznie lub prawie deterministycznie,
3. daje wynik nadający się do demonstracji w notacji muzycznej,
4. ma strukturę łatwą do opisania w pracy inżynierskiej.

Takie założenie widać bezpośrednio w komentarzach modułów:

> `Wersja uproszczona pod pracę inżynierską`  
Źródło: [config.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/config.py:1)

> `Wersja obronowa`  
Źródło: [phrases.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/phrases.py:1)

> `Jawna baza wiedzy muzycznej używana przez harmonizer.`  
Źródło: [theory.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/theory.py:1)

Założenia projektowe można więc opisać tak:

- jawność wiedzy muzycznej,
- ograniczenie złożoności,
- etapowy pipeline,
- czytelna reprezentacja danych,
- możliwość prezentacji wyników w interfejsie i eksporcie.

### 3.2 Wykorzystane narzędzia

Najważniejsze narzędzia i technologie:

1. Python jako język implementacji.
2. Biblioteka `music21` do parsowania, analizy i eksportu struktur muzycznych.
3. Flask do przygotowania prostego interfejsu WWW.
4. MusicXML jako format wejścia i podstawowy format wyjścia.

Dowody w kodzie:

- parsowanie MusicXML przez `music21.converter.parse(...)`: [parser.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/parser.py:24)
- reprezentacja metrum przez `music21.meter.TimeSignature`: [models.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/models.py:13)
- interfejs Flask: [app.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/app.py:1)
- eksport MusicXML i PDF: [exporter.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/exporter.py:14)

Można to opisać w pracy tak:

> System został zaimplementowany w języku Python. Do przetwarzania danych muzycznych wykorzystano bibliotekę Music21, która umożliwia parsowanie plików MusicXML, odczyt metrum i tonacji, a także zapis wyników. Do warstwy demonstracyjnej użyto frameworka Flask, co pozwoliło przygotować prosty interfejs użytkownika do uruchamiania algorytmu i przeglądu rezultatów.

### 3.3 Implementacja algorytmu harmonizacji

#### 3.3.1 Architektura systemu i przepływ danych

Architektura systemu jest modułowa. Poszczególne odpowiedzialności są rozdzielone między pliki:

- `parser.py` – parsowanie pliku wejściowego,
- `models.py` – reprezentacja danych,
- `tonality.py` – wiedza o tonacjach i detekcja trybu,
- `phrases.py` – detekcja fraz,
- `harmonizer.py` – orkiestracja procesu harmonizacji,
- `planner.py` – plan harmoniczny wynikający z formy,
- `theory.py` – baza wiedzy akordowej i kandydaci,
- `rules.py` – scoring,
- `exporter.py` – eksport,
- `app.py` – interfejs użytkownika.

Dobry cytat:

> `Harmonizer jest teraz orkiestratorem: wywołuje kolejne etapy, ale nie ukrywa logiki w setkach helperów.`  
Źródło: [harmonizer.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/harmonizer.py:23)

Przepływ danych jest liniowy i przewidywalny:

`plik MusicXML -> PieceModel -> analiza tonacji -> analiza fraz -> sloty harmoniczne -> kandydaci akordowi -> scoring -> wybrane akordy -> eksport`

#### 3.3.2 Reprezentacja danych

Reprezentacja danych jest jedną z mocniejszych stron projektu. Zamiast operować bezpośrednio na obiektach biblioteki `music21` w całym systemie, projekt wprowadza własne jawne struktury:

- `NoteInfo`,
- `MeasureInfo`,
- `PhraseInfo`,
- `ChordCandidate`,
- `HarmonicSlot`,
- `PieceModel`.

Źródło: [models.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/models.py:42)

Znaczenie tych struktur:

- `NoteInfo` przechowuje informacje o pojedynczym zdarzeniu melodycznym, w tym `pitch_class`, `duration_ql`, `beat_strength`, `global_offset`.
- `MeasureInfo` opisuje takt i gromadzi jego nuty.
- `PhraseInfo` opisuje zasięg formalny frazy.
- `ChordCandidate` opisuje potencjalny akord, jego skład dźwiękowy, funkcję harmoniczną i ocenę.
- `HarmonicSlot` reprezentuje jeden punkt decyzji harmonicznej.
- `PieceModel` spina wszystkie warstwy informacji w jeden kontener.

To odpowiada sformułowaniu:

> „implementacja struktury danych - kontenera zawierającego tablice z danymi”

Dokładnie tym kontenerem jest `PieceModel`, a `harmonic_slots` i `all_notes` są jego głównymi tablicami roboczymi.

#### 3.3.3 Analiza fraz

Analiza fraz została zaprojektowana jako heurystyczna, ale czytelna. W komentarzu modułu zapisano:

> `opiera granice fraz na kilku jasnych przesłankach:`  
> `1. pauza,`  
> `2. długa nuta końcowa,`  
> `3. duży skok do następnego taktu,`  
> `4. preferencja długości 4-taktowej,`  
Źródło: [phrases.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/phrases.py:1)

Implementacja składa się z trzech głównych etapów:

1. obliczenie `boundary_scores`: [phrases.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/phrases.py:38)
2. globalny wybór granic metodą dynamic programming: [phrases.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/phrases.py:87)
3. budowa obiektów `PhraseInfo`: [phrases.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/phrases.py:124)

Ważne heurystyki:

- końcowa pauza lub długa nuta zwiększają prawdopodobieństwo granicy,
- duży skok między taktami wzmacnia hipotezę zakończenia frazy,
- ostatni takt zawsze domyka ostatnią frazę,
- pickup nie jest włączany do pierwszej frazy roboczej,
- finalny podział jest wybierany globalnie, a nie tylko lokalnie.

To można opisać jako uproszczoną analizę formalną opartą na sygnałach rytmicznych i melodycznych, w której lokalny scoring granic jest łączony z globalnym wyborem najlepszego podziału fraz metodą dynamic programming.

#### 3.3.4 Rytm i ruch harmoniczny

Rytm harmoniczny jest modelowany przez `HarmonicSlot`, czyli miejsca decyzji akordowej. Siatka slotów powstaje w `create_slots()`:

Źródło: [harmonizer.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/harmonizer.py:72)

System wspiera kilka trybów:

- `per_measure`,
- `per_beat`,
- `per_strong_beat`,
- `auto`.

W trybie automatycznym decyzja zależy m.in. od:

- długości dźwięków,
- pojawienia się nowych nut na silnych miejscach,
- gęstości rytmicznej melodii.

Wprost realizuje to logika:

- `Bardzo długa wartość -> 1 akord`
- `Nowa nuta na kolejnym silnym miejscu -> 2 akordy`
- `Bardzo gęsty rytm -> gęściej`

Źródło: [harmonizer.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/harmonizer.py:121)

Ruch harmoniczny jest dodatkowo wspierany przez:

- preferencje następstw funkcji: [theory.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/theory.py:18)
- premię za ruch podstaw: [theory.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/theory.py:162)

#### 3.3.5 Reguły i heurystyki

Reguły muzyczne są rozproszone, ale jawnie zorganizowane. Główne grupy:

1. zgodność dźwięków melodii z akordem,
2. preferencje formalne zależne od miejsca w frazie,
3. plan harmoniczny wymuszający kadencje,
4. progresja funkcyjna,
5. ruch podstaw,
6. kontrola monotonii,
7. kontrolowane użycie `V7` i akordów pożyczonych.

W `theory.py` zapisano:

> `jakie akordy są dostępne w tonacji,`  
> `jakie pełnią funkcje,`  
> `jakie kadencje dopuszczamy,`  
> `jakie następstwa są preferowane.`  
Źródło: [theory.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/theory.py:1)

Plan harmoniczny jest realizowany przez `PlannedMoment` i `build_harmonic_plan()`:

Źródło: [planner.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/planner.py:18)

Najważniejsze założenia planu:

- początek utworu: tonika,
- koniec utworu: `V-I`,
- końce fraz wewnętrznych: zależnie od strategii albo pełna kadencja, albo półkadencja.

#### 3.3.6 Scoring i wybór kandydatów

Scoring jest zebrany w `rules.py`. Najważniejszy cytat:

> `Każda reguła zwraca liczbę punktów. Harmonizer sumuje wyniki i wybiera kandydata z najwyższym łącznym wynikiem.`  
Źródło: [rules.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/rules.py:1)

W `score_candidate()` widać komplet kryteriów:

- `melody_fit`
- `phrase_position`
- `planned_degree`
- `progression`
- `root_motion`
- `variety`
- `primary_function`
- `color`
- `cadential_extension`

Źródło: [rules.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/rules.py:39)

Wybór finalnego akordu odbywa się w `harmonize()` przez prostą maksymalizację wyniku:

> `if score > best_score:`  
> `best_score = score`  
> `best_candidate = candidate`  
Źródło: [harmonizer.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/harmonizer.py:46)

To jest klasyczny lokalny wybór najlepszego kandydata w każdym slocie, z uwzględnieniem kontekstu poprzedniego akordu.

## 4. Jak projekt realizuje praktyczne zasady doboru akordów

### Zasada 1. Akord powinien wspierać dźwięki strukturalne melodii

Ta zasada jest realizowana bardzo bezpośrednio.

Po pierwsze, kandydaci są filtrowani pod kątem najważniejszych dźwięków:

> `Zachowuje kandydatów zgodnych z najważniejszymi dźwiękami melodii.`  
Źródło: [theory.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/theory.py:176)

Po drugie, scoring mocniej premiuje zgodność na silnych częściach taktu:

- `melody_in_chord_strong_beat`
- `melody_not_in_chord_strong_beat`

Źródło: [config.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/config.py:40), [rules.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/rules.py:61)

Oznacza to, że akcentowane metrycznie i ważniejsze dźwięki są traktowane jako strukturalne i powinny należeć do akordu.

### Zasada 2. Rytm harmoniczny powinien być spójny z metrum i frazą

Ta zasada jest realizowana przez tworzenie slotów na podstawie metrum i charakteru melodii:

- metryczne helpery: [models.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/models.py:18)
- siatka slotów: [harmonizer.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/harmonizer.py:72)

Projekt nie zmienia akordów przypadkowo, tylko wykorzystuje:

- silne części taktu,
- podział beatowy,
- początek taktu,
- charakter rytmiczny melodii.

To bardzo dobrze zgadza się z zasadą praktyczną.

### Zasada 3. Dźwięki obce są dopuszczalne, o ile prowadzą do dźwięków akordowych

Projekt nie modeluje jawnie każdego rodzaju nuty obcej w sensie klasycznej analizy kontrapunktycznej, ale realizuje tę zasadę pośrednio i wystarczająco dobrze dla uproszczonego systemu:

1. Na silnych pozycjach wymusza zgodność z akordem.
2. Na słabych pozycjach dopuszcza większą elastyczność scoringową.
3. Jeśli żaden kandydat nie pasuje idealnie, nie odrzuca wszystkiego na siłę, tylko pozostawia decyzję scoringowi.

Najlepszy cytat:

> `Nie wyrzucamy wszystkiego agresywnie. Jeśli nic nie pasuje, zwracamy pełną listę, a decyzję zostawiamy scoringowi.`  
Źródło: [theory.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/theory.py:179)

To oznacza, że system akceptuje krótkie dysonansowe lub ozdobne relacje, zwłaszcza na słabszych pozycjach.

### Zasada 4. Następstwo akordów powinno mieć kierunek funkcyjny

To jest realizowane bardzo jawnie. W `theory.py` zdefiniowano macierz preferowanych przejść funkcjonalnych:

- `T -> S`
- `T -> D`
- `S -> D`
- `D -> T`

Źródło: [theory.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/theory.py:18)

W `rules.py` przejścia te są używane jako składnik oceny:

Źródło: [rules.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/rules.py:100)

W praktyce daje to kierunek:

`stabilizacja -> napięcie -> rozwiązanie`

czyli dokładnie to, o czym mówi zasada teoretyczna.

### Zasada 5. Końce fraz są miejscami uprzywilejowanymi dla kadencji

To jest realizowane przez `build_harmonic_plan()`. Algorytm buduje punkty kotwiczące:

- `piece_start`
- `pre_cadence`
- `cadence_end`
- `half_cadence`

Źródło: [planner.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/planner.py:24)

Końce fraz mogą więc być domykane:

- pełną kadencją `V-I`,
- półkadencją kończącą się na `V`.

To jest niemal podręcznikowa realizacja tej zasady w systemie heurystycznym.

## 5. Jak projekt realizuje założenia z Twojego opisu

### 5.1 Zunifikowany system przechowywania i reprezentacji danych

To założenie jest spełnione bardzo dobrze. `PieceModel` jest centralnym kontenerem stanu, a reszta danych ma postać jawnych struktur dataclass.

Najlepsze miejsca w kodzie:

- definicje struktur: [models.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/models.py:42)
- tworzenie `PieceModel` przy parsowaniu: [parser.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/parser.py:29)
- późniejsze uzupełnianie `phrases` i `harmonic_slots`: [phrases.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/phrases.py:22), [harmonizer.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/harmonizer.py:67)

### 5.2 Analiza metrum i tonacji melodii

To założenie również jest spełnione:

- odczyt metrum z pliku: [parser.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/parser.py:38)
- obliczenie siły metrycznej przez `getAccentWeight`: [models.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/models.py:18)
- detekcja i korekta trybu tonacji: [tonality.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/tonality.py:151)

Warto podkreślić, że projekt nie tylko odczytuje tonację z pliku, ale ją jeszcze weryfikuje heurystycznie.

### 5.3 Detekcja fraz

To założenie jest zrealizowane w sposób uproszczony, ale spójny. Projekt wykorzystuje:

- długość frazy,
- sygnały rytmiczne,
- granice oddechowe,
- skoki interwałowe,
- zakończenia na tonice lub dominancie.

Nie ma natomiast pełnej korelacji rytmiczno-melodycznej w sensie rozbudowanego modelu statystycznego. Jeśli chcesz być bardzo precyzyjny w pracy, lepiej pisać o heurystycznej detekcji fraz opartej na kilku cechach niż o pełnej analizie korelacyjnej.

### 5.4 Implementacja reguł punktacji i wyboru kandydatów

To jest jedna z najlepiej zrealizowanych części projektu. System ocenia kandydatów wielokryterialnie i robi to w jawny sposób.

Najlepszy cytat:

> `Każda reguła zwraca liczbę punktów.`  
Źródło: [rules.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/rules.py:1)

Z punktu widzenia pracy możesz bezpiecznie napisać, że system implementuje zasady:

- zgodności z tonacją i systemem dur-moll,
- progresji funkcyjnej,
- kadencyjności,
- zmian napięć,
- różnorodności materiału harmonicznego.

### 5.5 Czytelna prezentacja wyników

To założenie też jest spełnione. Interfejs Flask:

- przyjmuje plik wejściowy,
- pozwala wybrać preset i parametry,
- uruchamia pipeline,
- pokazuje dane utworu, frazy i akordy,
- udostępnia wynik do podglądu i pobrania.

Najważniejsze miejsca:

- konfiguracja UI i presetów: [app.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/app.py:23)
- przyjęcie pliku i uruchomienie pipeline'u: [app.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/app.py:221)
- ekstrakcja danych do prezentacji: [app.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/app.py:177)
- eksport symboli akordowych i głosów: [exporter.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/exporter.py:55), [exporter.py](/Users/antonio/Downloads/harmonizer_clean_config_phrases_simplified/exporter.py:101)

## 6. Mocne strony projektu

1. Bardzo czytelny pipeline.
2. Jawna reprezentacja danych.
3. Dobra separacja odpowiedzialności między modułami.
4. Reguły scoringu dają się łatwo opisać i uzasadnić.
5. Projekt ma warstwę demonstracyjną i eksport.

## 7. Ograniczenia, które warto uczciwie opisać

To są ograniczenia, które lepiej nazwać wprost w pracy niż ukrywać:

1. System nie realizuje pełnej harmonii czterogłosowej w sensie akademickim.
2. Voice leading w `exporter.py` ma charakter demonstracyjny, nie jest osobnym algorytmem optymalizacyjnym.
3. Detekcja fraz jest heurystyczna, a nie oparta o złożony model formalny.
4. Akordy pożyczone są ograniczone do małego, kontrolowanego zestawu.
5. Wybór akordu jest lokalny, choć uwzględnia poprzedni kontekst.

Takie ograniczenia nie osłabiają projektu, jeśli przedstawisz go jako system heurystyczny, interpretowalny i inżyniersko uporządkowany.

## 8. Propozycja gotowego opisu całości projektu

Możesz wykorzystać poniższy akapit jako bazę do własnego tekstu:

> Zaimplementowany system realizuje automatyczną harmonizację jednogłosowej melodii zapisanej w formacie MusicXML. Architektura rozwiązania ma charakter etapowy. W pierwszym etapie dane wejściowe są parsowane i zamieniane na zunifikowaną reprezentację wewnętrzną obejmującą nuty, takty i informacje metryczne. Następnie wykonywana jest analiza tonacji oraz heurystyczna detekcja fraz. Na tej podstawie tworzona jest siatka slotów harmonicznych, czyli punktów decyzji akordowej. Dla każdego slotu generowany jest zbiór kandydatów harmonicznych zgodnych z bazową tonacją i przyjętym profilem harmonizacji. Kandydaci są oceniani za pomocą wielokryterialnego systemu punktacji uwzględniającego zgodność z melodią, miejsce w obrębie frazy, plan kadencyjny, kierunek funkcyjny progresji, ruch podstaw oraz różnorodność materiału harmonicznego. Najwyżej oceniony kandydat zostaje zapisany jako wynik dla danego slotu. Ostatecznie system eksportuje rezultat do postaci pliku MusicXML z symbolami akordowymi oraz opcjonalną realizacją dodatkowych głosów.

## 9. Najkrótsza mapa projektu

- wejście: `MusicXML`
- parser: `parser.py`
- model danych: `models.py`
- tonacja: `tonality.py`
- frazy: `phrases.py`
- sloty harmoniczne i orkiestracja: `harmonizer.py`
- plan formalny: `planner.py`
- kandydaci i wiedza muzyczna: `theory.py`
- scoring: `rules.py`
- eksport: `exporter.py`
- interfejs: `app.py`

## 10. Notatka metodologiczna

Jeśli chcesz pisać tekst maksymalnie uczciwie i mocno, najlepsze określenie tego systemu to:

**heurystyczny, etapowy system automatycznej harmonizacji melodii, oparty na jawnej reprezentacji danych i regułach inspirowanych harmonią funkcyjną.**

To zdanie bardzo dobrze oddaje charakter projektu i jest zgodne z tym, co faktycznie robi kod.
