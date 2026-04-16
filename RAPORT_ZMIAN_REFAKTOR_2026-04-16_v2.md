# Raport zmian — refaktor 1:1 względem docelowej wizji architektury

## Założenie
Ta wersja projektu została przebudowana od nowa na bazie starej paczki tak, aby odpowiadała raportowi docelowej architektury.

## Najważniejsze zmiany

### 1. Nowy pipeline w `main.py`
Pipeline działa teraz jawnie jako:
1. parser,
2. analiza fraz i slotów,
3. teoria i tonacja,
4. planowanie frazowe,
5. harmonizer,
6. eksport.

To realizuje porządek:
**struktura utworu → wiedza teoretyczna → kandydaci → plan frazowy → scoring → wybór akordu**.

### 2. `models.py` jako centrum danych
Dodano i uporządkowano warstwę modeli:
- `HarmonizationSettings`,
- `KeyInfo`,
- `PhraseInfo` z polami slotowymi,
- `HarmonicSlot` z pełnymi metadanymi pozycyjnymi,
- `ChordCandidate`,
- `SlotPlanExpectation`,
- `PhrasePlan`,
- `PieceModel` rozszerzony o `settings`, `key_info`, `candidate_pool`, `phrase_plans`, `slot_plan_map`.

### 3. `phrases.py` przejęło pełną analizę strukturalną
Do `phrases.py` przeniesiono i uporządkowano:
- detekcję fraz,
- tworzenie slotów,
- podział wg gęstości harmonizacji,
- przypisanie nut do slotów,
- przypisanie slotów do fraz,
- zapis pól typu `slotInPhrase`, `phraseLength`, `slotsToEnd`, `formalLabel`.

### 4. `theory.py` przejęło pełną warstwę teorii
`theory.py` zawiera teraz:
- wiedzę o stopniach i funkcjach,
- obsługę tonacji ręcznej i automatycznej,
- wzorce kadencji 2/3/4-slotowych,
- generowanie pełnej puli kandydatów akordowych.

### 5. `rules.py` zawiera wyłącznie scoring
Usunięto scoring z `config.py`.
`rules.py` jest teraz jedynym miejscem, gdzie znajdują się:
- wagi,
- profile wag,
- reguły oceny,
- składanie końcowego wyniku punktowego.

### 6. `planner.py` planuje frazy i kadencje
Planner:
- wybiera typ kadencji dla frazy,
- wybiera jej rozpiętość (2/3/4 sloty),
- zapisuje oczekiwania dla początku i końca frazy,
- buduje `PhrasePlan` i `SlotPlanExpectation`.

### 7. `harmonizer.py` został odchudzony do roli orkiestratora
Harmonizer:
- nie tworzy slotów,
- nie wykrywa tonacji,
- nie generuje kandydatów,
- nie planuje kadencji,
- nie naprawia braków w pipeline.

Jeżeli prerequisites nie są spełnione, zgłasza błąd.

### 8. `config.py` zawiera już tylko konfigurację
W `config.py` pozostawiono:
- presety,
- profile użytkownika,
- gęstość harmonizacji,
- złożoność,
- ustawienia trybu tonacji,
- parametry eksportu.

Usunięto z niego scoring.

### 9. `app.py` pozostawiono bez zmian
Zgodnie z założeniem UI i Flask nie były przebudowywane.

### 10. `tonality.py` pozostawiono wyłącznie jako warstwę kompatybilności
Zgodnie z nową architekturą logika tonacji należy do `theory.py`.
`tonality.py` tylko deleguje importy dla kompatybilności.

## Uwaga techniczna
Kod został przebudowany architektonicznie. W tym środowisku nie było możliwe pełne uruchomienie pipeline'u z `music21` + Flask UI, ale składnia modułów została sprawdzona kompilacją Pythona.
