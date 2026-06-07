from dotenv import load_dotenv
import os

load_dotenv()

gtfs_path = os.getenv("GTFS")
gtfs_rt_path = os.getenv("GTFS-RT")
api_key = os.getenv("API_KEY")
export_dir = os.getenv("EXPORT_DIR")

HEADERS = {"Authorization": f"Bearer {api_key}"} if api_key else {}