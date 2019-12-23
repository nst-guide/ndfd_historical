import os.path
import re
import tempfile
from time import sleep

import click
import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import rasterio.mask
import requests
from shapely.geometry import box

import constants


# If you wanted to do bbox, you could get the cells of the four corners, and then include everything between them
# Something similar for polygons? Where you query all the cells of the exterior,
# and assume that inner cells are included. (I.e. no polygons with holes.)
@click.command()
@click.option(
    '--bbox',
    required=False,
    default=None,
    type=str,
    help='Bounding box to use for finding grid intersections.')
@click.option(
    '--elevations',
    is_flag=True,
    default=False,
    help='Whether to ping NWS API for elevations of each grid square.')
@click.argument(
    'file',
    required=False,
    nargs=-1,
    type=click.Path(
        exists=True, file_okay=True, dir_okay=False, resolve_path=True),
    default=None)
def main(bbox, elevations, file):
    if (bbox is None) and (file is None):
        raise ValueError('Either bbox or file must be provided')

    if (bbox is not None) and (file is not None):
        raise ValueError('Either bbox or file must be provided')

    if bbox:
        raise NotImplementedError(
            "Haven't figured out how to fill cell intersections from bbox")
        # bbox = '-120.4906,37.9606,-119.6604,38.7561'
        bbox = tuple(map(float, re.split(r'[, ]+', bbox)))
        gdf = gpd.GeoDataFrame(geometry=[box(*bbox)], crs={'init': 'epsg:4326'})
        gdf = gdf.to_crs(crs=constants.crs)
        int_gdf = intersect_with_grid(gdf.geometry[0].exterior.coords)

    if file:
        gdfs = [gpd.read_file(f) for f in file]
        gdf = gpd.GeoDataFrame(
            pd.concat(gdfs, sort=False),
            crs=gdfs[0].crs).to_crs(crs=constants.crs)

        # Get all coordinates
        all_coords = []
        for line in gdf.geometry:
            msg = 'only LineString geometry currently supported'
            assert line.type == 'LineString', msg
            for coord in line.coords:
                all_coords.append((coord[0], coord[1]))

        int_gdf = intersect_with_grid(all_coords)

    # If requested, find elevation of each grid square centroid from NWS
    # This requires two API calls: once for getting the forecast url, a second
    # time for getting a forecast. The elevation value is only included in the
    # forecast output.
    if elevations:
        centroids = int_gdf.centroid
        headers = {'accept': 'application/geo+json'}
        elevations = []
        for centroid in centroids:
            lon, lat = centroid.coords[0]
            url = f'https://api.weather.gov/points/{lat},{lon}'

            sleep(0.1)
            point_res = requests.get(url, headers=headers)
            # Points in Mexico/Canada return 404
            if point_res.status_code == 404:
                elevations.append(np.nan)
                continue
            forecast_url = point_res.json()['properties']['forecast']

            sleep(0.1)
            forecast_res = requests.get(forecast_url, headers=headers)
            ele = forecast_res.json()['properties']['elevation']

            assert ele['unitCode'] == 'unit:m', 'Elevation not in meters'
            value = ele['value']
            elevations.append(value)

        int_gdf['ele'] = elevations

    print(int_gdf.to_json())


def intersect_with_grid(int_coords, fill=False):
    """
    Args:
        - int_coords: projected coordinates to be used for intersection
        - fill: whether to include the interior of the intersected cells. I.e.
          if the coords of a box are provided and intersect with 0,0 and 4,4,
          this would include the entire 25-cell grid

    Returns:
        GeoDataFrame with three columns:
        - x: x coordinate of NDFD grid. A higher x seems to move down, towards the south?
        - y: y coordinate of NDFD grid. A higher y seems to move right, towards the east?
        - geometry: geometry of grid cell (reprojected back into WGS84)
    """
    grid_path = create_grid()
    with rasterio.Env(), rasterio.open(grid_path) as src:
        intersected_cells = set()
        for int_coord in int_coords:
            intersected_cells.add(src.index(*int_coord))

        if fill:
            intersected_cells = fill_cells(intersected_cells)

        # For each of the cells, generate its box
        cell_boxes = []
        for x, y in list(intersected_cells):
            cell_boxes.append([
                x, y, box(*src.xy(x, y, 'll'), *src.xy(x, y, 'ur'))])

    grid = gpd.GeoDataFrame(
        cell_boxes, columns=['x', 'y', 'geometry'], crs=constants.crs)
    return grid.to_crs(epsg=4326)


def fill_cells(cells):
    """Fill interior of given cells so that there are no holes.

    Args:
        - cells: tuples of (x, y) that represent existing cell intersections
    """
    # Generate cells covering all of min/max bounds, then intersect
    # I do this with fstopo already
    # The question is how to generate a polygon out of the current cells
    pass


def create_grid():
    """Create raster file conforming to NDFD 2.5km CONUS grid

    The easiest way to find the necessary constants is to find a
    correctly-formatted GRIB file, and run:
    ```
    with rasterio.Env(), rasterio.open('YEUZ98_KWBN_201701010519') as r:
        print(r.bounds)
        print(r.transform)
        print(r.crs)
    ```
    """
    # In NDFD coordinates, it spans from the minx to maxx with 2145 horizontal
    # cells
    # If spans from miny to maxy in 1377 vertical cells.
    # This makes each side of each cell 2,539.7 meters
    x = np.linspace(-2764474.35, 2683182.15, 2145)
    y = np.linspace(-265055.18999999994, 3232111.71, 1377)
    # Make 2D arrays for x and y
    X, Y = np.meshgrid(x, y)
    # set third dimension to 0 for this example, with same dimensions as X and Y
    Z = X * 0

    path = os.path.join(tempfile.mkdtemp(), 'grid.tif')
    with rasterio.open(path, 'w', driver='GTiff', height=Z.shape[0],
                       width=Z.shape[1], count=1, dtype=Z.dtype,
                       crs=constants.crs,
                       transform=constants.aff) as new_dataset:
        new_dataset.write(Z, 1)
    return path


if __name__ == '__main__':
    main()
