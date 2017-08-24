'''
Created on Aug 24, 2017

@author: xuwang
'''
'''
Created on Aug 24, 2017

@author: xuwang
'''
import sys
import os
import argparse
import csv
import PhotoScan

# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-wp", "--wpath", required=True, help="workingPath")
args = vars(ap.parse_args())
workingPath = args["wpath"]
print("Working path is: %s" % workingPath)

srcImagePath = workingPath
dem = workingPath+"dem.tif"
orthomosaic = workingPath+"ortho.tif"
project = workingPath+"project.psx"

files = os.listdir(srcImagePath)
file_list=[]
for file in files:
    if file.endswith(".tif"):
        filePath = srcImagePath + file
        file_list.append(filePath)

app = PhotoScan.Application()
doc = PhotoScan.app.document

PhotoScan.app.gpu_mask = 14
PhotoScan.app.cpu_enable = 8

chunk = PhotoScan.app.document.addChunk()
chunk.crs = PhotoScan.CoordinateSystem("EPSG::4326")
# Import photos
chunk.addPhotos(file_list, PhotoScan.MultiplaneLayout)
chunk.matchPhotos(accuracy=PhotoScan.HighAccuracy, 
                 preselection=PhotoScan.ReferencePreselection,
                 keypoint_limit = 15000,tiepoint_limit = 10000)
# Align photos                 
chunk.alignCameras(adaptive_fitting=True)
# Save project
doc.save(path=project, chunks=[doc.chunk])
# Assign GCPs
markerFile = "markerList"
markerList = open(workingPath+markerFile+".csv", "rt")

eof = False
line = markerList.readline() #reading the line in input file
while not eof:
    photos_total = len(chunk.cameras)         #number of photos in chunk
    markers_total = len(chunk.markers)         #number of markers in chunk
    sp_line = line.rsplit(",", 6)   #splitting read line by four parts
    camera_name = sp_line[0]        #camera label
    marker_name = sp_line[1]        #marker label
    x = int(sp_line[2])                #x- coordinate of the current projection in pixels
    y = int(sp_line[3])                #y- coordinate of the current projection in pixels
    cx = float(sp_line[4])            #world x- coordinate of the current marker
    cy = float(sp_line[5])            #world y- coordinate of the current marker
    cz = float(sp_line[6])            #world z- coordinate of the current marker
    flag = 0
    for i in range (0, photos_total):    
        if chunk.cameras[i].label == camera_name:
            for marker in chunk.markers:    #searching for the marker (comparing with all the marker labels in chunk)
                if marker.label == marker_name:
                    marker.projections[chunk.cameras[i]] = (x,y)        #setting up marker projection of the correct photo)
                    flag = 1
                    break
            if not flag:
                marker = chunk.addMarker()
                marker.label = marker_name
                marker.projections[chunk.cameras[i]] = (x,y)
            marker.reference.location = PhotoScan.Vector([cx, cy, cz])
            break
    line = markerList.readline()        #reading the line in input file
    # print (line)
    if len(line) == 0:
        eof = True
        break # EOF
markerList.close()
# Correct markers
markerList = open(workingPath+markerFile+".csv", "rt")
# Set the corrected markerList file
markerFileCorrected = open(workingPath+markerFile+"_c.csv",'wt')
try:
    writer = csv.writer(markerFileCorrected, delimiter=',', lineterminator='\n')
    eof = False
    line = markerList.readline() #reading the line in input file
    while not eof:    
        photos_total = len(chunk.cameras)         #number of photos in chunk
        markers_total = len(chunk.markers)         #number of markers in chunk
        sp_line = line.rsplit(",", 6)   #splitting read line by four parts
        camera_name = sp_line[0]        #camera label
        marker_name = sp_line[1]        #marker label
        x = int(sp_line[2])                #x- coordinate of the current projection in pixels
        y = int(sp_line[3])                #y- coordinate of the current projection in pixels
        cx = float(sp_line[4])            #world x- coordinate of the current marker
        cy = float(sp_line[5])            #world y- coordinate of the current marker
        cz = float(sp_line[6])            #world z- coordinate of the current marker
        for i in range (0, photos_total):    
            if chunk.cameras[i].label == camera_name:
                for marker in chunk.markers:    #searching for the marker (comparing with all the marker labels in chunk)
                    if marker.label == marker_name:
                        # print("marker: %s" % marker.label)
                        # print("camera: %s" % chunk.cameras[i])
                        # Error check
                        projection_m = marker.projections[chunk.cameras[i]].coord
                        reprojection = chunk.cameras[i].project(marker.position)
                        if not (reprojection is None or reprojection == 0):
                            error_pix = (projection_m - reprojection).norm()
                            # print("error pixel: %f" % error_pix)
                            if error_pix < 1.5:
                                writer.writerow((camera_name,marker_name,x,y,cx,cy,cz,error_pix))
                        break
                break
        line = markerList.readline()        #reading the line in input file
        if len(line) == 0:
            eof = True
            break # EOF
    markerList.close()
finally:
    markerFileCorrected.close()
# Remove all markers
for marker in chunk.markers:
    chunk.remove(marker)
# Reinsert markers
markerList = open(workingPath+markerFile+"_c.csv", "rt")
eof = False
line = markerList.readline() #reading the line in input file
while not eof:    
    photos_total = len(chunk.cameras)         #number of photos in chunk
    markers_total = len(chunk.markers)         #number of markers in chunk
    sp_line = line.rsplit(",", 7)   #splitting read line by four parts
    camera_name = sp_line[0]        #camera label
    marker_name = sp_line[1]        #marker label
    x = int(sp_line[2])                #x- coordinate of the current projection in pixels
    y = int(sp_line[3])                #y- coordinate of the current projection in pixels
    cx = float(sp_line[4])            #world x- coordinate of the current marker
    cy = float(sp_line[5])            #world y- coordinate of the current marker
    cz = float(sp_line[6])            #world z- coordinate of the current marker
    flag = 0
    for i in range (0, photos_total):    
        if chunk.cameras[i].label == camera_name:
            for marker in chunk.markers:    #searching for the marker (comparing with all the marker labels in chunk)
                if marker.label == marker_name:
                    marker.projections[chunk.cameras[i]] = (x,y)        #setting up marker projection of the correct photo)
                    flag = 1
                    break
            if not flag:
                marker = chunk.addMarker()
                marker.label = marker_name
                marker.projections[chunk.cameras[i]] = (x,y)
            marker.reference.location = PhotoScan.Vector([cx, cy, cz])
            break    
    line = markerList.readline()        #reading the line in input file
    # print (line)
    if len(line) == 0:
        eof = True
        break # EOF
markerList.close()
# Save project
doc.save(path=project, chunks=[doc.chunk])

chunk.updateTransform()

chunk.optimizeCameras(fit_f=True, fit_cxcy=True, fit_b1=True, fit_b2=True, fit_k1k2k3=True, fit_p1p2=True)

chunk.buildDenseCloud(quality=PhotoScan.Quality.UltraQuality, filter=PhotoScan.FilterMode.AggressiveFiltering)

chunk.buildModel(surface=PhotoScan.SurfaceType.HeightField, interpolation=PhotoScan.Interpolation.DisabledInterpolation, face_count=PhotoScan.FaceCount.HighFaceCount)

doc.save(path=project, chunks=[doc.chunk])

chunk.buildDem(source=PhotoScan.DataSource.DenseCloudData, interpolation=PhotoScan.Interpolation.DisabledInterpolation, projection=PhotoScan.CoordinateSystem("EPSG::32614"))

chunk.buildOrthomosaic(surface=PhotoScan.DataSource.ElevationData, blending=PhotoScan.BlendingMode.MosaicBlending, color_correction=False, projection=PhotoScan.CoordinateSystem("EPSG::32614"))

chunk.exportDem(dem, image_format=PhotoScan.ImageFormatTIFF, projection=PhotoScan.CoordinateSystem("EPSG::32614"), nodata=-9999, write_kml=False, write_world=False, tiff_big=False)

chunk.exportOrthomosaic(orthomosaic, image_format=PhotoScan.ImageFormatTIFF, raster_transform=PhotoScan.RasterTransformType.RasterTransformNone, projection=PhotoScan.CoordinateSystem("EPSG::32614"), write_kml=False, write_world=False, tiff_compression=PhotoScan.TiffCompressionNone, tiff_big=False)

doc.save(path=project, chunks=[doc.chunk])
