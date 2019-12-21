import pyproj
from affine import Affine

proj_list = [
    '+proj=lcc', '+lat_0=25', '+lon_0=265', '+lat_1=25', '+lat_2=25', '+x_0=0',
    '+y_0=0', '+R=6371200', '+units=m', '+no_defs']
proj_str = ' '.join(proj_list)
crs = pyproj.CRS.from_proj4(proj_str)

a = 2539.70
b = 0
c = -2764474.35
d = 0
e = -2539.70
f = 3232111.71
aff = Affine(a, b, c, d, e, f)
