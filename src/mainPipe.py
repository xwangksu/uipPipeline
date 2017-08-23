'''
Created on Aug 19, 2017

@author: xuwang
'''
"""
Demonstrates how to use the blocking scheduler to schedule a job that executes on 3 second
intervals.
"""

from datetime import datetime
import os
import re
import shutil
import pymysql
import csv


from apscheduler.schedulers.blocking import BlockingScheduler

preProcessedPath = 'F:\\Xu\\uav_preprocessed'
processingPath = 'F:\\Xu\\uav_processing'
manifest = 'manifest.txt'

def getQueueStatus():
# Read the processing queue file
    queueFile = open(processingPath+'\\queue.txt',"r")
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
            queueFile = open(processingPath+'\\queue.txt',"w")
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
            manifestFile = open(preProcessedPath+'\\'+flightFolder[0]+'\\manifest.txt',"r") # Check the availability of manifest.txt
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
    queueFile = open(processingPath+'\\queue.txt',"w")
    queueFile.write(newFolder[0]+",processing")
    queueFile.truncate()
    queueFile.close()
    print("A new job - %s has been added to the queue." % newFolder[0])
    return newFolder[0]

def getGCPListFromDB(flight_id):
    # Connect to the database
    conn = pymysql.connect(host='beocat.cis.ksu.edu', port=6306,
                       user='xuwang', passwd = 'xuwang',
                       db='wheatgenetics')
    gcpListFile = open(processingPath+'\\gcpList.txt','w') 
    try:
        writer = csv.writer(gcpListFile, delimiter=',', lineterminator='\n')
        writer.writerow(('Index','Longitude','Latitude','Altitude'))
        with conn.cursor() as cursor:
            querySQLString = "SELECT uas_run_test.experiment_id FROM uas_run_test WHERE uas_run_test.flight_filename = %s"
            cursor.execute(querySQLString, (flight_id))
            exp_id = cursor.fetchone()
            querySQLString = "SELECT gcp.index,gcp.longitude,gcp.latitude,gcp.altitude FROM gcp WHERE gcp.experiment = %s"
            cursor.execute(querySQLString, (exp_id))
            for row in cursor:
                writer.writerow(row)
                print(row)
        print("GCP list is updated.")
    finally:
        cursor.close()
        conn.close()
        
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
                getGCPListFromDB(flightFolder)
                # Start photogrammetry processing
            
            
if __name__ == '__main__':
    scheduler = BlockingScheduler()
    scheduler.add_job(pipeline, 'interval', seconds=60)
    print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
    