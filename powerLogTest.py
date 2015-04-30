import gpib_eth as g
import time
import csv

def csvWrite(fileName,dataToWrite):#{{{
    with open(fileName,'wb') as csvFile:
        writer = csv.writer(csvFile,delimiter=',')
        writer.writerows(dataToWrite)
    csvFile.close()
    print "Wrote powers to file %s"%fileName
    return None
#}}}

conn = g.gigatronics_powermeter(ip='149.236.99.25')
time.sleep(1.)

startTime = time.time()
timeList = []
powerList = []
for i in range(20):
    power = float(conn.read_power())
    timelapsed = time.time()-startTime
    powerList.append(power)
    timeList.append(timelapsed)
    time.sleep(0.5)
    print "I just recorded power %0.2f"%power

conn.close()

# dump as txt file
fileName = 'test.csv'
dataToWrite = [('time (s)','power (dBm)')] + zip(timeList,powerList)
csvWrite(fileName,dataToWrite)
