'''
Created on Nov 8, 2017

@author: xuwang
'''
import cv2
import matplotlib.pyplot as plt
import numpy
import os
import micasense.plotutils as plotutils
import micasense.metadata as metadata
import micasense.utils as msutils
from pyimagesearch.shapedetector import ShapeDetector
import imutils
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon

def panelDetect(image,b_th,ct_th):
    image = cv2.imread(image)
    resized = imutils.resize(image, width=640, height=480)
    ratio = image.shape[0] / float(resized.shape[0])
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blurred, b_th, 255, cv2.THRESH_BINARY)[1]
    cv2.imshow("Image", thresh)
    cv2.waitKey(0)
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
                cv2.imshow("Image", image)
                cv2.waitKey(0)
    if sq == 1:
        print(approx)
        return approx
    else:
        return [[[0,0]],[[0,0]],[[0,0]],[[0,0]]]

imagePath = 'F:/Xu/17ASH_Macia_0831/OUT'
imageName = os.path.join(imagePath,'IMG_0002_2.tif')

# Read raw image DN values
imageRaw=plt.imread(imageName)

exiftoolPath = None
if os.name == 'nt':
    exiftoolPath = 'D:/ExifTool/exiftool.exe'
    
meta = metadata.Metadata(imageName, exiftoolPath=exiftoolPath)
bandName = meta.get_item('XMP:BandName')

radianceImage, L, V, R = msutils.raw_image_to_radiance(meta, imageRaw)
# plotutils.plotwithcolorbar(V,'Vignette Factor')
# plotutils.plotwithcolorbar(R,'Row Gradient Factor')
# plotutils.plotwithcolorbar(V*R,'Combined Corrections')
# plotutils.plotwithcolorbar(L,'Vignette and row gradient corrected raw values')
# plotutils.plotwithcolorbar(radianceImage,'All factors applied and scaled to radiance')

panel_coords = panelDetect(imageName, 110, 7000)
# print(panel_coords)
# Extract coordinates
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

panelCalibration = { 
    "Blue": 0.66, 
    "Green": 0.67, 
    "Red": 0.67, 
    "Red edge": 0.66, 
    "NIR": 0.6 
}

# Select panel region from radiance image
print('Mean Radiance in panel region: {:1.3f} W/m^2/nm/sr'.format(meanRadiance))
panelReflectance = panelCalibration[bandName]
radianceToReflectance = panelReflectance / meanRadiance
print('Radiance to reflectance conversion factor: {:1.5f}'.format(radianceToReflectance))
reflectanceImage = radianceImage * radianceToReflectance
plotutils.plotwithcolorbar(reflectanceImage, 'Converted Reflectane Image')

# ulx = int(numpy.min([nw_x,sw_x,ne_x,se_x])*1.2)
# lrx = int(numpy.max([nw_x,sw_x,ne_x,se_x])*0.8)
# uly = int(numpy.min([nw_y,sw_y,ne_y,se_y])*1.2)
# lry = int(numpy.max([nw_y,sw_y,ne_y,se_y])*0.8)
# markedImg = reflectanceImage.copy()
# cv2.rectangle(markedImg,(ulx,uly),(lrx,lry),(0,255,0),3)
# panelRegionRefl = reflectanceImage[uly:lry, ulx:lrx]
# panelRegionReflBlur = cv2.GaussianBlur(panelRegionRefl,(55,55),5)
# plotutils.plotwithcolorbar(panelRegionReflBlur, 'Smoothed panel region in reflectance image')
# print('Min Reflectance in panel region: {:1.2f}'.format(panelRegionRefl.min()))
# print('Max Reflectance in panel region: {:1.2f}'.format(panelRegionRefl.max()))
# print('Mean Reflectance in panel region: {:1.2f}'.format(panelRegionRefl.mean()))
# print('Standard deviation in region: {:1.4f}'.format(panelRegionRefl.std()))

# undistortedReflectance = msutils.correct_lens_distortion(meta, reflectanceImage)
# plotutils.plotwithcolorbar(undistortedReflectance, 'Undistorted reflectance image')

