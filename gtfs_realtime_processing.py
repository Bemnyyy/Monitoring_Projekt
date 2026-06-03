from google.transit import gtfs_realtime_pb2
import requests
from dotenv import load_dotenv
from load_dotenv import gtfs_rt_path

load_dotenv(gtfs_rt_path)

feed = gtfs_realtime_pb2.FeedMessage()
response = requests.get(gtfs_rt_path)
feed.ParseFromString(response.content)
for entity in feed.entity:
    if entity.HasField("trip_update"):
        print(entity.trip_update)