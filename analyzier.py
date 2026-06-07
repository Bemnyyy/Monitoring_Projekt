import pandas as pd
import partridge as ptg
from datetime import datetime, timedelta
from config import export_dir, gtfs_path

capacity_utilization_rate = 0.20 #20% average load factor for PKM-calculation

def load_static_data(target_date):
    # Loading static GTFS Data for BoDo
    print(f"Lade Soll-Daten aus {gtfs_path} für {target_date}...")
    service_ids = list(ptg.read_service_ids_by_date(gtfs_path).values())[0]
    view = {"trips.txt": {"service_id": service_ids}}
    return ptg.load_feed(gtfs_path, view)

def process_daily_data(rt_data_list):
    # Processes Static and realtime data together and exports them
    yesterday = datetime.now().date() - timedelta(days=1)
    feed = load_static_data(yesterday)
    static_df = pd.merge(feed.stop_times, feed.trips, on="trip_id")

    static_metrics = static_df.groupby("trip_id").agg(
        static_start=("departure_time", "min"),
        static_end=("arrival_time", "max"),
        static_vkm=("shape_dist_traveled", "max")
    ).reset_index()
    static_metrics["soll_fahrplanminuten"] = (static_metrics["static_end"] - static_metrics["static_start"]) / 60

    if not rt_data_list:
        df_rt = pd.DataFrame(columns=["trip_id", "delay_seconds", "trip_status", "RT_vorhanden"])
    else:
        df_rt = pd.DataFrame(rt_data_list)
        df_rt = df_rt.sort_values("timestamp").drop_duplicates(subset=["trip_id"], keep="last")
        df_rt["RT_vorhanden"] = True

    df_final = pd.merge(static_metrics, df_rt, on="trip_id", how="outer")
    df_final["RT_vorhanden"] = df_final["RT_vorhanden"].fillna(False)
    df_final["fahrtausfall"] = (df_final["trip_status"] == "3") | (~df_final["RT_vorhanden"] & df_final["static_vkm"].notna())