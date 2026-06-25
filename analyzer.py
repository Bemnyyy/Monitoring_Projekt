import pandas as pd
import partridge as ptg
from datetime import datetime, timedelta
from config import EXPORT_DIR, GTFS_PATH, capacity_utilization_rate, conversion_factor_km

### this is the analyzing part of the code; all calculations and necessary exports are performed here. 
### if problems occur during export or calculation, this code should be checked.

def load_static_data(target_date):
    # Loading static GTFS data from the path specified in the dotenv-file.
    print(f"Lade Soll-Daten aus {GTFS_PATH} für {target_date}...")
    service_ids = list(ptg.read_service_ids_by_date(GTFS_PATH).values())[0] #partridge is used to reliably read the large volume of static data
    view = {"trips.txt": {"service_id": service_ids}}
    return ptg.load_feed(GTFS_PATH, view)

def process_daily_data(rt_data_list):
    ### this function is the core component of all calculations and exports
    ### it first generates dataframes for realtime and static data then processes these fpr calculations and export

    yesterday = datetime.now().date() - timedelta(days=1)
    feed = load_static_data(yesterday) # feed resembles all static data from the day before
    #merge basic static data
    static_df = pd.merge(feed.stop_times, feed.trips, on="trip_id")

    # adding stop names to the feed
    if hasattr(feed, "stops") and not feed.stops.empty:
        static_df = pd.merge(static_df, feed.stops[["stop_id", "stop_name"]], on="stop_id", how="left")
    else:
        static_df["stop_name"] = "Unbekannter Name"

    if "shape_dist_traveled" in static_df.columns:
        static_df["shape_dist_traveled"] = static_df["shape_dist_traveled"] / conversion_factor_km

    # preparing realtime data
    if not rt_data_list:
        df_rt = pd.DataFrame(columns=["timestamp", "trip_id", "delay_seconds", "trip_status", "stop_id", "stop_status", "RT_vorhanden"])
    else:
        df_rt = pd.DataFrame(rt_data_list)
        df_rt["RT_vorhanden"] = True
    
    
    print("Berechne Fahrten-Level KPIs...")
    # overview trips, it prepares a variable for later use
    static_metrics = static_df.groupby(["trip_id", "route_id"]).agg(
        static_start=("departure_time", "min"),
        static_end=("arrival_time", "max"),
        static_vkm=("shape_dist_traveled", "max")
    ).reset_index()

    #Scheduled travel minutes are calculated here by subtracting the static start time from the static end time and dividing it by 60.
    static_metrics["soll_fahrplanminuten"] = (static_metrics["static_end"] - static_metrics["static_start"]) / 60 

    # Adding all information for routes for a better overview in the csv-export.
    # all these columns were added to simplify further processing.
    if hasattr(feed, "routes") and not feed.routes.empty:
        routes_df = feed.routes[["route_id", "route_short_name", "route_long_name", "route_type"]]
        static_metrics = pd.merge(static_metrics, routes_df, on="route_id", how="left")

    # keeping only the last trip update, so that only the most recent trip updates are factored into the calculations
    if not df_rt.empty:
        df_rt_trips = df_rt.sort_values("timestamp").drop_duplicates(subset=["trip_id"], keep="last")
    else:
        df_rt_trips = df_rt


    df_fahrten = pd.merge(static_metrics, df_rt_trips, on="trip_id", how="outer")
    # fills columns with "False" if no real-time data is available for certain trips.
    df_fahrten["RT_vorhanden"] = df_fahrten["RT_vorhanden"].fillna(False)
    # the live-API (or the .pb-file) returns the value 3 for cancelled trips and the value 1 for additional trips; these are therefore taken into account here
    df_fahrten["fahrtausfall"] = (df_fahrten["trip_status"] == "3") | (~df_fahrten["RT_vorhanden"] & df_fahrten["static_vkm"].notna())
    df_fahrten["zusatzfahrt"] = (df_fahrten["trip_status"] == "1") | (df_fahrten["static_vkm"].isna() & df_fahrten["RT_vorhanden"])
    # extreme outliners resulting from calculation errors or transmission errors via the live API or the .pb-file are set to 0, as otherwise the export would yield meaningless figures.
    df_fahrten.loc[df_fahrten["delay_seconds"] > 86400, "delay_seconds"] = 0
    df_fahrten.loc[df_fahrten["delay_seconds"] <-86400, "delay_seconds"] = 0
    df_fahrten.loc[~df_fahrten["fahrtausfall"], "abweichungen_minuten"] = df_fahrten["delay_seconds"] / 60
    # the acutal travel time is calculated here as the scheduled time plus/minus the deviation. In the event of cancellations, this value is set to zero
    df_fahrten["ist_fahrplanminuten"] = df_fahrten["soll_fahrplanminuten"] + df_fahrten["abweichungen_minuten"]
    df_fahrten.loc[df_fahrten["fahrtausfall"], "ist_fahrplanminuten"] = 0
    # calculations of the acutal distance traveled by the vehicle
    df_fahrten["static_vkm"] = df_fahrten["static_vkm"].fillna(0)
    df_fahrten["ist_vkm"] = df_fahrten.apply(lambda row: 0 if row["fahrtausfall"] else row["static_vkm"], axis=1)
    # calculation of the theoretical distance passengers spent inside the vehicle, based on the occupancy rate redefined in config.py
    df_fahrten["soll_pkm"] = df_fahrten["static_vkm"] * capacity_utilization_rate
    df_fahrten["ist_pkm"] = df_fahrten["ist_vkm"] * capacity_utilization_rate

    # clean up columns.
    export_cols_fahrten = [
        'trip_id', 'route_id', 'route_short_name', 'route_long_name', 'route_type', 'RT_vorhanden', 'fahrtausfall', 'zusatzfahrt', 
        'soll_fahrplanminuten', 'ist_fahrplanminuten', 'abweichungen_minuten', 
        'static_vkm', 'ist_vkm', 'soll_pkm', 'ist_pkm'
    ]
    # data is exported here as a CSV with a defined prefix, using semicolons as delimiters and the German decimal seperator (comma).
    path_fahrten = f"{EXPORT_DIR}Monitoring_fahrten_{yesterday.strftime('%Y-%m-%d')}.csv"
    df_fahrten[export_cols_fahrten].round(2).to_csv(path_fahrten, index=False, sep=";", decimal=",", encoding="utf-8-sig")



    print("Berechne Haltestellen-Level KPIs...")
    # code for getting the csv for the stops, it thus checks behaviour at every single stop -to the extent possible- using live data.
    static_stops = static_df[['trip_id', 'route_id', 'stop_id', 'stop_name', 'stop_sequence', 'departure_time']].copy()

    # keeping the last updated trip for every stop, so that only the most recent trip updates are factored into the calculations
    if not df_rt.empty:
        df_rt_stops = df_rt.sort_values("timestamp").drop_duplicates(subset=["trip_id", "stop_id"], keep="last")
    else:
        df_rt_stops = df_rt

    df_halte = pd.merge(static_stops, df_rt_stops, on=["trip_id", "stop_id"], how="outer")
    df_halte["RT_vorhanden"] = df_halte["RT_vorhanden"].fillna(False)

    # stop missed, trip cancelled or stop explicity marked as status "1" == "skipped" or showing no realtime-data despite being scheduled
    df_halte["haltausfall"] = (df_halte["trip_status"] == "3") | (df_halte["stop_status"] == "1") | (~df_halte["RT_vorhanden"] & df_halte["stop_sequence"].notna())
    # additional Stop; the stop does not have a static stop sequence but appear in the realtime-data
    df_halte["zusatzhalt"] = df_halte["stop_sequence"].isna() & df_halte["RT_vorhanden"]
    # delay per stop, same logic as for the "Fahrten KPIs"
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
    path_halte = f"{EXPORT_DIR}Monitoring_halte_{yesterday.strftime('%Y-%m-%d')}.csv"
    # sort by route and stop_sequence, also uses a defined prefix, using semicolons as delimiters and the German decimal seperator (comma).
    df_halte = df_halte.sort_values(by=['route_id', 'trip_id', 'stop_sequence'])
    df_halte[export_cols_halte].round(2).to_csv(path_halte, index=False, sep=";", decimal=",", encoding="utf-8-sig")

    # terminal output for a better overview of where the code is currently executing.
    print(f"===== EXPORT ABGESCHLOSSEN =====")
    print(f"1. Fahrten-Level exportiert nach: {path_fahrten}")
    print(f"2. Halte-Level exportiert nach:   {path_halte}")