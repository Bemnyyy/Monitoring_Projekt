import time
import schedule
from realtime_scraper import fetch_gtfs_rt, get_and_clear_daily_data
from analyzer import process_daily_data

def nightly_job():
    # Works on the previous day, runs at night
    print("\n=== START: DATENVERARBEITUNG & EXPORT ===")
    rt_data = get_and_clear_daily_data()
    process_daily_data(rt_data)
    print("\n=== ENDE: DATENVERARBEITUNG & EXPORT ===\n")

# scheduling-setup for a real live run
schedule.every(1).minutes.do(fetch_gtfs_rt)
schedule.every().day.at("03:00").do(nightly_job)

if __name__ == "__main__":
    print("--- ÖPNV Monitoring System gestartet ---")
    
    print("1. Daten-Abruf wird ausgeführt...")
    # loading given realtime data from .pb file to DB-table
    fetch_gtfs_rt()
    
    print("2. Starte Analyse...")
    # clearing DB-table, working on static-realtime-comparisson and building csv
    nightly_job()

    print("=== Initialer Durchlauf komplett! CSV-Dateien sind fertig. ===")
    print("\nGehe in regulären Zeitplan über...")
    print("Warte auf geplante Ausführung... (Strg + C zum Beenden)")

    #endless loop for server-operation
    while True:
        schedule.run_pending()
        time.sleep(1)