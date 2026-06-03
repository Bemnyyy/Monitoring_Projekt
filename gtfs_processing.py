import os
import pandas as pd
import networkx
from dotenv import load_dotenv
from load_dotenv import gtfs_path, gtfs_rt_path

load_dotenv(gtfs_path)
#gtfs_realtime = os.getenv("GTFS-RT")

def load_gtfs_data(gtfs_path):
    print("dotenv-Pfad verbunden")
    gtfs = {}

    try:
        gtfs["calendar_dates"] = pd.read_csv(f"{gtfs_path}/calendar_dates.txt")
        gtfs["routes"] = pd.read_csv(f"{gtfs_path}/routes.txt")
        gtfs["shapes"] = pd.read_csv(f"{gtfs_path}/shapes.txt")
        gtfs["stop_times"] = pd.read_csv(f"{gtfs_path}/stop_times.txt")
        gtfs["stops"] = pd.read_csv(f"{gtfs_path}/trips.txt")
        print("GTFS Daten geladen")

    except FileNotFoundError as e:
        print(f"Fehler beim Laden der GTFS-Daten: {e}")
        gtfs = {}

    return gtfs

print(load_gtfs_data(gtfs_path))