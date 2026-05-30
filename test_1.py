# this is test so see how i can extract the given data to display them

import os
from dotenv import load_dotenv

load_dotenv()

gtfs_path = os.getenv("GTFS")
gtfsrt = os.getenv("GTFS-Rt")

