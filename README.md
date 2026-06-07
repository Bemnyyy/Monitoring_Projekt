# **ÖPNV Monitoring-System (bodo-Verbund)**

*Dieses Python-basierte Backend-System dient dem automatisierten Monitoring und der Qualitätsanalyse von ÖPNV-Verkehrsleistungen im Bodensee-Oberschwaben Verkehrsverbund (bodo)*
*Es führt einen täglichen Soll-Ist-Vergleich durch, indem es statische Fahrplandaten (GTFS) mit dynamischen Echtzeitdaten (GTFS-RT) vergleicht.*

## **Funktionen:**
- Echtzeit-Scraping: Minütliche Abfrage des GTFS-Realtime-Feeds und persistente Zwischenspeicherung in einer lokalen SQLite-Datenbank
- Soll-Ist-Matching: Automatische Zusammenführung jeden Morgen um 03:00 Uhr für den vergangenen Betriebstag
- Verkehrsplanerische KPIs:
    - Erkennung von Fahrtausfällen und Zustzfahrten
    - Berechnung von Soll- und Ist-Fahrplanminuten sowie fahrtgenauen Verspätungen/Verfrühungen
    - Automatische metrische Umrechnung der Routendistanz von Metern in Kilometern zur                 Ermittlung der Fahrzeugkilometer (VKM)
    - Berechnung der Personenkilometer (PKM) auf Basis eines konfigierbaren Auslastungsfaktors
- Detaillierte Berichterstattung: Zweigleisiger CSV-Export sowohl auf aggregierter Fahrten-Ebene als auch auf feiner Haltestellen-Ebene (inkl. Erkennung ausgelassener Halte)

## **Installation & Inbetriebnahme**
1. Abhängigkeiten installieren
   `pip install -r requirements.txt`
2. Umgebgungsvariablen einrichten:
   Erstelle eine `.env`-Datei im Hauptverzeichnis mit folgenden Pfaden:
   *GTFS* = "Pfad zu den GTFS-Daten"
   *GTFS-RT* = "Link zu den zugehörigen GTFS-RT Daten"
   *API_KEY* = "API Key für Realtime Abfragen" (falls benötigt, kann auch weggelassen werden)
   *EXPORT_DIR* = Pfad zum Speichern der exportierten CSV-Dateien
3. System starten
   `python main.py`
