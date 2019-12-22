# National Digital Forecast Database: Historical

## Objective

Create a map layer with historical weather information for a given geometry
within the continental US.

The clearest way to do this is with data from the [National Digital Forecast
Database (NDFD)][ndfd_home], which has historical weather _forecasts_. Because
of the limited number and geographic dispersion of actual weather stations, this
is the easiest way to have weather data for any portion of the continental US.

The NDFD is a grid that spans the following box:

![[CONUS bounds][ndfd_srs]](assets/conusGridSmall.jpg)

[ndfd_srs]: https://www.weather.gov/mdl/ndfd_srs
[ndfd_home]: https://www.ncdc.noaa.gov/data-access/model-data/model-datasets/national-digital-forecast-database-ndfd

## Plan

- Download large sections of bulk historical forecasts for a single WMO category at a time.
- It appears that there are NDFD files saved hourly, but forecasts for 3 to 24 hour periods. Use the file closest to the forecast valid time.
<!-- - Update index file to keep track of which files have been imported. -->
- Extract numerical data from grid, save it as a Numpy file (.npy) to S3
- After all the data for a given WMO category is extracted, create distributions of the measurement type for day/week/month of interest.
- With small data files with distributions of interest, set up code to map a clicked point to a gridded cell.

## NDFD Notes

There are a total of 67 weather "elements" forcasted in the NDFD program. For a
full list, see [this Excel spreadsheet][ndfd_elements.xls], sheet "NDFD
Elements".

[ndfd_elements.xls]: https://graphical.weather.gov/docs/NDFDelem_complete.xls

For initial exploration, I'll only look at the following elements:

| Element                              | "T1T2" Code |
|--------------------------------------|-------------|
| Temperature                          | YE          |
| 12-hour Probability of Precipitation | YD          |
| Quantitative Precipitation Forecast  | YI          |
| Wind Speed                           | YC          |

NDFD provides files for different portions of the country. The third letter
after the `T1T2` code represents the geographical region of interest. For
example, `U` corresponds to CONUS, or the entire continental US.

It would be possible to download weather data for portions of the US at a time,
and then merge them if the desired geometry crossed the boundaries of a
particular region, but the merging would not necessarily be straightforward, and
you'd have to figure out grid intersections for different grids.

Since we're interested in historical weather for the entire United States, the
third value should be `U`, which corresponds to CONUS. The first column
(`Designator`) on the `NDFD_Files` tab of the above-linked spreadsheet shows the
ID's for each combination of forecast element and forecast region.

If you mix, for example, data that starts with `YEU` with data that starts with
`YEP`, you'll get arrays of different sizes, because `YEP` corresponds to hourly
temperature in the Pacific Northwest, while `YEU` corresponds to hourly
temperature for all of CONUS.

There's a separate column in that Excel spreadsheet that gives the forecast
ranges for each element. When the value of `A2ii` is `Z98`, the downloaded
dataset will have forecasts at smaller intervals for the next three days. When
the value of `A2ii` is `Z97`, the downloaded dataset will have forecasts for
wider intervals from four to seven days in advance.

Since we wish to use NDFD forecasts as a proxy for actual historical weather,
and since NDFD forecasts have been created daily, only the `Z98` dataset is ever
needed, because we only care about the 24 hours of data following the
prediction.

### Downloading the data

NOAA has an [FTP][ndfd_ftp]/[HTTPS][ndfd_https] server with NDFD data, however
the data on those servers only go back to January 2017, and additionally those
servers are quite slow.

Alternatively, you can [download the data in bulk by WMO header][ndfd_bulk_wmo].

[ndfd_ftp]: ftp://nomads.ncdc.noaa.gov/NDFD/
[ndfd_https]: https://nomads.ncdc.noaa.gov/data/ndfd/
[ndfd_bulk_wmo]: https://www.ncdc.noaa.gov/has/HAS.FileAppRouter?datasetname=9959_02&subqueryby=STATION&applname=&outdest=FILE

### Grid size

It appears that since 2005 CONUS has had two and only two grids: a 5km-cell grid
and a 2.5km-cell grid. From guess and check,

- August 1, 2014 and prior has a 5km grid. The 5km grid has 1073 longitude bins and 689 latitude bins.
- October 1, 2014 and later has a 2.5km grid. The 2.5km grid has 1377 x 2145 cells.

More details about the CONUS grids are [found here](https://www.weather.gov/mdl/ndfd_srs).

### Temporal resolution

The temporal resolution of temperature data is 3 hours, but reports are created every hour. So a file exists for every hour of the day, but temperature forecasts are for 00:00, 03:00, 06:00, etc.

From [ECMWF](https://confluence.ecmwf.int/display/CKB/How+to+read+or+decode+a+GRIB+file):

> `dataDate` and `dataTime` indicate the date/time we forecast _from_. `validityDate` and `validityTime` indicate the date/time we forecast _for_.

## Reading GRIB data

```py
import pygrib

grbs = pygrib.open('ds.temp.bin')
# Use .message() to call a layer, a single forecast period
# Each GRIB file has many layers. Just pick the layer closest in time
grb = grbs.message(1)

# Now grb has a lot of metadata:
print(grb.keys())

# To get the data itself, call .data()
# If you call .data() without arguments, it retrieves the entire dataset
# Alternatively you can pass a bounding box
print(grb.data())

# The output is a tuple with three 2D Numpy arrays
# The first is an array with the parameter of interest
print(grb.data()[0])

# The second is a 2D array with latitudes, and the third is a 2D array with
# longitudes. I'm not sure exactly why these are 2D arrays instead of 1D, but
# it's probably a projection issue.
print(grb.data()[1])
print(grb.data()[2])
```

## Glossary

- CONUS: Continental United States
- WMO Category: abbreviation for specific weather element

## Resources

NDFD sector definitions: https://www.weather.gov/mdl/degrib_dataloc#ndfd