# Kassensturz verwenden

Englische Version: [HOW_TO_USE.md](HOW_TO_USE.md)

Diese Anleitung ist für Personen gedacht, die Kassensturz während einer
Veranstaltung oder im laufenden Barbetrieb benutzen. Sie erklärt die Bedienung
der App: was eingetragen wird, wo man nachschaut und was die einzelnen Aktionen
bedeuten.

## Grundidee

Kassensturz unterscheidet zwei Arten von Kassenvorgängen:

- Kassensturz / Zählung: Was liegt gerade tatsächlich in einer Kasse?
- Kassenbewegung: Geld wird von einem Konto in ein anderes Konto bewegt.

Eine Zählung setzt den Bestand eines Kontos. Eine Bewegung verändert zwei
Bestände: sie zieht Geld vom Quellkonto ab und addiert es zum Zielkonto.

Beispiel:

```text
Zählung:   Bar Cash Box = 200,00 EUR
Bewegung:  Bar Cash Box -> Runner Float = 50,00 EUR

Ergebnis:  Bar Cash Box = 150,00 EUR
           Runner Float = 50,00 EUR
```

## Wichtige Bereiche

Kassensturz hat vier Bereiche für den Alltag:

- Kassensturz-Seite: gezähltes Bargeld für ein Konto eintragen.
- Kassenbewegung-Seite: Bargeldbewegungen zwischen Konten eintragen.
- Bestände-Seite: prüfen, wie viel Geld aktuell in welchem Konto sein sollte.
- Admin-Seite: Exporte neu erstellen, synchronisieren, Status prüfen und
  Backups wiederherstellen.

## Konten

Die App startet mit festen Konten:

- Bar Cash Box
- Entrance Cash Box
- Runner Float
- Supplier / Drinks Purchase
- Cash Handout
- Bank

Die Konten beschreiben, wo sich das Bargeld befindet oder warum es den normalen
Kassenbestand verlässt.

Verwende Cash-Box-Konten für physische Verkaufskassen. Verwende `Runner Float`
für Wechselgeld oder Vorschüsse, die vorübergehend an eine laufende Person
gegeben werden. Verwende Lieferanten-, Auszahlungs- oder Bankkonten, wenn Geld
die Hauptkassen für einen bestimmten Zweck verlässt.

## Kassensturz eintragen

Trage einen Kassensturz ein, wenn jemand das Bargeld in einem Konto physisch
gezählt hat.

Typische Momente:

- Beginn einer Veranstaltung
- Ende einer Veranstaltung
- Schichtwechsel
- Zwischenkontrolle während des Betriebs
- Korrektur nach Prüfung des echten Bargelds

Schritte:

1. Öffne die Kassensturz-Seite.
2. Wähle das Konto aus.
3. Trage ein, wer gezählt hat.
4. Wähle die Art der Zählung.
5. Trage Veranstaltung, Schicht oder Kontext ein.
6. Trage entweder den Gesamtbetrag oder die Stückelung ein.
7. Speichere die Zählung.

Zählarten:

- `opening`: Anfangsbestand.
- `closing`: Endbestand.
- `spot_check`: Zwischenkontrolle.
- `reconciliation`: Korrektur oder Abgleich.

Nach dem Speichern wird der Bestand des ausgewählten Kontos auf den gezählten
Betrag gesetzt.

## Kassenbewegung eintragen

Trage eine Kassenbewegung ein, wenn Bargeld physisch bewegt wird.

Beispiele:

- Bar Cash Box -> Runner Float
- Entrance Cash Box -> Bank
- Runner Float -> Supplier / Drinks Purchase
- Bar Cash Box -> Cash Handout

Schritte:

1. Öffne die Kassenbewegung-Seite.
2. Wähle das Quellkonto.
3. Wähle das Zielkonto.
4. Trage den Betrag ein.
5. Trage Veranstaltung, Schicht oder Kontext ein.
6. Ergänze Person, Referenz oder Notiz, falls hilfreich.
7. Speichere die Bewegung.

Das Quellkonto sinkt um den Betrag der Bewegung. Das Zielkonto steigt um den
Betrag der Bewegung.

Mindestens eine Seite muss ausgewählt sein. Wähle nur ein Zielkonto, wenn Geld
neu in das erfasste System kommt. Wähle nur ein Quellkonto, wenn Geld das
erfasste System verlässt.

## Runner-Float-Regel

Es gibt eine Sonderregel:

Wenn Geld von `Runner Float` zu `Supplier / Drinks Purchase` bewegt wird, gibt
die App den verbleibenden Runner-Float-Bestand automatisch zurück an
`Bar Cash Box`.

So bleibt der Runner Float nach einem Lieferanteneinkauf nicht versehentlich
offen.

## Kontext verwenden

Der Kontext ist meistens Veranstaltung, Schicht oder Tag.

Gute Beispiele:

- Friday Bar
- Main Hall Saturday
- Sommerfest 2026
- Schicht 2

Verwende denselben Kontext für zusammengehörige Zählungen und Bewegungen. So
bleibt der Verlauf später leichter nachvollziehbar.

## Bestände prüfen

Öffne die Bestände-Seite, um diese Frage zu beantworten:

```text
Wie viel Bargeld sollte gerade in jedem Konto sein?
```

Nutze diese Seite während des Betriebs, um den erwarteten Bestand mit dem
physischen Bargeld zu vergleichen.

Wenn ein Bestand falsch aussieht:

1. Prüfe die letzte Zählung für das betroffene Konto.
2. Prüfe die letzten Bewegungen in dieses Konto oder aus diesem Konto.
3. Wenn das physische Bargeld korrekt ist und die App angepasst werden soll,
   trage eine `reconciliation`-Zählung ein.

## Admin-Seite

Die Admin-Seite ist für Wartung und Wiederherstellung.

Sie zeigt:

- App-Version
- Datenbankschema-Version
- Anzahl der Konten, Kontexte, Bewegungen und Zählungen
- Sync-Status
- Produktions-Bootstrap-Status
- verfügbare Backups

Admin-Aktionen:

- Exporte neu erstellen: Excel- und Text-Export aus der lokalen Datenbank neu
  erzeugen.
- Jetzt synchronisieren: Exporte neu erstellen und den Sync-Ablauf starten.
- Backup wiederherstellen: die aktuelle Datenbank durch ein früheres Backup
  ersetzen.

Das Wiederherstellen eines Backups überschreibt die aktuelle lokale Datenbank.
Nutze diese Aktion nur, wenn das ausgewählte Backup wirklich der Zustand ist,
zu dem du zurückkehren möchtest.

## Exporte

Kassensturz erzeugt zwei Exportdateien:

- Excel-Arbeitsmappe
- Textzusammenfassung

Die Datenbank ist die Quelle der Wahrheit. Die Exportdateien werden aus der
Datenbank erzeugt. Wenn sie fehlen oder veraltet sind, können sie auf der
Admin-Seite neu erstellt werden.

## Sync

Wenn Sync eingerichtet ist, kann Kassensturz Daten über die entfernte
Arbeitsmappe austauschen.

Vereinfacht macht Sync Folgendes:

1. Lokales Backup speichern.
2. Lokale Exporte neu erstellen.
3. Prüfen, ob eine entfernte Arbeitsmappe vorhanden ist.
4. Entfernte Zeilen importieren.
5. Zeilen hinzufügen, die lokal noch nicht vorhanden sind.
6. Zusammengeführten Export neu erstellen.
7. Neue Exportdateien hochladen.

Sync-Importe sind append-only. Wenn dieselben entfernten Zeilen erneut
synchronisiert werden, sollen keine Duplikate entstehen.

## Produktions-Bootstrap

Wenn die App in Produktion mit leerer Datenbank startet, kann sie vorhandene
entfernte Kassendaten importieren, bevor neue Einträge angelegt werden.

Das ist für den ersten Produktionsstart gedacht, wenn alte Kassensturz-Daten
bereits entfernt vorhanden sind.

Die Admin-Seite zeigt, ob Bootstrap:

- inaktiv ist
- bereit ist
- blockiert ist
- übersprungen wurde
- importiert wurde

## Backups

Kassensturz erstellt lokale Datenbank-Backups vor Sync- und Exportarbeiten.

So stellst du ein Backup wieder her:

1. Öffne die Admin-Seite.
2. Wähle ein Backup aus der Liste.
3. Bestätige die Wiederherstellung.
4. Prüfe danach Bestände und letzte Einträge.

Nach einer Wiederherstellung werden die Exporte aus der wiederhergestellten
Datenbank neu erstellt.

## Tagesablauf bei einer Veranstaltung

Ein einfacher Ablauf:

1. Anfangsbestände für aktive Kassen eintragen.
2. Jede relevante Bargeldbewegung während der Veranstaltung eintragen.
3. Während des Betriebs die Bestände-Seite prüfen.
4. Am Ende Schlusszählungen eintragen.
5. Bei Bedarf über die Admin-Seite synchronisieren.
6. Backup und Exporte für Wiederherstellung oder Prüfung aufbewahren.

## Fehlerbehebung

Wenn ein Bestand falsch aussieht:

- letzte Zählung des betroffenen Kontos prüfen
- letzte Bewegungen für dieses Konto prüfen
- eine `reconciliation`-Zählung eintragen, wenn das physische Bargeld die neue
  Wahrheit sein soll

Wenn eine Bewegung falsch eingetragen wurde:

- eine korrigierende Bewegung in Gegenrichtung eintragen
- eine Notiz zur Korrektur ergänzen

Wenn Sync nicht funktioniert hat:

- Admin-Seite öffnen
- Sync-Status prüfen
- Sync bei Bedarf erneut starten
- technische Betreuung bitten, die Remote-Einstellungen zu prüfen, falls es
  wiederholt fehlschlägt

Wenn versehentlich ein Backup wiederhergestellt wurde:

- ein neueres Backup wiederherstellen, falls vorhanden
- Bestände prüfen, bevor neue Einträge gemacht werden

Für technische Einrichtung und Deployment siehe
[configuration.md](configuration.md).
