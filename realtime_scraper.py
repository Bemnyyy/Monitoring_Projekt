import requests
from datetime import datetime
from google.transit import gtfs_realtime_pb2
from config import gtfs_rt_path, HEADERS

_daily_rt_data = []

def fetch_gtfs_rt():
    try:
        response = requests.get(gtfs_rt_path, headers=HEADERS)
        response.raise_for_status
        feed = gtfs_realtime_pb2.FeedMessage()
        feed.ParseFromString(response.content)
        timestamp = datetime.now()

        for entity in feed.entity:
            if entity.HasField("trip_update"):
                trip = entity.trip_update.trip
                trip_status = trip.schedule_relationship

                for stop_update in entity.trip_update.stop_time_update:
                    delay = 0
                    if stop_update.HasField("departure"):
                        delay = stop_update.departure.delay
                    elif stop_update.HasField("arrival"):
                        delay = stop_update.arrival.delay
                    
                    _daily_rt_data.append({
                        "timestamp": timestamp,
                        "trip_id": trip.trip_id,
                        "trip_status": trip_status,
                        "stop_id": stop_update.stop_id,
                        "delay_seconds": delay
                    })
        
        print(f"[{timestamp.strftime("%H:%M:%S")}] Echtzeitdaten erfolgreich erfasst.")
    except Exception as e:
        print(f"Fehler beim RT-Abruf: {e}")

def get_and_clear_daily_data():
    global _daily_rt_data
    data_copy = list(_daily_rt_data)
    _daily_rt_data.clear()
    return data_copy