"""
Download and import
"""
import re
import tarfile
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlretrieve

import click
import geopandas as gpd
import pandas as pd
import rasterio
from rasterio.io import MemoryFile
from rasterio.windows import Window
from tqdm import tqdm


# url = 'HAS011421999'
# grid_path = 'grid.geojson'
@click.command()
@click.option(
    '-g',
    '--grid-path',
    required=False,
    default=None,
    type=click.Path(
        exists=True, file_okay=True, dir_okay=False, resolve_path=True),
    help='Path to grid GeoJSON file.')
@click.option(
    '--data-dir',
    required=False,
    default=None,
    type=click.Path(file_okay=False, dir_okay=True, resolve_path=True),
    help='Root of directory where to save extracted data.')
@click.argument('url', required=True, nargs=1, type=str)
def main(grid_path, data_dir, url):
    """Download and import NDFD GRIB files"""
    if not url.startswith('HAS'):
        raise ValueError('url should start with HAS, e.g. HAS011421999')

    # Query webpage to find individual tarball URLs in extract
    url = 'https://www1.ncdc.noaa.gov/pub/has/' + url
    urls = get_extract_urls(url)

    # Load grid
    grid = gpd.read_file(grid_path)

    # For each tarball url, download and import it
    for tar_url in urls:
        with TemporaryDirectory() as dirpath:
            # Download tar_url to that directory
            local_path = Path(dirpath.name) / Path(tar_url).name
            download_url(tar_url, local_path)

            with tarfile.open(local_path) as tf:
                import_tarfile(tf, grid, data_dir)


def import_tarfile(tf, grid, data_dir):
    """Import tarball of GRIB files and save to data directory

    - iterate over each member in the tarfile, extracting it into memory
    - pass that tarfile to MemoryFile
    - open the dataset with MemoryFile.open()
    - You now have a standard rasterio reader. No need to add the crs/transform
      because I already have the x/y coordinates in the raster's crs that I'm
      selecting.
    - Get the tags of the first band with dataset.tags(1)
    - Those tags tell you valid time; other forecast things
    - Keep cells corresponding to (x, y) pairs of grid
    - You should essentially be creating a DataFrame with columns:
        - x: grid x coord
        - y: grid y coord
        - time: timestamp in UTC of forecast _valid_ time
        - element: thing that is being forecasted, i.e. hourly temp/max temp/etc
        - fcst_time: timestamp in UTC of when forecast was made
        Other metadata? Unit of measurement?

    Figure out which file format is best for these incremental appends

    Args:
        - tf: opened tarfile
        - grid: DataFrame with `x` and `y` columns defining grid cells to select
        - data_dir: Where to save data
    """
    # Find members of interest:
    # Keep only files that are Z98
    # Z97 corresponds to 4-7 day forecasts
    # Z98 corresponds to 1-3 day forecasts
    names = [x for x in tf.getnames() if x[3:6] == 'Z98']

    minx, miny, maxx, maxy = (
        grid['x'].min(), grid['y'].min(), grid['x'].max(), grid['y'].max())
    window = Window.from_slices((minx, maxx + 1), (miny, maxy + 1))

    # Since you're only reading a part of the dataset, you need to adjust the
    # x/y grid values to be relative from the minx/miny
    grid['adj_x'] = grid['x'] - minx
    grid['adj_y'] = grid['y'] - miny

    for name in names:
        with rasterio.Env(), tf.extractfile(name) as f, MemoryFile(
                f.read()) as memfile, memfile.open() as dataset:

            # Expanded context manger for debugging
            # f = tf.extractfile(name)
            # memfile = MemoryFile(f.read())
            # dataset = memfile.open()

            # Read data of predefined window into array
            # Using window means least reading necessary compared to reading for
            # entire CONUS
            # Theoretically since the grid cells I'm interested in aren't an
            # even box, you could read less data by iterating over each cell as
            # its own window, but that might have higher overhead, and this is
            # simpler
            arr = dataset.read(1, window=window)

            # Select cell values according to indices adjusted for window extent
            # This syntax is basically equivalent to zip() over the x/y cols
            values = arr[grid['adj_x'].values, grid['adj_y'].values]
            msg = 'values should have same length as provided indices'
            assert len(values) == len(grid), msg

            # Create new dataframe with just desired cells and their values
            new_data = grid[['x', 'y']].copy()
            new_data['vals'] = values

            # Timestamp of when forecast was made
            time_regex = r'^(\d+)\s*sec\s*UTC$'
            fcst_time_str = dataset.tags(1)['GRIB_REF_TIME']
            fcst_time_int = int(re.match(time_regex, fcst_time_str).group(1))
            fcst_timestamp = datetime.utcfromtimestamp(fcst_time_int)

            # Timestamp of when forecast was valid for
            valid_time_str = dataset.tags(1)['GRIB_VALID_TIME']
            valid_time_int = int(re.match(time_regex, valid_time_str).group(1))
            valid_timestamp = datetime.utcfromtimestamp(valid_time_int)

            new_data['fcst_time'] = fcst_timestamp
            new_data['valid_time'] = valid_timestamp
            f'{name}.parquet'
            new_data.memory_usage(deep=True).sum()
            new_data.to_parquet('test.parquet')


def get_extract_urls(url):
    """Find urls of individual tarballs within extract
    """
    dfs = pd.read_html(url)
    assert len(dfs) == 1, 'More than 1 table on page'
    df = dfs[0]

    # Keep only Name columm
    df = df[['Name']]
    df = df[df['Name'].notnull()]
    df = df[df['Name'] != 'Parent Directory']
    return (url.rstrip('/') + '/' + df['Name']).values


class DownloadProgressBar(tqdm):
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)


def download_url(url, output_path):
    with DownloadProgressBar(unit='B', unit_scale=True, miniters=1,
                             desc=url.split('/')[-1]) as t:
        urlretrieve(url, filename=output_path, reporthook=t.update_to)


if __name__ == '__main__':
    main()
