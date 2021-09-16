# ------------------------------------------------------------------------------
# Spatial methods for economists using Python
# Exam 4
# ------------------------------------------------------------------------------

# Importing modules
# ------------------------------------------------------------------------------

import arcpy
from arcpy import env
import os

# Checking extension availability (not necessary)
# ------------------------------------------------------------------------------

arcpy.CheckExtension('Spatial')

# Directories and input files
# ------------------------------------------------------------------------------

wd = os.getcwd()  # Check where the working directory is
wd_data = os.getcwd() + r'\data'


# load shp (feature classes) and txt
conservation = wd_data + "/source/Conservation Areas/20210705_Conservation_Areas_INSPIRE_Dataset.shp"
green_belt = wd_data + "/source/England_Green_Belt_2019-20_WGS84/England_Green_Belt_2019-20_WGS84.shp"
land_reg = wd_data + "/source/Land_registry/lr_2020.txt"
local_plan = wd_data + '/source/Local_Planning_Authorities_(April_2019)_UK_BFC/Local_Planning_Authorities_(April_2019)_UK_BFC.shp'
major_towns = wd_data + "/source/Major_Towns_and_Cities_December_2015_Boundaries (1)/Major_Towns_and_Cities_December_2015_Boundaries.shp"
parks = wd_data + "/source/Parks and Gardens/ParksAndGardens_09Aug2021.shp"

# Checking if several coordinate systems exist
coord_list = set([arcpy.Describe(i).spatialReference.name
                  for i in [conservation, green_belt, local_plan, major_towns, parks]])
coord_list

# Listing transformations (checking manually is easier)
extent1 = arcpy.Describe(local_plan).extent
sr1 = arcpy.Describe(local_plan).spatialReference
sr2 = arcpy.Describe(green_belt).spatialReference
sr3 = arcpy.Describe(major_towns).spatialReference
arcpy.ListTransformations(sr2, sr1, extent1)
arcpy.ListTransformations(sr3, sr1, extent1)

arcpy.Describe(local_plan).spatialReference.name

# Local variables
# ------------------------------------------------------------------------------

# -------------------------------------------------------------------------------
print("...Make geodatabase storage space")

env.overwriteOutput = True
arcpy.CreateFileGDB_management(wd + '/data', "/A4.gdb")
out = wd + '/data' + '/A4.gdb/'

# -------------------------------------------------------------------------------
print("...Importing data and environment settings")
arcpy.management.CopyFeatures(local_plan, out + "local_plan")

# General environment settings
env.overwriteOutput = True
env.workspace = out

env.outputCoordinateSystem = out + "local_plan"
arcpy.env.geographicTransformations = "OSGB_1936_To_WGS_1984_7"
env.extent = out + "local_plan"

# Copying other boundaries
arcpy.management.CopyFeatures(conservation, out + "conservation")
arcpy.management.CopyFeatures(green_belt, out + "green_belt")
arcpy.management.CopyFeatures(major_towns, out + "major_towns")
arcpy.management.CopyFeatures(parks, out + 'parks')

# Creating feature class from X-Y coordinates text file
arcpy.ListSpatialReferences("*World*", spatial_reference_type="GCS")
sr_land_reg = 'Geographic Coordinate Systems/World/WGS 1984'
arcpy.MakeXYEventLayer_management(land_reg, 'lon', 'lat', wd + '/data ' + '/A4.gdb/land_reg_temp',  sr_land_reg)
arcpy.CopyFeatures_management(wd + '/data ' + '/A4.gdb/land_reg_temp', out + 'land_reg')

# -------------------------------------------------------------------------------
print("...All hail the fishnet")

originCoordinate = '0,0 0,0'  # Careful: the 'Go to XY' in the Map tab report y-x coords!
# Alternatively, you can compute the origin coordinates using a cursor
yaxis = '0,0 1,0'
#oppositeCoorner = '1066308.257489 2851754.642122'
extent1 = arcpy.Describe(local_plan).extent
cellSizeWidth = '3000'
cellSizeHeight = '3000'

arcpy.CreateFishnet_management(out + 'fishnet_3km', origin_coord=originCoordinate,
                               y_axis_coord=yaxis,
                               number_rows="350", number_columns="250", cell_width='3000', \
                               cell_height='3000',
                               labels='NO_LABELS', geometry_type='POLYGON')

arcpy.management.CreateFeatureclass(out, "centroids", "POINT")

# Municipality centroids using cursors
with arcpy.da.InsertCursor(out + "centroids", "SHAPE@") as cursor_centroid:
    with arcpy.da.SearchCursor(out + "fishnet_3km", "SHAPE@") as cursor_bound:
        for row in cursor_bound:
            cursor_centroid.insertRow([row[0].centroid])

# -------------------------------------------------------------------------------
print("Add and loading the raster")
# load shp (feature classes) and txt
dem = wd_data + "/source/DEM/eu_dem_v11_E30N30.TIF"
dem_1 = wd_data + "/source/DEM/eu_dem_v11_E30N30_mod.tif"
# dem_2 = wd_data + "/source/DEM/eu_dem_v11_E30N30.TIF.aux.xml"
# Checking if several coordinate systems exist
coord_list = set([arcpy.Describe(i).spatialReference.name
                  for i in [dem, dem_1]])
coord_list

# Listing transformations (checking manually is easier)
sr4 = arcpy.Describe(dem).spatialReference
#sr5 = arcpy.Describe(dem_1).spatialReference
arcpy.ListTransformations(sr4, sr1, extent1)
#arcpy.ListTransformations(sr5, sr1, extent1)

# Copying DEM data
arcpy.CopyRaster_management(dem, wd + "/data" + "/A4.gdb/" + 'dem')
arcpy.CopyRaster_management(dem_1, wd + "/data" + "/A4.gdb/" + 'dem_1')

arcpy.management.Resample(wd + "/data" + "/A4.gdb/" + 'dem',
                          wd + "/data" + "/A4.gdb/" + 'dem100m',"100 100","NEAREST")

# -------------------------------------------------------------------------------
print("...Map Algebra")

# Spatial Join
arcpy.analysis.SpatialJoin(out + 'fishnet_3km',
                           out + 'land_reg',
                           out + 'test',
                           join_operation='JOIN_ONE_TO_MANY', field_mapping='')

# Height
arcpy.sa.ZonalStatisticsAsTable(out + 'fishnet_3km', 'OID', out + 'dem100m/Band_1',
                         out + 'avg_height_per_cell', "DATA", 'MEAN')

# Slope
arcpy.sa.SurfaceParameters(out + "dem100m/band_1", 'SLOPE', "", "", "", "", output_slope_measurement='DEGREE').save(out + 'slope2')

arcpy.sa.ZonalStatisticsAsTable(out + 'fishnet_3km', 'OID', out + 'slope2/Band_1',
                         out + 'avg_slope_per_cell', "DATA", 'MEAN')

# Output the table
arcpy.TableToTable_conversion(out + "avg_height_per_cell",
                              "C:/Users/eugen/Downloads/Assignment_Group_4-main/data",
                              "avg_height_per_cell.csv")
arcpy.TableToTable_conversion(out + "avg_slope_per_cell",
                              "C:/Users/eugen/Downloads/Assignment_Group_4-main/data",
                              "avg_slope_per_cell.csv")
arcpy.TableToTable_conversion(out + "test",
                              "C:/Users/eugen/Downloads/Assignment_Group_4-main/data",
                              "test.csv")