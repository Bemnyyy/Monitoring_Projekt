import os
import sqlite3
import requests
from datetime import datetime
from google.transit import gtfs_realtime_pb2
from config import gtfs_rt_path, HEADERS  # Achte darauf, wie deine Variablen in der config.py heißen!

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "bodo_rt_data.db")

def init_db():
    """Erstellt die Tabelle, falls sie noch nicht existiert."""
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
    conn.close()

init_db()

def fetch_gtfs_rt():
    try:
        response = requests.get(gtfs_rt_path, headers=HEADERS)
        response.raise_for_status()
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        updates_to_insert = []
        
        for entity in feed.entity:
            if entity.HasField('trip_update'):
                trip = entity.trip_update.trip
                trip_status = str(trip.schedule_relationship)
                for stop_update in entity.trip_update.stop_time_update:
                    stop_status = str(stop_update.schedule_relationship)
                    delay = 0
                    if stop_update.HasField('departure'):
                        delay = stop_update.departure.delay
                    elif stop_update.HasField('arrival'):
                        delay = stop_update.arrival.delay
                    updates_to_insert.append((
                        timestamp, trip.trip_id, trip_status, stop_update.stop_id, stop_status, delay
                    ))
        if updates_to_insert:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.executemany('''
                INSERT INTO rt_updates 
                (timestamp, trip_id, trip_status, stop_id, stop_status, delay_seconds)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', updates_to_insert)
            conn.commit()
            conn.close()
            
        print(f"[{timestamp}] {len(updates_to_insert)} Halte-Updates in DB gespeichert.")
    except Exception as e:
        print(f"Fehler beim RT-Abruf: {e}")

def get_and_clear_daily_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rt_updates")
    columns = [col[0] for col in cursor.description]
    data = [dict(zip(columns, row)) for row in cursor.fetchall()]
    cursor.execute("DELETE FROM rt_updates")
    conn.commit()
    conn.close()
    
    return data