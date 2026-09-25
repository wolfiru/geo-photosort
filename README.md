# Geo-Photosort

Sortiert Fotos und Videos anhand ihrer GPS-Metadaten geografisch in Ordner:

```
GeoSort/
  <Grossraum, z.B. "Deutschland - Bayern">/
    <Bubble, z.B. "Muenchen">/
      IMG_0001.jpg
  Ohne_GPS/
    IMG_9999.jpg
  geosort_report.csv
```

- **Bubble**: geometrisches Clustering (Complete-Linkage) von Orten, die naeher als `bubble_distance_km` (Default 20 km) beieinander liegen – innerhalb einer Bubble liegt kein Punktepaar weiter als der Schwellwert auseinander.
- **Grossraum**: Land + Bundesland/Region der jeweiligen Bubble, ermittelt per Reverse-Geocoding (OpenStreetMap Nominatim) und lokal gecacht. Kein Distanz-Schwellwert noetig, da administrative Grenzen verwendet werden.

## Installation

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Zusaetzlich wird **exiftool** benoetigt (liest GPS-Daten aus Fotos *und* Videos):

```powershell
winget install -e --id OliverBetz.ExifTool
```

Alternativ von https://exiftool.org herunterladen. Wird exiftool nicht automatisch gefunden, fragt Geosort beim Start einmalig nach dem Pfad und merkt sich ihn danach selbststaendig in `geosort_settings.json` (wird automatisch angelegt, keine manuelle Bearbeitung noetig).

## Benutzung

### Grafische Oberflaeche

Doppelklick auf `Geosort_GUI.bat`. Quell-/Zielordner per Dialog waehlen, Optionen einstellen, "Scan (Vorschau)" zeigt das Ergebnis im Log-Fenster, "Jetzt ausfuehren" fragt vor dem eigentlichen Kopieren/Verschieben nochmal nach.

### Interaktiver Assistent (Kommandozeile)

Doppelklick auf `Geosort_starten.bat`, oder ohne Parameter starten:

```powershell
python -m geosort
```

Fragt dann Schritt fuer Schritt Quellordner, Zielordner, kopieren/verschieben, Bubble-Radius, Sprache und Tagging ab, bietet danach automatisch einen Scan (Dry-Run) zur Kontrolle an und fragt erst dann, ob wirklich kopiert/verschoben werden soll.

### Direkt per Kommandozeile (fuer wiederholte/automatisierte Laeufe)

```powershell
python -m geosort --source "D:\Fotos\Urlaub2025" --dry-run
```

Wenn das Ergebnis (siehe `GeoSort/geosort_report.csv`) passt, ohne `--dry-run` erneut ausfuehren.
Mit `--mode move` werden Dateien verschoben statt kopiert (Default: `copy`).

Alle Parameter koennen auch ueber eine YAML-Datei gesetzt werden, siehe `config.example.yaml`:

```powershell
python -m geosort --config config.yaml
```

### Wichtige Parameter

| Parameter | Beschreibung | Default |
|---|---|---|
| `--source` | Quellordner (rekursiv durchsucht) | - |
| `--output` | Zielordner | `<source>/GeoSort` |
| `--bubble-km` | Schwellwert Bubble in km | 20 |
| `--mode` | `copy` oder `move` | `copy` |
| `--dry-run` | nur simulieren, Bericht schreiben | aus |
| `--language` | Sprache der Ortsnamen | `de` |
| `--write-location-tags` | Ort zusaetzlich als IPTC/XMP-Tags (City/State/Country + Keywords) in die Zieldatei schreiben | aus |
| `--tag-existing` | Nur vorhandene GeoSort-Ordner nachtraeglich taggen, ohne neu zu sortieren | aus |

### Ort in der Datei suchbar machen

Mit `--write-location-tags` schreibt Geosort den ermittelten Ort zusaetzlich als IPTC/XMP-Metadaten (City, State, Country, Keywords) in jede Zieldatei. Windows-Explorer, Fotos-Apps und Lightroom koennen danach durchsucht werden. Der Datei-Zeitstempel ("Geaendert am") sowie das EXIF-Aufnahmedatum werden dabei **nicht** veraendert (exiftool-Flag `-P`).

Wurde bereits ohne diese Option sortiert, muss nicht neu kopiert werden: `--tag-existing` liest die Ortsangaben direkt aus den vorhandenen Grossraum-/Bubble-Ordnernamen und taggt die dort liegenden Dateien nachtraeglich:

```powershell
python -m geosort --source "D:\Fotos\Urlaub2025" --tag-existing
```

### Direktlauf ohne Rueckfragen

`sortall.cmd` sortiert einen fest hinterlegten Ordner per Doppelklick in einem Rutsch (kopieren + Orts-Tags), ohne jegliche Rueckfrage. Pfad und Optionen darin nach Bedarf anpassen.

## Bekannte Einschraenkungen

- Dateien ohne GPS-Metadaten landen unsortiert in `Ohne_GPS`.
- Nominatim (OSM) erlaubt max. 1 Anfrage/Sekunde; bei sehr vielen unterschiedlichen Orten kann das etwas dauern (nur pro Cluster, nicht pro Datei).
- Der Mittelpunkt eines Clusters wird als einfacher Durchschnitt von Breiten-/Laengengrad berechnet; nahe den Polen oder am 180.-Meridian kann das ungenau werden (fuer Reisefotos in der Praxis kein Problem).
