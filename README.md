# Schnee-Checker

Der Schnee-Checker ist eine kleine Desktop-Anwendung, mit der man auf einer
interaktiven Landkarte auf einen Blick erkennen kann, wo es besonders hoch
hinausgeht oder wo viel Schnee liegt. Statt trockener Zahlenkolonnen bekommt
man das Ergebnis direkt farbig auf einer echten Karte eingezeichnet – man wählt
ein Gebiet, stellt eine Schwelle ein, und das Programm markiert genau die
Flächen, die darüber liegen.

## Schnellstart

```bash
# 1. Abhängigkeiten installieren
python -m pip install -r requirements.txt
# (Unter Linux zusätzlich das Tk-Paket der Standardbibliothek, z. B.:)
#   sudo apt install python3-tk

# 2. Programm starten
python main.py
```

Getestet mit **Python 3.9+**. Benötigt wird nur **Pillow**; `tkinter` gehört zur
Python-Standardbibliothek (unter manchen Linux-Distributionen muss `python3-tk`
separat nachinstalliert werden). Für den Datenabruf ist eine Internetverbindung
nötig.

## Auch auf dem Handy: Web-Version

Neben der Desktop-App gibt es unter [`web/index.html`](web/index.html) eine
eigenständige Web-Version derselben Idee. Sie läuft in **jedem Browser – auch am
Handy** mit Pinch-Zoom und Wischen.

Funktionen der Web-Version:

- **Farbverlauf statt nur „drüber/drunter":** Flächen werden je nach Höhe bzw.
  Schneehöhe abgestuft eingefärbt, mit passender Farbskala in der Legende.
- **Wert antippen:** Tippt man auf ein Feld, erscheint der genaue Wert.
- **Mein Standort:** Knopf unten rechts springt zur aktuellen GPS-Position.
- **Ortssuche:** Suchfeld für Orte (über Nominatim/OpenStreetMap).
- **Als App installierbar (PWA):** eigenes Icon, „Zum Home-Bildschirm
  hinzufügen", startet wie eine App.
- Einstellungen (Modus, Schwelle, Auflösung) werden gemerkt; wackliges Netz wird
  mit einem Wiederholversuch abgefangen.

**Öffnen auf dem Handy – am einfachsten über GitHub Pages (kostenlos):**

1. Im GitHub-Repository auf **Settings → Pages** gehen.
2. Bei *Build and deployment* → *Source* **„Deploy from a branch"** wählen,
   Branch `main` (oder den gewünschten Branch) und Ordner `/root`, speichern.
3. Nach kurzer Wartezeit zeigt GitHub eine Adresse an, z. B.
   `https://<benutzername>.github.io/Schneechecker2/web/`.
4. Diese Adresse auf dem Handy im Browser öffnen (und bei iPhone/Android bei
   Bedarf „Zum Home-Bildschirm hinzufügen").

> Hinweis: Als Artifact/Chat-Vorschau lässt sich die Karte **nicht** anzeigen –
> jene Sandbox erlaubt keine externen Kartenkacheln und keine API-Zugriffe. Über
> eine normal gehostete Seite (GitHub Pages) funktioniert beides.

## Bedienung

1. Zu der Region navigieren, die einen interessiert – mit gedrückter Maustaste
   verschieben, mit dem Mausrad hinein- und herauszoomen.
2. In der Steuerleiste rechts einen der beiden Modi wählen: **Höhe** oder
   **Schnee**.
3. Die **Schwelle** einstellen (z. B. „ab 1500 Metern" oder „ab 30 Zentimetern
   Schnee"), bei Bedarf **Auflösung** (Feinheit des Rasters) und **Zoom**
   anpassen.
4. Auf **Aktualisieren** (roter Button) klicken. Im Hintergrund werden die
   Daten geladen – die Karte bleibt bedienbar, ein Fortschrittsbalken zeigt den
   Stand an.
5. Das Ergebnis legt sich als halbtransparente Fläche über die Karte:
   **Höhen in warmem Rot, Schnee in kühlem Blau**. Weil die Flächen
   durchscheinend sind, bleiben Straßen, Orte und Gelände darunter erkennbar.

In der Mitte hilft ein feines Fadenkreuz bei der Orientierung, unten links
werden jederzeit Zoomstufe und geografische Koordinaten eingeblendet.

## Was im Hintergrund passiert

Die Werte stammen live aus der frei zugänglichen **Open-Meteo**-Schnittstelle.
Das Programm legt ein Raster über das sichtbare Gebiet, fragt für jeden
Rasterpunkt Höhe bzw. Schneehöhe ab und fasst die Punkte zu farbigen Flächen
zusammen. Damit nicht unnötig viele Anfragen anfallen, werden die Punkte
paketweise abgearbeitet, kurze Pausen eingelegt und bereits abgerufene Werte
zwischengespeichert. Der Abruf läuft in einem separaten Arbeits-Thread, damit
die Oberfläche nicht einfriert.

Datenquellen:

- **Höhe:** `https://api.open-meteo.com/v1/elevation` (Meter über Meer)
- **Schnee:** `https://api.open-meteo.com/v1/forecast` mit `current=snow_depth`
  (von Meter in Zentimeter umgerechnet)
- **Kartenkacheln:** OpenStreetMap (`https://tile.openstreetmap.org`)

## Aufbau des Projekts

```
main.py                     Startpunkt (python main.py)
schnee_checker/
    __init__.py
    geo.py                  Web-Mercator-Projektion (Kartenmathematik)
    data.py                 Rasterung, Open-Meteo-Abruf, Cache
    mapview.py              interaktive Kartenansicht (tkinter + Pillow)
    app.py                  Hauptfenster mit Steuerleiste und Worker
tests/
    test_core.py            Tests für die GUI-freien Kernmodule
```

`geo.py` und `data.py` kommen bewusst ohne tkinter/Pillow aus und lassen sich
daher einzeln testen.

## Tests

```bash
python -m unittest discover -s tests -v
```

Die Tests decken die Kartenmathematik sowie die Rasterung, die Schwellenlogik
und den Cache ab (ohne Netzwerkzugriff, mit einer eingesetzten Test-Abfrage).

## Hinweise

- Die OpenStreetMap-Kacheln werden im temporären Verzeichnis des Systems
  (`schnee_checker_tiles`) zwischengespeichert, um sie nicht doppelt zu laden.
- Bitte die Nutzungsbedingungen der Datenquellen beachten (OpenStreetMap
  Tile-Usage-Policy, Open-Meteo Fair-Use).

## Kontext

Der Schnee-Checker ist im Rahmen eines Informatik-Projekts entstanden und
verbindet mehrere Themen: den Umgang mit einer echten Programmieroberfläche,
das Einbinden externer Datenquellen aus dem Netz und die anschauliche
Darstellung von Geodaten auf einer Karte.
