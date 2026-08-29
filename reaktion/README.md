# Farb-Reaktion

Ein kleines Reaktions-Trainingsspiel nach dem **Stroop-Prinzip**: Farbe, Wort und
Hintergrund passen absichtlich nicht zusammen – du musst schnell das richtige Feld
antippen.

## Starten

Einfach [`index.html`](index.html) im Browser öffnen – funktioniert am Rechner
**und am Handy**, ohne Installation.

## Als App aufs Handy (PWA)

Die App ist – genau wie der Schnee-Checker – eine **PWA**: eigenes Icon, startet
wie eine echte App und läuft auch offline. Am einfachsten über **GitHub Pages**
(kostenlos):

1. Im GitHub-Repository auf **Settings → Pages** gehen.
2. Bei *Build and deployment* → *Source* **„Deploy from a branch"** wählen,
   den gewünschten Branch und Ordner `/root`, speichern.
3. Nach kurzer Wartezeit zeigt GitHub eine Adresse an, z. B.
   `https://<benutzername>.github.io/Schneechecker2/reaktion/`.
4. Diese Adresse auf dem Handy im Browser öffnen und dann:
   - **iPhone (Safari):** Teilen-Symbol → „Zum Home-Bildschirm".
   - **Android (Chrome):** Menü ⋮ → „App installieren" bzw.
     „Zum Startbildschirm hinzufügen".

Danach liegt „Farb-Reaktion" mit eigenem Icon auf dem Handy und startet im
Vollbild – ohne Browser-Leiste.

> Diese App braucht kein Internet und keine externen Dienste – sie läuft nach dem
> ersten Laden komplett offline.

## Spielprinzip

- **Vier Felder** (2×2). Jedes Feld hat eine eigene **Hintergrundfarbe** und zeigt
  ein **Farb-Wort** als Text. Wort, Textfarbe und Hintergrund sind pro Runde
  zufällig und passen bewusst nicht zusammen.
- **Oben steht die Aufgabe.** Es gibt zwei Fälle:
  - **Wort in Weiß/Schwarz** → tippe das Feld, das **diese Farbe hat**
    (der Hintergrund).
  - **Wort in Farbe** → tippe das Feld, auf dem **genau dieses Wort** steht
    (die Buchstaben zählen – in welcher Farbe das Wort geschrieben ist, ist egal).

Jeder Treffer gibt einen Punkt und misst deine Reaktionszeit. Mit steigender
Punktzahl wird das Zeitlimit pro Runde kürzer. Ein Fehlgriff oder abgelaufene Zeit
beendet die Runde.

## Menü & Auswertung

- **Hauptmenü:** Beim Start – „Spielen" oder „Auswertung". Während des Spiels
  kommt man über den Knopf **„Menü"** jederzeit zurück.
- **Auswertung:** dauerhaft gespeicherte Statistik (im Browser, bleibt erhalten):
  Rekord-Punkte, gespielte Spiele, schnellste Reaktion, durchschnittliche
  Reaktion, Treffer gesamt und das letzte Spiel. Mit „Statistik zurücksetzen"
  lässt sich alles wieder auf null stellen.

## Farben

Rot · Gelb · Grün · Blau
