'''
Created on Aug 30, 2017

@author: xuwang
'''
from pyimagesearch.shapedetector import ShapeDetector
import argparse
import imutils
import cv2

# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-b", "--bthresh", required=True,
    help="threshold for binary image")
ap.add_argument("-ct", "--ctthresh", required=True,
    help="threshold for contour")
ap.add_argument("-i", "--image", required=True,
    help="path to the input image")
args = vars(ap.parse_args())
# load the image and resize it to a smaller factor so that
# the shapes can be approximated better
b_th = float(args["bthresh"])
ct_th = float(args["ctthresh"])
image = cv2.imread(args["image"])
resized = imutils.resize(image, width=640, height=480)
ratio = image.shape[0] / float(resized.shape[0])
# convert the resized image to grayscale, blur it slightly,
# and threshold it
gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
blurred = cv2.GaussianBlur(gray, (3, 3), 0)
thresh = cv2.threshold(blurred, b_th, 255, cv2.THRESH_BINARY)[1]
cv2.imshow("Image", thresh)
cv2.waitKey(0)
# find contours in the thresholded image and initialize the
# shape detector
cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
    cv2.CHAIN_APPROX_SIMPLE)
cnts = cnts[0] if imutils.is_cv2() else cnts[1]
sd = ShapeDetector()
# loop over the contours
for c in cnts:
    # compute the center of the contour, then detect the name of the
    # shape using only the contour
    shape = "unidentified"
    M = cv2.moments(c)
    if M["m00"] != 0:
        cX = int(round((M["m10"] / M["m00"]))) # * ratio
        cY = int(round((M["m01"] / M["m00"]))) # * ratio
#         cX = int((M["m10"] / M["m00"])* ratio) # * ratio
#         cY = int((M["m01"] / M["m00"])* ratio) # * ratio
        # print("cX: %d, cY: %d" % (cX,cY))
        shape = sd.detect(c)
    # multiply the contour (x, y)-coordinates by the resize ratio,
    # then draw the contours and the name of the shape on the image
    if shape == "square":
        print(shape)
        print("Estimated contour size: %f" % (cv2.contourArea(c)))
        if cv2.contourArea(c)>ct_th:
            c = c.astype("float")
            c *= ratio
            c = c.astype("int")
            # peri = cv2.arcLength(c, True)
            # approx = cv2.approxPolyDP(c, 0.04 * peri, True)
#             print("approx:")
#             print(approx)
    #         print("Estimated contour size:")
    #         print(cv2.contourArea(c))
    #         print(12*2.54/100*4*0.9/cv2.contourArea(c))
            cv2.drawContours(image, [c], -1, (0, 255, 0), 1)
            cv2.putText(image, shape, (cX, cY), cv2.FONT_HERSHEY_SIMPLEX,
                        0.5, (255, 255, 255), 1)
        # show the output image
            cv2.imshow("Image", image)
            cv2.waitKey(0)