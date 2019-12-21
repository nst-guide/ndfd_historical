

#### Get NDFD CONUS indices for geometry

Download any georeferenced CONUS file, for example:
[YEUZ98_KWBN_201701010003](https://nomads.ncdc.noaa.gov/data/ndfd/201701/20170101/YEUZ98_KWBN_201701010003).

```
# Keep only the first band
gdal_translate YEUZ98_KWBN_201701010003 -b 1 -of GRIB YEUZ98_KWBN_201701010003_band1

```