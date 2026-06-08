import pandas as pd
import partridge as ptg
from datetime import datetime, timedelta
from config import export_dir, gtfs_path

capacity_utilization_rate = 0.20 # 20% average load factor for PKM
umrechnungsfaktor_km = 1000      # the gtfs data is using meter, so we divide by 1000 to get kilometers

def load_static_data(target_date):
    # Loading static GTFS Data for BoDo
    print(f"Lade Soll-Daten aus {gtfs_path} für {target_date}...")
    service_ids = list(ptg.read_service_ids_by_date(gtfs_path).values())[0]
    view = {"trips.txt": {"service_id": service_ids}}
    return ptg.load_feed(gtfs_path, view)

def process_daily_data(rt_data_list):
    yesterday = datetime.now().date() - timedelta(days=1)
    feed = load_static_data(yesterday)
    #merge basic static data
    static_df = pd.merge(feed.stop_times, feed.trips, on="trip_id")

    # adding stop names to the feed
    if hasattr(feed, "stops") and not feed.stops.empty:
        static_df = pd.merge(static_df, feed.stops[["stop_id", "stop_name"]], on="stop_id", how="left")
    else:
        static_df["stop_name"] = "Unbekannter Name"

    if "shape_dist_traveled" in static_df.columns:
        static_df["shape_dist_traveled"] = static_df["shape_dist_traveled"] / umrechnungsfaktor_km

    # preparing realtime data
    if not rt_data_list:
        df_rt = pd.DataFrame(columns=["timestamp", "trip_id", "delay_seconds", "trip_status", "stop_id", "stop_status", "RT_vorhanden"])
    else:
        df_rt = pd.DataFrame(rt_data_list)
        df_rt["RT_vorhanden"] = True
    print("Berechne Fahrten-Level KPIs...")
    # overview trips
    static_metrics = static_df.groupby(["trip_id", "route_id"]).agg(
        static_start=("departure_time", "min"),
        static_end=("arrival_time", "max"),
        static_vkm=("shape_dist_traveled", "max")
    ).reset_index()
    
    static_metrics["soll_fahrplanminuten"] = (static_metrics["static_end"] - static_metrics["static_start"]) / 60

    if hasattr(feed, "routes") and not feed.routes.empty:
        routes_df = feed.routes[["route_id", "route_short_name", "route_long_name", "route_type"]]
        static_metrics = pd.merge(static_metrics, routes_df, on="route_id", how="left")

    # keeping only the last trip update
    if not df_rt.empty:
        df_rt_trips = df_rt.sort_values("timestamp").drop_duplicates(subset=["trip_id"], keep="last")
    else:
        df_rt_trips = df_rt

    df_fahrten = pd.merge(static_metrics, df_rt_trips, on="trip_id", how="outer")
    df_fahrten["RT_vorhanden"] = df_fahrten["RT_vorhanden"].fillna(False)
    df_fahrten["fahrtausfall"] = (df_fahrten["trip_status"] == "3") | (~df_fahrten["RT_vorhanden"] & df_fahrten["static_vkm"].notna())
    df_fahrten["zusatzfahrt"] = (df_fahrten["trip_status"] == "1") | (df_fahrten["static_vkm"].isna() & df_fahrten["RT_vorhanden"])
    df_fahrten.loc[df_fahrten["delay_seconds"] > 86400, "delay_seconds"] = 0
    df_fahrten.loc[df_fahrten["delay_seconds"] <-86400, "delay_seconds"] = 0
    df_fahrten.loc[~df_fahrten["fahrtausfall"], "abweichungen_minuten"] = df_fahrten["delay_seconds"] / 60
    df_fahrten["ist_fahrplanminuten"] = df_fahrten["soll_fahrplanminuten"] + df_fahrten["abweichungen_minuten"]
    df_fahrten.loc[df_fahrten["fahrtausfall"], "ist_fahrplanminuten"] = 0
    df_fahrten["static_vkm"] = df_fahrten["static_vkm"].fillna(0)
    df_fahrten["ist_vkm"] = df_fahrten.apply(lambda row: 0 if row["fahrtausfall"] else row["static_vkm"], axis=1)
    df_fahrten["soll_pkm"] = df_fahrten["static_vkm"] * capacity_utilization_rate
    df_fahrten["ist_pkm"] = df_fahrten["ist_vkm"] * capacity_utilization_rate

    export_cols_fahrten = [
        'trip_id', 'route_id', 'route_short_name', 'route_long_name', 'route_type', 'RT_vorhanden', 'fahrtausfall', 'zusatzfahrt', 
        'soll_fahrplanminuten', 'ist_fahrplanminuten', 'abweichungen_minuten', 
        'static_vkm', 'ist_vkm', 'soll_pkm', 'ist_pkm'
    ]
    path_fahrten = f"{export_dir}Monitoring_fahrten_{yesterday.strftime('%Y-%m-%d')}.csv"
    df_fahrten[export_cols_fahrten].round(2).to_csv(path_fahrten, index=False, sep=";", decimal=",")



    print("Berechne Haltestellen-Level KPIs...")
    # code for getting the csv for the stops
    static_stops = static_df[['trip_id', 'route_id', 'stop_id', 'stop_name', 'stop_sequence', 'departure_time']].copy()

    # keeping the last updated trip for every stop
    if not df_rt.empty:
        df_rt_stops = df_rt.sort_values("timestamp").drop_duplicates(subset=["trip_id", "stop_id"], keep="last")
    else:
        df_rt_stops = df_rt

    df_halte = pd.merge(static_stops, df_rt_stops, on=["trip_id", "stop_id"], how="outer")
    df_halte["RT_vorhanden"] = df_halte["RT_vorhanden"].fillna(False)

    # 1. Stop missed, trip cancelled or stop explicity marked as status "1" == "skipped" or showing no realtime-data despite being scheduled
    df_halte["haltausfall"] = (df_halte["trip_status"] == "3") | (df_halte["stop_status"] == "1") | (~df_halte["RT_vorhanden"] & df_halte["stop_sequence"].notna())
    # 2. Additional Stop; the stop does not have a static stop sequence but appear in the realtime-data
    df_halte["zusatzhalt"] = df_halte["stop_sequence"].isna() & df_halte["RT_vorhanden"]
    # 3. delay per stop
    df_halte.loc[df_halte["delay_seconds"] > 86400, "delay_seconds"] = 0
    df_halte.loc[df_halte["delay_seconds"] < -86400, "delay_seconds"] = 0
    df_halte["verspaetung_minuten"] = df_halte["delay_seconds"] / 60
    # clean up columns
    export_cols_halte = [
        'trip_id', 'route_id', 'stop_id', 'stop_name', 'stop_sequence', 'RT_vorhanden', 
        'haltausfall', 'zusatzhalt', 'verspaetung_minuten'
    ]
    # Ensuring that all columns for the export are present (to prevent a crash in the event of a complete absence of realtime-data)
    for col in export_cols_halte:
        if col not in df_halte.columns:
            df_halte[col] = None
    path_halte = f"{export_dir}Monitoring_halte_{yesterday.strftime('%Y-%m-%d')}.csv"
    # sort by route and stop_sequence
    df_halte = df_halte.sort_values(by=['route_id', 'trip_id', 'stop_sequence'])
    df_halte[export_cols_halte].round(2).to_csv(path_halte, index=False, sep=";", decimal=",")

    print(f"===== EXPORT ABGESCHLOSSEN =====")
    print(f"1. Fahrten-Level exportiert nach: {path_fahrten}")
    print(f"2. Halte-Level exportiert nach:   {path_halte}")