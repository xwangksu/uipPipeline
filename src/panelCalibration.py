'''
Created on Nov 13, 2017

@author: xuwang
'''
import cv2
import matplotlib.pyplot as plt
import numpy
import os
import micasense.metadata as metadata
import micasense.utils as msutils
from pyimagesearch.shapedetector import ShapeDetector
import imutils
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
import argparse

def panelDetect(image,b_th,ct_th):
    image = cv2.imread(image)
    resized = imutils.resize(image, width=640, height=480)
    ratio = image.shape[0] / float(resized.shape[0])
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blurred, b_th, 255, cv2.THRESH_BINARY)[1]
#     cv2.imshow("Image", thresh)
#     cv2.waitKey(0)
    cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if imutils.is_cv2() else cnts[1]
    sd = ShapeDetector()
    # loop over the contours
    sq=0
    for c in cnts:
        shape = "unidentified"
        M = cv2.moments(c)
        if M["m00"] != 0:
            cX = int(round((M["m10"] / M["m00"]))) # * ratio
            cY = int(round((M["m01"] / M["m00"]))) # * ratio
            shape = sd.detect(c)
        if shape == "square":
            # print(shape)
            # print("Estimated contour size: %f" % (cv2.contourArea(c)))
            if cv2.contourArea(c)>ct_th:
                sq +=1
                c = c.astype("float")
                c *= ratio
                c = c.astype("int")
                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.04 * peri, True)
                cv2.drawContours(image, [c], -1, (0, 255, 0), 1)
                cv2.putText(image, shape, (cX, cY), cv2.FONT_HERSHEY_SIMPLEX,0.5, (255, 255, 255), 1)
#                 cv2.imshow("Image", image)
#                 cv2.waitKey(0)
    if sq == 1:
        return approx
    else:
        return [[[0,0]],[[0,0]],[[0,0]],[[0,0]]]

# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-pp", "--ppath", required=True, help="panelPath")
args = vars(ap.parse_args())
workingPath = args["ppath"]
print("Panel path is: %s" % workingPath)
imageFiles = os.listdir(workingPath)

exiftoolPath = None
if os.name == 'nt':
    exiftoolPath = 'D:/ExifTool/exiftool.exe'

# Sum of each band's radiance 
sbr_B = 0
sbr_G = 0
sbr_R = 0
sbr_E = 0
sbr_N = 0
# Num of each band's radiance 
nbr_B = 0
nbr_G = 0
nbr_R = 0
nbr_E = 0
nbr_N = 0

for im in imageFiles:
    # Read raw image DN values
    imageName = os.path.join(workingPath,im)
    imageRaw=plt.imread(imageName)
    print("Processing %s" % imageName)
    meta = metadata.Metadata(imageName, exiftoolPath=exiftoolPath)
    bandName = meta.get_item('XMP:BandName')
    
    radianceImage, L, V, R = msutils.raw_image_to_radiance(meta, imageRaw)
    
    panel_coords = panelDetect(imageName, 110, 7000)
    # print(panel_coords)
    # Extract coordinates
    if panel_coords[0][0][0]:
        nw_x = int(panel_coords[0][0][0])
        nw_y = int(panel_coords[0][0][1])
        sw_x = int(panel_coords[1][0][0])
        sw_y = int(panel_coords[1][0][1])
        se_x = int(panel_coords[2][0][0])
        se_y = int(panel_coords[2][0][1])
        ne_x = int(panel_coords[3][0][0])
        ne_y = int(panel_coords[3][0][1])
        x_min = numpy.min([nw_x,sw_x,ne_x,se_x])
        x_max = numpy.max([nw_x,sw_x,ne_x,se_x])
        y_min = numpy.min([nw_y,sw_y,ne_y,se_y])
        y_max = numpy.max([nw_y,sw_y,ne_y,se_y])
        
        panelPolygon = Polygon([(sw_x, sw_y), (nw_x, nw_y), (ne_x, ne_y), (se_x, se_y)])
        numPixel = 0
        sumRadiance = 0
        for x in range(x_min,x_max):
            for y in range(y_min,y_max):
                if panelPolygon.contains(Point(x,y)):
                    numPixel += 1
                    sumRadiance = sumRadiance+radianceImage[y,x]
        
        meanRadiance = sumRadiance/numPixel
        
        if bandName == 'Blue':
            sbr_B = sbr_B + meanRadiance
            nbr_B += 1
        elif bandName == 'Green':
            sbr_G = sbr_G + meanRadiance
            nbr_G += 1
        elif bandName == 'Red':
            sbr_R = sbr_R + meanRadiance
            nbr_R += 1
        elif bandName == 'Red edge':
            sbr_E = sbr_E + meanRadiance
            nbr_E += 1
        else:
            sbr_N = sbr_N + meanRadiance
            nbr_N += 1

if nbr_B != 0:
    meanRadiance_B = sbr_B / nbr_B
else:
    meanRadiance_B = 0
if nbr_G != 0:
    meanRadiance_G = sbr_G / nbr_G
else:
    meanRadiance_G = 0
if nbr_R != 0:
    meanRadiance_R = sbr_R / nbr_R
else:
    meanRadiance_R = 0
if nbr_E != 0:
    meanRadiance_E = sbr_E / nbr_E
else:
    meanRadiance_E = 0
if nbr_N != 0:
    meanRadiance_N = sbr_N / nbr_N
else:
    meanRadiance_N = 0
    
panelCalibration = { 
    "Blue": 0.66, 
    "Green": 0.67, 
    "Red": 0.67, 
    "Red edge": 0.66, 
    "NIR": 0.6 
}

# Select panel region from radiance image
print('Blue Mean Radiance in panel region: {:1.3f} W/m^2/nm/sr'.format(meanRadiance_B))
print('Green Mean Radiance in panel region: {:1.3f} W/m^2/nm/sr'.format(meanRadiance_G))
print('Red Mean Radiance in panel region: {:1.3f} W/m^2/nm/sr'.format(meanRadiance_R))
print('Nir Mean Radiance in panel region: {:1.3f} W/m^2/nm/sr'.format(meanRadiance_N))
print('Red edge Mean Radiance in panel region: {:1.3f} W/m^2/nm/sr'.format(meanRadiance_E))

radianceToReflectance = panelCalibration["Blue"] / meanRadiance_B
print('Blue Radiance to reflectance conversion factor: {:1.5f}'.format(radianceToReflectance))
radianceToReflectance = panelCalibration["Green"] / meanRadiance_G
print('Green Radiance to reflectance conversion factor: {:1.5f}'.format(radianceToReflectance))
radianceToReflectance = panelCalibration["Red"] / meanRadiance_R
print('Red Radiance to reflectance conversion factor: {:1.5f}'.format(radianceToReflectance))
radianceToReflectance = panelCalibration["NIR"] / meanRadiance_N
print('Nir Radiance to reflectance conversion factor: {:1.5f}'.format(radianceToReflectance))
radianceToReflectance = panelCalibration["Red edge"] / meanRadiance_E
print('Red-edge Radiance to reflectance conversion factor: {:1.5f}'.format(radianceToReflectance))

