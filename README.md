# Photo Tagger – Notatki z developmentu

## Cel projektu

Desktopowa aplikacja w Pythonie do automatycznego tagowania zdjęć przy użyciu modeli AI działających **lokalnie** (bez API, bez internetu po pobraniu modeli). Użytkownik wrzuca zdjęcie, aplikacja wykrywa co jest na zdjęciu i zapisuje tagi do lokalnej bazy SQLite.

---

## Stack technologiczny

| Technologia | Rola |
|---|---|
| Python 3.12 | język projektu |
| tkinter | GUI (wbudowany w Python) |
| Pillow | wyświetlanie i obracanie zdjęć |
| sqlite3 | baza danych (wbudowana w Python) |
| transformers (HuggingFace) | ładowanie modeli AI |
| torch (PyTorch) | backend ML |

---

## Modele AI – co testowałem i dlaczego zrezygnowałem

### 1. YOLOv8 (ultralytics) – ❌ odrzucony

**Co robi:** Wykrywa obiekty na zdjęciu i rysuje bounding boxy (prostokąty) wokół nich.

**Problem:** YOLO jest wytrenowany na datasecie COCO, który zawiera tylko **80 predefiniowanych klas** (person, car, dog, chair itd.). Oznacza to, że:
- Zdjęcie książki → wykrywał „person" bo zobaczył okładkę z twarzą
- Zdjęcie Pałacu Kultury → nic nie wykrył, bo „palace" nie jest w COCO
- Zdjęcie jedzenia, krajobrazu, wnętrza → bardzo słabe wyniki
- Bounding boxy na statycznych zdjęciach w galerii były zbędnym obciążeniem

**Wniosek:** YOLO świetnie sprawdza się w real-time detekcji (np. kamery), ale nie nadaje się do ogólnego tagowania zdjęć z nieznaną zawartością.

---

### 2. BLIP Large (Salesforce) – ❌ odrzucony

**Co robi:** Generuje opis tekstowy zdjęcia (image captioning) oraz odpowiada na pytania o zdjęcie (Visual Question Answering).

**Problem 1 – halucynacje:** Model generował kompletnie błędne opisy, np. dla zdjęcia ptaków w powietrzu zwrócił:
```
"there is a spider that is flying in the sky with a lot of birds"
```

**Problem 2 – pytania wracały jako tagi:** BLIP przy odpowiadaniu na pytanie doklejał treść pytania do odpowiedzi, więc po splitowaniu tekstu na słowa powstawały tagi: `what`, `objects`, `image`, `location`, `happening` – całkowicie bezużyteczne.

**Problem 3 – rozmiar i czas:** Model waży ~900MB, czas ładowania przy pierwszym uruchomieniu był długi, a czas analizy jednego zdjęcia wynosił kilkanaście sekund.

**Problem 4 – złożoność parsowania:** Żeby wyciągnąć sensowne tagi z generowanego tekstu, trzeba było napisać dodatkowy kod (stopwords, regex, filtry długości słów). To dodało złożoności bez gwarancji jakości.

**Wniosek:** BLIP jest ciekawy jako narzędzie do opisów, ale nie jako silnik tagowania.

---

### 3. CLIP ViT-B/32 (OpenAI) – ✅ wybrany

**Co robi:** Porównuje zdjęcie z listą kandydatów tekstowych i zwraca **prawdopodobieństwo** dopasowania każdego kandydata do zdjęcia.

**Dlaczego działa lepiej:**

- **Deterministyczny i kontrolowany** – nie halucynuje, bo nie generuje tekstu. Wybiera tylko z podanej listy.
- **Szeroki zakres** – lista kandydatów może zawierać cokolwiek: jedzenie, architektę, zwierzęta, przedmioty codziennego użytku, krajobrazy, sport. Nie jest ograniczona do 80 klas jak YOLO.
- **Zrozumienie kontekstu** – CLIP rozumie semantykę, nie tylko piksele. Widząc Pałac Kultury nie musi znać tej konkretnej budowli – rozpozna ją jako `palace`, `monument`, `building`, `architecture`.
- **Lekki i szybki** – model ViT-B/32 waży ~600MB, ale analiza jednego zdjęcia trwa 1–3 sekundy.
- **Prosta integracja** – wynik to lista par (kandydat, prawdopodobieństwo), bez potrzeby dodatkowego parsowania.

**Jak działa (wyjaśnienie dla frontendowca):**

```
CLIP to jak test wielokrotnego wyboru.
Ty piszesz pytania i odpowiedzi A/B/C/D (CLIP_CANDIDATES).
CLIP patrzy na zdjęcie i zaznacza które odpowiedzi pasują.
```

**Lista kandydatów** (`CLIP_CANDIDATES`) zawiera ~250 pozycji podzielonych na kategorie:
- ludzie i ciało, zwierzęta, dom / wnętrza, jedzenie i napoje,
- elektronika, transport, architektura, natura, sport, sztuka i inne

---

## Architektura aplikacji

```
photo_tagger/
├── main.py       # GUI (tkinter) – okno, galeria, podgląd, przyciski
├── detector.py   # logika CLIP – wykrywanie tagów
├── database.py   # SQLite – zapis/odczyt zdjęć i tagów
└── photos.db     # baza danych (tworzy się automatycznie)
```

### Przepływ danych

```
Użytkownik klika "+ Dodaj zdjęcie"
        ↓
filedialog → wybór pliku
        ↓
wątek w tle → detect_objects(path)  ← CLIP analizuje zdjęcie
        ↓
tags = [{"tag": "mountain", "confidence": 0.42}, ...]
        ↓
add_photo(path) + add_tags(photo_id, tags)  ← zapis do SQLite
        ↓
odświeżenie galerii i listy tagów w GUI
```

---

## Funkcje aplikacji

- ✅ Wrzucanie zdjęć i automatyczne tagowanie przez CLIP
- ✅ Galeria miniaturek ze scrollem
- ✅ Filtrowanie zdjęć po tagach (panel lewy)
- ✅ Podgląd zdjęcia po kliknięciu miniaturki
- ✅ Wyświetlanie tagów z poziomem pewności (confidence)
- ✅ Obracanie zdjęcia w podglądzie (↺ ↻) z możliwością zapisu do pliku
- ✅ Usuwanie zdjęcia z bazy (z opcją usunięcia pliku z dysku)
- ✅ Duplikaty dozwolone – to samo zdjęcie można dodać wielokrotnie
- ✅ Animowany pasek postępu podczas analizy
- ✅ Informacja który model przeanalizował zdjęcie

---

## Napotkane problemy techniczne

### Problem z Pythonem na macOS
Systemowy Python 3.9 (`/usr/bin/python3`) z Xcode miał błąd z biblioteką `libexpat`:
```
ImportError: dlopen(...pyexpat...): Symbol not found: _XML_SetAllocTrackerActivationThreshold
```
**Rozwiązanie:** Instalacja Pythona 3.12 przez `pyenv` i stworzenie virtualenv.

### Problem z tkinter
Homebrew Python nie zawiera Tk domyślnie:
```
ModuleNotFoundError: No module named '_tkinter'
```
**Rozwiązanie:** `brew install python-tk@3.12`

### Problem z macOS 26 i PyTorch
Systemowy pip instalował PyTorch wymagający macOS 26, podczas gdy system był na macOS 16:
```
macOS 26 (2602) or later required, have instead 16 (1602)
```
**Rozwiązanie:** Użycie PyTorcha zainstalowanego w venvie z Pythonem 3.12.

---

## Uruchomienie projektu

```bash
# 1. Wejdź do folderu z venvem
cd photo_tagger

# 2. Aktywuj środowisko wirtualne
source venv/bin/activate

# 3. Uruchom aplikację
python main.py
```

Przy pierwszym uruchomieniu CLIP pobierze model (~600MB) – chwilę poczekaj.

