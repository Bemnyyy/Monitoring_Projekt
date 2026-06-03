import pandas as pd
from datetime import datetime
from load_dotenv import gtfs_path, gtfs_rt_path


calendar_dates_df = pd.read_csv(f"{gtfs_path}/calendar_dates.txt")
