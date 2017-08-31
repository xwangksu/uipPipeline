'''
Created on Aug 29, 2017

@author: xuwang
'''
import argparse
import exiftool
import math
import numpy
from pyimagesearch.shapedetector import ShapeDetector
import imutils
import cv2
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon

def panelDetect(image,b_th,ct_th):
    image = cv2.imread(image)
    resized = imutils.resize(image, width=640, height=480)
    ratio = image.shape[0] / float(resized.shape[0])
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
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
        return approx
    else:
        return [[0,0],[0,0],[0,0],[0,0]]

# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-i", "--image", required=True, help="image to process")
args = vars(ap.parse_args())
srcImage = args["image"]
print("The source image is: %s" % srcImage)
# Get all EXIF attributes needed
with exiftool.ExifTool() as et:
    exifAttributes = et.get_metadata(srcImage)
for tag in exifAttributes:
    if tag == 'EXIF:BitsPerSample':
        bit = exifAttributes[tag]
        # Norm factor
        normFactor = int(math.pow(2,bit))
        print('Normalized factor: %s' % normFactor)
    if tag == 'EXIF:BlackLevel':
        pblList = exifAttributes[tag].split(' ')
        f_pblList = [float(x) for x in pblList]
        # Black Level Offset
        pbl = numpy.mean(f_pblList)
        print('mean of Black Level Offset: %s' % pbl)
    if tag == 'XMP:RadiometricCalibration':
        akList = exifAttributes[tag]
        print('Radiometric calibration coefficients: %s' % akList)
        # Radiometric calibration coefficients
        ak1 = float(akList[0])
        ak2 = float(akList[1])
        ak3 = float(akList[2])
    if tag == 'EXIF:ExposureTime':
        # Exposure Time
        te = float(exifAttributes[tag])
        print('Exposure Time: %s' % te)
    if tag == 'EXIF:ISOSpeed':
        # Sensor gain
        gain = float(exifAttributes[tag])/100
        print('Sensor gain: %s' % gain)
    if tag == 'XMP:VignettingCenter':
        # Vignetting center
        vc = exifAttributes[tag]
        print('Vignetting center: %s' % vc)
        vcx = float(vc[0])
        vcy = float(vc[1])
    if tag == 'XMP:VignettingPolynomial':
        # Vignetting correction factors
        vcf = exifAttributes[tag]
        print('Vignetting correction factors: %s' % vcf)
        vk0 = float(vcf[0])
        vk1 = float(vcf[1])
        vk2 = float(vcf[2])
        vk3 = float(vcf[3])
        vk4 = float(vcf[4])
        vk5 = float(vcf[5])
# Detect panel area 
panel_coords = panelDetect(srcImage, 110, 7000)
# print(panel_coords[0][0][0])
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

rawImage = cv2.imread(srcImage,cv2.IMREAD_ANYCOLOR | cv2.IMREAD_ANYDEPTH)
panelPolygon = Polygon([(sw_x, sw_y), (nw_x, nw_y), (ne_x, ne_y), (se_x, se_y)])
numPixel = 0
sumRadiance = 0
for x in range(x_min,x_max):
    for y in range(y_min,y_max):
        if panelPolygon.contains(Point(x,y)):
            numPixel += 1
            r = numpy.sqrt((x-vcx)**2+(y-vcy)**2)
            k = 1 + vk0*r + vk1*(r**2) + vk2*(r**3) + vk3*(r**4) + vk4*(r**5) + vk5*(r**6)
            vf = 1/k
            rad = vf*(ak1/gain)*(rawImage[x,y]/normFactor-pbl/normFactor)/(te+ak2*y-ak3*te*y)
            sumRadiance = sumRadiance+rad

avgRadiance = sumRadiance/numPixel
print('Average radiance: %f' % avgRadiance)

blueAlbedo = 0.66
greenAlbedo = 0.67
redAlbedo = 0.67
rededgeAlbedo = 0.66
nirAlbedo = 0.6

blueFactor = blueAlbedo/avgRadiance
print('Blue band reflectance calibration factor: %f' % blueFactor)


# rawImage = cv2.imread(srcImage)
# print(rawImage[442,170])


