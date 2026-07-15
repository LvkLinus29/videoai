# VideoCutterAI

VideoCutterAI ist eine lokale Linux-App, die Fotos und eine Audiodatei zu einem Video rendert.
Die Bedienung läuft im Browser, die Verarbeitung passiert lokal über `ffmpeg`.

## Funktionen

- Fotos per Drag-and-drop hinzufügen
- Bildvorschau mit Thumbnails
- Bilder per Drag-and-drop sortieren
- Bilder löschen
- Audio hochladen und direkt abspielen
- Ausgabe als `MP4`, `WebM`, `MKV` oder `MOV`
- Auflösung, FPS und Sekunden pro Foto einstellen
- Render-Fortschritt anzeigen
- Renderzeit anzeigen
- Einstellungen lokal speichern
- Dunkles und helles Design
- Fertiges Video im Browser ansehen und herunterladen

Den aktuellen Entwicklungsstand findest du in `ROADMAP.md`.

## Voraussetzungen

Python-Pakete werden aktuell nicht benötigt. Die Datei `requirements.txt` ist deshalb bewusst leer kommentiert.

Benötigt wird:

- `python3`
- `ffmpeg`
- `ffprobe`

Ubuntu/Debian:

```bash
sudo apt install ffmpeg
```

## Starten

```bash
cd "/media/linus/TOSHIBA MQ4/videocutterai"
bash start.sh
```

Danach öffnet sich die App unter:

```text
http://127.0.0.1:7865
```

Falls sich kein Browser automatisch öffnet:

```bash
python3 app.py --no-browser
```

Version anzeigen:

```bash
python3 app.py --version
```

Tests ausführen:

```bash
python3 -B -m unittest discover -s tests -p 'test_*.py'
```

## Projektstruktur

```text
videocutterai/
├── app.py
├── routes.py
├── renderer.py
├── upload.py
├── utils.py
├── config.py
├── settings.py
├── logging_setup.py
├── static/
├── templates/
├── output/
├── requirements.txt
├── .gitignore
├── LICENSE
├── CHANGELOG.md
├── ROADMAP.md
└── README.md
```

## Einstellungen

Die App speichert Benutzereinstellungen unter:

```text
~/.config/VideoCutterAI/settings.json
```

Aktuell enthalten sind Design, Sprache, Standardformat, Standardauflösung, Standard-FPS, Standardspeicherort und optionaler FFmpeg-Pfad.

## Unterstützte Bildformate

`.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`

## Ausgabeformate

`MP4`, `WebM`, `MKV`, `MOV`
