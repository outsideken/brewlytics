import pandas as pd

url = 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.csv'

df = pd.read_csv(url)

output_table = df
