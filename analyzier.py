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
    static_metrics = static_df.groupby(["trip_id", "route_id"]).agg(
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

    # 1. Trip cancellation, status 3 == cancelled or no realtime data despite scheduled data
    df_final["fahrtausfall"] = (df_final["trip_status"] == "3") | (~df_final["RT_vorhanden"] & df_final["static_vkm"].notna())
    # 2. Additional trip, status 1 == added or realtime data without scheduled data
    df_final["zusatzfahrt"] = (df_final["trip_status"] == "1") | (df_final["static_vkm"].isna() & df_final["RT_vorhanden"])
    # 3. deviatons in minutes
    df_final.loc[~df_final["fahrtausfall"], "abweichungen_minuten"] = df_final["delay_seconds"] / 60
    # 4. actual scheduled minutes (realtime)
    df_final["ist_fahrplanminuten"] = df_final["soll_fahrplanminuten"] + df_final["abweichungen_minuten"]
    df_final.loc[df_final["fahrtausfall"], "ist_fahrplanminuten"] = 0
    # 5. vehicle-kilometers
    df_final["static_vkm"] = df_final["static_vkm"].fillna(0)
    ## if trip is cancelled, realtime-km should be 0, else like planned
    df_final["ist_vkm"] = df_final.apply(lambda row: 0 if row["fahrtausfall"] else row["static_vkm"], axis=1)
    # 6. passenger-kilometers (-occupancy rate * vehicle-kilometers)
    df_final["soll_pkm"] = df_final["static_vkm"] * capacity_utilization_rate
    df_final["ist_pkm"] = df_final["ist_vkm"] * capacity_utilization_rate

    export_columns = [
        'trip_id', 'route_id', 'RT_vorhanden', 'fahrtausfall', 'zusatzfahrt', 
        'soll_fahrplanminuten', 'ist_fahrplanminuten', 'abweichungen_minuten', 
        'static_vkm', 'ist_vkm', 'soll_pkm', 'ist_pkm'
    ]
    df_export = df_final[export_columns].round(2)
    export_path = f"{export_dir}_monitoring_kpis_{yesterday.strftime('%Y-%m-%d')}.csv"
    
    df_export.to_csv(export_path, index=False, sep=";")
    print(f"KPI-Daten wurden nach {export_path} erfolgreich exportiert.")