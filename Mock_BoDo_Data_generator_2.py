import os
import sqlite3
import random
import pandas as pd
import partridge as ptg
from datetime import datetime
from config import gtfs_path

GTFS_STATIC_PATH =  gtfs_path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "bodo_rt_data.db")

def create_mock_live_data():
    print("Analysiere statisches GTFS für Mock-Daten-Generierung...")
    
    service_ids_dict = ptg.read_service_ids_by_date(GTFS_STATIC_PATH)
    if not service_ids_dict:
        print("Fehler: Keine Fahrpläne für das heutige Datum in der GTFS gefunden!")
        return
        
    service_ids = list(service_ids_dict.values())[0]
    view = {'trips.txt': {'service_id': service_ids}}
    feed = ptg.load_feed(GTFS_STATIC_PATH, view)
    trips_df = feed.trips.head(20) # Wir nehmen 20 echte Fahrten für den Test
    stop_times_df = feed.stop_times
    updates_to_insert = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"Generiere künstliche Live-Updates für {len(trips_df)} echte bodo-Fahrten...")
    
    for _, trip in trips_df.iterrows():
        trip_id = trip['trip_id']
        stops = stop_times_df[stop_times_df['trip_id'] == trip_id]
        
        scenario = random.random()
        if scenario < 0.20:
            for _, stop in stops.iterrows():
                updates_to_insert.append((timestamp, trip_id, "3", stop['stop_id'], "1", 0))
        else:
            random_delay = random.randint(-60, 300) 
            for _, stop in stops.iterrows():
                updates_to_insert.append((timestamp, trip_id, "0", stop['stop_id'], "0", random_delay))

    print(f"Verbinde mit Datenbank unter: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rt_updates (
            timestamp TEXT,
            trip_id TEXT,
            trip_status TEXT,
            stop_id TEXT,
            stop_status TEXT,
            delay_seconds INTEGER
        )
    ''')
    conn.commit()
    cursor.execute("DELETE FROM rt_updates")
    cursor.executemany('''
        INSERT INTO rt_updates 
        (timestamp, trip_id, trip_status, stop_id, stop_status, delay_seconds)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', updates_to_insert)
    conn.commit()
    conn.close()
    print(f"Erfolgreich {len(updates_to_insert)} bodo-Mock-Daten in der DB gespeichert!")

if __name__ == "__main__":
    create_mock_live_data()