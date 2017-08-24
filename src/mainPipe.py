'''
Created on Aug 24, 2017

@author: Xu Wang
'''
"""
Main pipeline program.
"""

from datetime import datetime
import os
import re
import shutil
import pymysql
import csv
import exifread
import numpy
import cv2
from pyimagesearch.shapedetector import ShapeDetector
import utm
import imutils
from apscheduler.schedulers.blocking import BlockingScheduler

preProcessedPath = 'F:\\Xu\\uav_preprocessed'
processingPath = 'F:\\Xu\\uav_processing'
manifest = 'manifest.txt'
jobQueue = 'queue.csv'
gcpSource = 'gcpList.csv'
markerList = 'markerList.csv'
gcpNum = 0
targetDatabase = 'wheatgenetics'

def getQueueStatus():
# Read the processing queue file
    queueFile = open(processingPath+'\\'+jobQueue,"r")
    lineNum = 0;
    isReady = False
    for line in queueFile:
        lineNum = lineNum+1
    queueFile.close()
    if lineNum==1:
        words=re.split(",|\n", line)
        if words[1]=="processing":
            print("There is a job being processed in the queue.")
            isReady = False
        else:
            print("The job in the queue is done. Emptying the queue...")
            isReady = True
            # Remove the second line from the queue.txt
            queueFile = open(processingPath+'\\'+jobQueue,"w")
            queueFile.write("")
            queueFile.truncate()
            queueFile.close()
    else: # Only header line meaning no job is being processed
        print("There is no job found in the queue. Ready to add new jobs in the queue.")
        isReady = True
    return isReady

def getFlightFolderStatus():
    isReady = False
    # Read the pre-processed FOLDER (dir)
    flightFolder = next(os.walk(preProcessedPath))[1]
    if len(flightFolder)>0:
        # Check the completeness of the folder
        if manifest in next(os.walk(preProcessedPath+'\\'+flightFolder[0]))[2]:
            # Get the total Tif number from the manifest file
            manifestFile = open(preProcessedPath+'\\'+flightFolder[0]+'\\'+manifest,"r") # Check the availability of manifest.txt
            manifestTifNum = 0
            for line in manifestFile:
                if line.find(".tif") != -1:
                    manifestTifNum = manifestTifNum+1
            manifestFile.close()
            # Get the total Tif number in the folder
            realTifNum = 0
            for pFile in next(os.walk(preProcessedPath+'\\'+flightFolder[0]))[2]:
                if pFile.find(".tif") != -1:
                    realTifNum = realTifNum+1
            if manifestTifNum==realTifNum:
                isReady = True
                print("New folder is detected: %s" % flightFolder[0])
                print("Images in the folder are completely uploaded.")
            else:
                isReady = False
                print("New folder is detected: %s" % flightFolder[0])
                print("Images in the folder are not completely transferred.")
        else:
            print("Manifest.txt not found.")
    else:
        print("No new folder found.")
        isReady = False
    return isReady

def moveFiles():
    isReady = False
    flightFolder = next(os.walk(preProcessedPath))[1]
    sourcePath = preProcessedPath+'\\'+flightFolder[0]
    targetPath = processingPath
    try:
        target = shutil.move(sourcePath,targetPath)
        print("Moving files to %s." % target)
        isReady = True
    except FileNotFoundError:
        isReady = False
    return isReady

def updateQueueFile():
    newFolder = next(os.walk(processingPath))[1]
    queueFile = open(processingPath+'\\'+jobQueue,"w")
    queueFile.write(newFolder[0]+",processing")
    queueFile.truncate()
    queueFile.close()
    print("A new job - %s has been added to the queue." % newFolder[0])
    return newFolder[0]

def getGCPListFromDB(flight_id):
    # Connect to the database
    conn = pymysql.connect(host='beocat.cis.ksu.edu', port=6306,
                       user='xuwang', passwd = 'xuwang',
                       db=targetDatabase)
    gcpListFile = open(processingPath+'\\'+gcpSource,'w') 
    try:
        writer = csv.writer(gcpListFile, delimiter=',', lineterminator='\n')
        writer.writerow(('Index','Longitude','Latitude','Altitude'))
        with conn.cursor() as cursor:
            querySQLString = "SELECT uas_run_test.experiment_id FROM uas_run_test WHERE uas_run_test.flight_filename = %s"
            cursor.execute(querySQLString, (flight_id))
            exp_id = cursor.fetchone()
            querySQLString = "SELECT gcp.index,gcp.longitude,gcp.latitude,gcp.altitude FROM gcp WHERE gcp.experiment = %s"
            cursor.execute(querySQLString, (exp_id))
            gcpAmt = 0
            for row in cursor:
                gcpAmt = gcpAmt+1
                writer.writerow(row)
                print(row)
        print("GCP list is updated.")
    finally:
        cursor.close()
        conn.close()
    return gcpAmt

def getExifFromImage(srcImage):
    # Get EXIF GPS attributes
    exifAttrib = open(srcImage, 'rb')
    tags = exifread.process_file(exifAttrib, details=False)
    longiRef = -1
    latiRef = 1
    for tag in tags.keys():
        if tag == 'GPS GPSLongitudeRef':
            longiRefStr = str(tags[tag])
    #         print("Longitude Ref: %s" % longiRefStr)
        elif tag == 'GPS GPSLatitudeRef':
            latiRefStr = str(tags[tag])
    #         print("Latitude Ref: %s" % latiRefStr)
        elif tag == 'GPS GPSLatitude':
            latitudeStr = str(tags[tag])[1:-1]
    #         print("Latitude: %s" % latitudeStr)
        elif tag == 'GPS GPSLongitude':
            longitudeStr = str(tags[tag])[1:-1]
    #         print("Longitude: %s" % longitudeStr)
        elif tag == 'GPS GPSAltitude':
            if len(str(tags[tag]).split('/')) == 2:
                altitude = float(str(tags[tag]).split('/')[0]) / float(str(tags[tag]).split('/')[1])
            else:
                altitude = float(str(tags[tag]).split('/')[0])
    #         print ("Altitude: %.3f" % altitude)
    if latiRefStr == "N":
        latiRef = 1
    else:
        latiRef = -1
    latitudeDeg = float(latitudeStr.split(',')[0])
    latitudeMin = float(latitudeStr.split(',')[1])
    if len(latitudeStr.split(',')[2].split('/')) == 2:
        latitudeSec = float(latitudeStr.split(',')[2].split('/')[0]) / float(latitudeStr.split(',')[2].split('/')[1])
    else:
        latitudeSec = float(latitudeStr.split(',')[2].split('/')[0])
    latitude = latiRef * (latitudeDeg + latitudeMin / 60 + latitudeSec / 3600)
    # print("Latitude: %.7f" % latitude)
    if longiRefStr == "W":
        longiRef = -1
    else:
        longiRef = 1
    longitudeDeg = float(longitudeStr.split(',')[0])
    longitudeMin = float(longitudeStr.split(',')[1])
    if len(longitudeStr.split(',')[2].split('/')) == 2:
        longitudeSec = float(longitudeStr.split(',')[2].split('/')[0]) / float(longitudeStr.split(',')[2].split('/')[1])
    else:
        longitudeSec = float(longitudeStr.split(',')[2].split('/')[0])
    longitude = longiRef * (longitudeDeg + longitudeMin / 60 + longitudeSec / 3600)
    # print("Latitude: %.7f" % longitude)
    return [longitude, latitude, altitude]

def matachGCP(theDist, pointCamera, gcpFile):
    gcpRecord = numpy.recfromcsv(gcpFile,delimiter=',')
    # Match the correct GCP
    gcpLongi = 0
    gcpLati = 0
    gcpAlti = 0
    gcpLabel = 0
#     closeGCP = 0
    minDist = 1000
    secondMinDist = 1000;
    secGCPLabel = 0;
    for gcp in gcpRecord:
        [utmGCPx, utmGCPy, latGCPzone, longGCPzone] = utm.from_latlon(gcp[2],gcp[1])
        point_gcp = numpy.array((utmGCPx, utmGCPy))
#         print(numpy.sqrt(numpy.sum((pointCamera - point_gcp) ** 2)) - theDist)
        if numpy.sqrt(numpy.sum((pointCamera - point_gcp) ** 2)) <= 10:
            diffDist = numpy.absolute(numpy.sqrt(numpy.sum((pointCamera - point_gcp) ** 2)) - theDist)
            if diffDist <= minDist:
                secondMinDist = minDist
                secGCPLabel = gcpLabel
                minDist = diffDist
                gcpLongi = gcp[1]
                gcpLati = gcp[2]
                gcpAlti = gcp[3]
                gcpLabel = gcp[0]
    print("First Min Distance: %f - GCP-%d; Seconde Min Distance: %f - GCP-%d" % (minDist, gcpLabel, secondMinDist, secGCPLabel))
    return [gcpLongi, gcpLati, gcpAlti, gcpLabel]

def detectGCP(srcImagePath, srcGCPFile):
    srcImages = os.listdir(srcImagePath)
    imageFiles  = []
    for img in srcImages:
        if img.find('_1.tif') != -1:
            imageFiles = imageFiles + [img]
    # Set the shrink image size, always 1/2 of the regular size
    # Hence it should be equal to the center of the image
    img_width = 1280
    img_height = 960
    sh_ratio = 0.5
    # Set the GCP area filter value
    th_GCP = 210
    # Set the Gaussian filter size
    gaussian_size = 3
    # Set the detected contour area size
    contour_min_size = 40
    contour_max_size = 70
    # Get system time to mark the output marker file
    # t_index = str(datetime.now().strftime('%Y%m%d_%H%M%S'))
    # Set final output file name
    finalFile = open(srcImagePath+'\\'+markerList,'w')
    try:
        # Create final output file
        writer = csv.writer(finalFile, delimiter=',', lineterminator='\n')
        # Header row if needed
        # writer.writerow(('camera_label','marker_label','marker_px','marker_py','gcp_longitude',
        #                 'gcp_latitude','gcp_altitude'))
        # Detect each individual image and match
        for imf in imageFiles:
            sh_width = int(img_width*sh_ratio)
            sh_height = int(img_height*sh_ratio)
            img2proc = cv2.imread(srcImagePath+'\\'+imf)
            # Resize, by default shrink by 50%
            resized = imutils.resize(img2proc, width=sh_width, height=sh_height)
            # Calculate the shrink ratio
            ratio = img2proc.shape[0]/float(resized.shape[0])
            # Grey scaling
            gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
            # Gaussian blur
            blurred = cv2.GaussianBlur(gray, (gaussian_size, gaussian_size), 0)
    #         cv2.imshow("Image", blurred)
    #         cv2.waitKey(0)
            # Set the threshold to filter out the GCP area
            thresh = cv2.threshold(blurred, th_GCP, 255, cv2.THRESH_BINARY)[1]
            # Find contours of the filtered areas
            cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cnts = cnts[0] if imutils.is_cv2() else cnts[1]
            # Load shape detector
            sd = ShapeDetector()
            # Initialize the center of the GCP (cX,cY) coordinates
            cX = 0
            cY = 0
            # The total number of the square shape and rectangle shape detected
            snum = 0
            shape = "unidentified"
            contourSize = 0
            for c in cnts:
                shape = "unidentified"
                shape = sd.detect(c)
    #             print(shape)
                if cv2.contourArea(c)>=contour_min_size and cv2.contourArea(c)<=contour_max_size and shape == "square": # or shape == "rectangle"):
                    print("Contour size: %f" % cv2.contourArea(c))
                    snum = snum+1
            if snum == 1:
                # Either a square OR a rectangle detected
                # Use the detected shape as a potential GCP
                for c in cnts:
                    contourSize = cv2.contourArea(c)
                    shape = sd.detect(c)
                    if cv2.contourArea(c)>=contour_min_size and cv2.contourArea(c)<=contour_max_size and shape == "square": # or shape == "rectangle"):
                        break
                # Matching GCPs
                M = cv2.moments(c)
                if M["m00"] != 0:
                    # Calculate the center of the tile
                    cX = int(round((M["m10"] / M["m00"]) * ratio))  # * ratio
                    cY = int(round((M["m01"] / M["m00"]) * ratio))  # * ratio
                    # print("Image: %s, cX: %d, cY: %d, cArea: %.1f" % (imf, cX, cY, contourSize))
                else:
                    cX = 0
                    cY = 0
                if cX != 0 and cY != 0 and (cX>int(img_width*0.1) and cX<int(img_width*0.9)) and (cY>int(img_height*0.1) and cY<int(img_height*0.9)):
                    # get image EXIF
                    [longi,lati,alti] = getExifFromImage(srcImagePath+'\\'+imf)
                    [uTMx,uTMy,longZone,latZone] = utm.from_latlon(lati, longi)
                    pointCamCenter = numpy.array((uTMx,uTMy))
                    pointImgCenter = numpy.array((sh_width-1, sh_height-1))
                    pointGcpCenter = numpy.array((cX, cY))
                    pixelDist2ImgCenter = numpy.sqrt(numpy.sum((pointGcpCenter - pointImgCenter) ** 2))
                    thDist = 12*2.54*0.01*4*0.9/contourSize*pixelDist2ImgCenter
                    #print("Pixel distance: %.2f, Contour size: %f, Real distance: %.2f" 
                    #% (pixelDist2ImgCenter, contourSize, thDist))
                    print(imf)
                    [gcpLongitude, gcpLatitude, gcpAltitude, gcpLab] = matachGCP(thDist, pointCamCenter, srcGCPFile)
                    print("gcplong: %f, gcpLat: %f, gcpAlt: %f" % (gcpLongitude, gcpLatitude, gcpAltitude))
                    # Output
                    if gcpLongitude != 0 and gcpLatitude != 0 and gcpAltitude != 0:
                        writer.writerow((imf, gcpLab, cX, cY, gcpLongitude, gcpLatitude, gcpAltitude))
            elif snum == 2:
                # If two shapes detected, use the square
                for c in cnts:
                    if sd.detect(c) == "square":
                        break
                print("2-Not sure!")
            else:
                # If more than two shapes detected
                print("3-Not sure!")
    finally:
        finalFile.close()
        
def pipeline():
    print('Tick! The time is: %s' % datetime.now())
    isQueueReady = getQueueStatus()
    if isQueueReady:
        isNewFolderReady = getFlightFolderStatus()
        if isNewFolderReady:
            # Move the folder from preprocessed to processing
            print("Moving files...")
            isMoveReady = moveFiles()
            if isMoveReady:
                # Write new job in the queue file
                flightFolder = updateQueueFile()
                # Connect to database, get all supporting data
                gcpNum = getGCPListFromDB(flightFolder)
                # Get GCPs
                if gcpNum > 0:
                    detectGCP(processingPath+'\\'+flightFolder, processingPath+'\\'+gcpSource)
                # Start photogrammetry processing
                    workingPath = processingPath+'/'+flightFolder+'/'
                    os.system("\"C:\Program Files\Agisoft\PhotoScan Pro\photoscan.exe\" -r F:/uav_processing/photoscanPy.py -wp %s" % workingPath)
                # Once processed, move the folder to DONE, change the queue file
                
                #
            
            
if __name__ == '__main__':
    scheduler = BlockingScheduler()
    scheduler.add_job(pipeline, 'interval', seconds=300)
    print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
    