from dotenv import load_dotenv
import os

load_dotenv()

GTFS_PATH = os.getenv("GTFS")
GTFS_RT_PATH = os.getenv("GTFS-RT")
API_KEY = os.getenv("API_KEY")
EXPORT_DIR = os.getenv("EXPORT_DIR")

HEADERS = {"Authorization": f"Bearer {API_KEY}"} if API_KEY else {}

capacity_utilization_rate = 0.20 # 20% average load factor for PKM
conversion_factor_km = 1000 # the gtfs data is using meter, so we divide by 1000 to get kilometers