"""
summarize.py: Given cleaned data, create summary stats for each cell
"""
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

data_dir = Path('../data/coalesced')
out_dir = Path('../data/final')
grid = '../grid.geojson'


def main(data_dir, out_dir, grid):
    files = data_dir.glob('*.parquet')
    grid = gpd.read_file(grid)

    for file in files:
        df = pd.read_parquet(file)

        # Bin valid_time into half-months
        df['month'] = df['valid_time'].dt.month
        df['first_half'] = (
            df['valid_time'].dt.day / df['valid_time'].dt.days_in_month <= .5)
        df['month_half'] = 2 * df['month'] - df['first_half']

        # Create aggregated DataFrame for each x/y/half-month
        # I.e. after aggregation there's one row for each x-y-halfmonth
        agg = df.groupby(['x', 'y', 'month_half'])['vals'].agg([
            np.mean, np.std]).reset_index()

        # Merge with GeoJSON grid
        merged = agg.merge(grid, on=['x', 'y'])


if __name__ == '__main__':
    main()
