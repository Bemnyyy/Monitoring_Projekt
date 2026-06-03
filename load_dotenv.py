from dotenv import load_dotenv
import os

load_dotenv()

gtfs_path = os.getenv("GTFS")

gtfs_rt_path = os.getenv("GTFS-RT")