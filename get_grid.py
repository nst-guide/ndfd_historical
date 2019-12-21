from io import BytesIO
import numpy as np
import rasterio
import geopandas as gpd
from shapely.geometry import Point, box
import pyproj
from affine import Affine
import rasterio.mask

proj_list = [
    '+proj=lcc',
    '+lat_0=25',
    '+lon_0=265',
    '+lat_1=25',
    '+lat_2=25',
    '+x_0=0',
    '+y_0=0',
    '+R=6371200',
    '+units=m',
    '+no_defs'
]
proj_str = ' '.join(proj_list)
crs = pyproj.CRS.from_proj4(proj_str)

a = 2539.70
b = 0
c = -2764474.35
d = 0
e = -2539.70
f = 3232111.71
aff = Affine(a, b, c, d, e, f)

# Click
# arg: bbox
# arg: geometry file
# For now, only linestrings
# If you wanted to do bbox, you could get the cells of the four corners, and then include everything between them
# Something similar for polygons? Where you query all the cells of the exterior,
# and assume that inner cells are included. (I.e. no polygons with holes.)
def main():
    # Load bbox/file
    #
    gdf = gpd.read_file('/Users/kyle/github/mapping/nst-guide/create-database/data/pct/line/halfmile/CA_Sec_A_tracks.geojson')
    trk_proj = gdf.to_crs(crs)

    # Get all coords and put into list
    all_coords = []
    for line in trk_proj.geometry:
        for coord in line.coords:
            all_coords.append((coord[0], coord[1]))

    intersected_cells = intersect_with_grid(all_coords)
    pass


def intersect_with_grid(int_coords):
    """
    Args:
        - int_coords: projected coordinates to be used for intersection
    """
    fname = create_grid()
    with rasterio.Env(), rasterio.open(fname) as src:
        intersected_cells = set()
        for int_coord in int_coords:
            intersected_cells.add(src.index(*int_coord))

        # For each of the cells, generate its box
        cell_boxes = []
        for x, y in list(intersected_cells):
            cell_boxes.append([x, y, box(*src.xy(x, y, 'll'), *src.xy(x, y, 'ur'))])

    grid = gpd.GeoDataFrame(cell_boxes, columns=['x', 'y', 'geometry'], crs=crs)
    from keplergl_quickvis import Visualize
    Visualize(grid.to_crs(epsg=4326))
    grid.to_crs(epsg=4326)

    cells_dict

    x, y = list(intersected_cells)[0]

    src.xy(x, y, 'll')
    src.xy(x, y, 'ur')
    point = Point(src.xy(x, y))
    gpd.GeoDataFrame(geometry=[point], crs=crs).to_crs(epsg=4326)
    src.xy(0, y)
    return intersected_cells

def create_grid():
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

    # TODO use tempfile
    new_dataset = rasterio.open('test.tif', 'w', driver='GTiff', height=Z.shape[0], width=Z.shape[1], count=1, dtype=Z.dtype, crs=crs, transform=aff)
    new_dataset.write(Z, 1)
    new_dataset.close()
    return 'test.tif'


