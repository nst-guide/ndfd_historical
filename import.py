"""
Download and import
"""
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlretrieve

import geopandas as gpd
import pandas as pd
from rasterio.io import MemoryFile

import constants

# url for HAS extract to download
# path to grid.geojson
url = 'https://www1.ncdc.noaa.gov/pub/has/HAS011421999/'
grid = 'grid.geojson'
def main(url, grid):
    urls = get_extract_urls(url)

    # Load grid
    grid = gpd.read_file(grid)

    for tar_url in urls:
        dirpath = TemporaryDirectory()
        with TemporaryDirectory() as dirpath:
            # Download tar_url to that directory
            local_path = Path(dirpath.name) / Path(tar_url).name
            urlretrieve(tar_url, local_path)

            data = import_tarfile(local_path)


def import_tarfile(local_path, grid):
    """
    - open tarfile
    - iterate over each member in the tarfile, extracting it into memory
    - pass that tarfile to MemoryFile
    - open the dataset with MemoryFile.open()
    - You now have a standard rasterio reader. Add the crs and transform
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
    """
    # extract tarball
    t = tarfile.open(local_path)
    t.getmembers()

    # Keep only files that are Z98

    test = t.extractfile('YEUZ98_KWBN_201507010021')
    memfile = MemoryFile(test.read())
    dataset = memfile.open()
    data_array = dataset.read()
    data_array.shape
    memfile
    dataset.crs
    dataset.tag_namespaces(1)
    dataset.tags(1)
    dataset.tags(2)
    dataset.tags('GRIB')
    dataset.bounds
    dataset.profile
    dataset.meta


    with MemoryFile(data) as memfile:
        with memfile.open() as dataset:
            data_array = dataset.read()

    t.getmember('YEUZ98_KWBN_201507010021')
    t.getnames()
    local_path



    #
    pass

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
    return (url + df['Name']).values

if __name__ == '__main__':
    main()
