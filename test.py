# Source - https://stackoverflow.com/a/56642535
# Posted by PKey, modified by community. See post 'Timeline' for change history
# Retrieved 2026-06-05, License - CC BY-SA 4.0

from google.transit import gtfs_realtime_pb2
import os
import requests


def main():
    feed = gtfs_realtime_pb2.FeedMessage()
    url = ("https://www.nvbw.de/fileadmin/user_upload/service/open_data/fahrplandaten_ohne_liniennetz/bodo.zip")#('https://opendata.vpe.de/data/gtfs/realtime/service-alerts.pbf?')
    get_feed(feed, url)

def printResults(feed):
    from datetime import datetime
    ts = int(str(feed.header.timestamp))
    print("Last update: " + datetime.fromtimestamp(ts).strftime('%d-%m-%Y %H:%M:%S'))
    for entity in feed.entity:
        print (str(entity.trip_update.trip.trip_id)+';')
        with open('output.txt', mode='w') as f:
            for entity in feed.entity:
                if entity.HasField('trip_update'):
                        f.write(str(entity.trip_update.trip.trip_id)+';')
def get_feed(feed, url):
    #proxies = {'http': '127.0.0.1:5555','https': '127.0.0.1:5555'}
    response = requests.get(url, allow_redirects=True)#,proxies=proxies)
    print("response content:", response.content)
    try:
        feed.ParseFromString(response.content)
        printResults(feed)
    except :
        print("Oops!  That was no valid data. Try again...\n\n" , response.content)
        try:
            from google.protobuf import text_format
            text_format.Parse(response.content.decode('UTF-8'), feed, allow_unknown_extension=True)
            print("Parse with text format successfully.")
            printResults(feed)
        except text_format.ParseError as e:
            raise IOError("Cannot parse file %s." % (str(e)))
if __name__ == "__main__":
    main()
