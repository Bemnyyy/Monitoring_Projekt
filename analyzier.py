import pandas as pd
import partridge as ptg
from datetime import datetime, timedelta
from config import export_dir, gtfs_path

def load_static_data(target_date):
    # Loading static GTFS Data for BoDo
    print(f"Lade Soll-Daten aus {gtfs_path} für {target_date}...")
    service_ids = ptg.read_service_ids_by_date(gtfs_path)[target_date]
    view = {"trips.txt": {"service_id": service_ids}}
    return ptg.load_feed(gtfs_path, view)

def process_daily_data(rt_data_list):
    # Processes Static and realtime data together and exports them
    yesterday = datetime.now().date() - timedelta(days=1)
    feed = load_static_data(yesterday)
    static_df = pd.merge(feed.stop_times, feed.trips, on="trip_id")

    static_metrics = static_df.groupby("trip_id").agg(
        start_time=("departure_time", "min"),
        end_time=("arrival_time", "max"),
        static_vkm=("shape_dist_traveled", "max")
    ).reset_index()
    static_metrics["soll_dauer_min"] = (static_metrics["end_time"] - static_metrics["start_time"]) / 60

    if not rt_data_list:
        print("ACHTUNG: Keine Echtzeitdaten vorhanden. Exportiere nur Soll-Daten.")
        df_rt = pd.DataFrame(columns=["trip_id", "delay_seconds", "trip_status"])
    else:
        df_rt = pd.DataFrame(rt_data_list)
        """
        ===== DEBUG TEST START =====
        print(f"DEBUG: Typ der übergebenen Daten: {type(rt_data_list)}")
        if not rt_data_list or not isinstance(rt_data_list, list):
            print("ACHTUNG: Keine Echtzeitdaten vorhanden. Es wird eine leere Platzhalter-Tabelle erstellt!")
            df_rt = pd.DataFrame(columns=["trip_id", "delay_seconds", "trip_status"])
        else:
            df_rt = pd.DataFrame(rt_data_list)
        ===== DEBUG TEST ENDE =====
        """
        df_rt = df_rt.drop_duplicates(subset=["trip_id"], keep="last")

    df_final = pd.merge(static_metrics, df_rt, on="trip_id", how="left")

    export_path = f"{export_dir}monitoring_matched_{yesterday.strftime('%Y-%m-%d')}.csv"
    df_final.to_csv(export_path, index=False, sep=";")
    print(f"Die Daten wurden erfolgreich nach {export_path} exportiert")