import pandas as pd
import dotenv
from datetime import datetime
from load_dotenv import gtfs_path, gtfs_rt_path


calendar_dates_df = pd.read_csv(f"{gtfs_path}/calendar_dates.txt")

check_date = datetime(2026, 4, 29)
date_str = check_date.strftime("%Y%m%d")
weekday_name = check_date.strftime("%A").lower()

def check_service_availability(service_id, check_date_str, check_weekday):
    exceptions = calendar_dates_df[(calendar_dates_df["service_id"] == service_id) & (calendar_dates_df["date"] == int(check_date_str))]

    if not exceptions.empty:
        exception_type = exceptions.iloc[0]["exception_type"]
        if exception_type == 1:
            return True #service explizit hinzugefügt
        elif exception_type == 2:
            return False #Service explizit gestrichen
        

test_service_id = input(f"Service-Id {"de:vpe:service"}:")#'de:vpe:service:32' # ACHTUNG HARD CODED
is_available = check_service_availability(test_service_id, date_str, weekday_name)

print(f"Service {test_service_id} verfügbar am {check_date.strftime('%d.%m.%Y')}: {is_available}")