import time
import schedule
from realtime_scraper import fetch_gtfs_rt, get_and_clear_daily_data
from analyzier import process_daily_data

def nightly_job():
    # Works on the previous day, runs at night
    print("Starte nächtliche Datenverarbeitung...")
    rt_data = get_and_clear_daily_data()
    process_daily_data(rt_data)

schedule.every(1).minutes.do(fetch_gtfs_rt)
schedule.every().day.at("03:00").do(nightly_job)

if __name__ == "__main__":
    print("--- ÖPNV Monitoring System gestartet ---")

    # MANUELLER TESTLAUF 
    # ===========================================
    fetch_gtfs_rt()
    nightly_job()
    print("Manueller Testlauf abgeschlossen.")
    # ===========================================
    print("Gehe in regulären Zeitplan über...")
    print("Warte auf geplante Ausführung... (Strg + C zum Beenden)")

    while True:
        schedule.run_pending()
        time.sleep(1)