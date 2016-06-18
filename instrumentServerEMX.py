import threading
import time
import subprocess
import gpib_eth as g
import socket
import os
import csv

# If by chance you switch back to the eip meter un-comment the line below.
# powerConn = g.eip_powermeter(ip='149.236.99.25')
powerConn = g.gigatronics_powermeter(ip='149.236.99.25')
powerLogThread = False
print "Initialized power meter connection"

### Various Functions
def setAtten(attenuation,*args):#{{{
    print "Setting attenuation to ", attenuation
    subprocess.call(['/home/nmrsu/jf_setmwpower','%0.2f'%attenuation])
#}}}

def csvWrite(fileName,dataToWrite):#{{{
    with open(fileName,'wb') as csvFile:
        writer = csv.writer(csvFile,delimiter=',')
        writer.writerows(dataToWrite)
    csvFile.close()
    print "Wrote powers to file %s"%fileName
    return None
#}}}

def ampOnOff(state,*args):#{{{
    subprocess.call(['/opt/topspin/exp/stan/nmr/emxDnp/ampOnOff',state])
#}}}

def powerLog(fileName,powerConn,stopEvent,*args):#{{{
    """
    Log powers with the eip power meter 
    """
    fileName += '.csv'
    print fileName
    timeout = 100
    powerlist = []
    timelist = []
    absoluteTimeList = []
    startTime = time.time()
    powerConn.read_power()
    count = 0 
    timeoutcount = 0 
    while(not stopEvent.is_set()): # this should let me stop the thread once we're golden
        try:
            thispower = powerConn.read_power()
            powerlist.append(float(thispower))
        except:
            print "Got some garbage from the GPIB controller I assume you're talking to it while I'm trying to talk so Ill wait"
            pass
        print 'I just recorded: ',thispower
        timelist.append((time.time()-startTime)) # this will hopefully give us a more human readable time.
        absoluteTimeList.append(time.asctime())
        if thispower <= -99.9:
            timeoutcount += 1
            if count > timeout:
                if timeoutcount >= 40: # the power has been off for atleast 20 seconds lets stop recording the powers
                    stopEvent.set()
        time.sleep(.5)
        count += 1 
        # An autosave thing to save powers list every 50 points 
        if int(count/50.) - (count/50.) == 0: # if we're at a multiple of 50 counts save the list
            dataToWrite = [('time (s)','power (dBm)','absolute time')] + zip(timelist,powerlist,absoluteTimeList)
            csvWrite(fileName,dataToWrite)
            print "I just saved the power file!"

    # once we break the while loop save the data
    print "I'm saving the recorded powers and times"
    print "the length of the power and time list is: ", len(powerlist),len(timelist)
    dataToWrite = [('time (s)','power (dBm)')] + zip(timelist,powerlist)
    csvWrite(fileName,dataToWrite)
#}}}

#{{{ # Actual server part
host = '0.0.0.0'
port = 7002
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((host,port)) 
s.listen(10)
try:
    while True:
        print 'Ready for command. \n\n\nListening on %s port %d\n\n'%(host,port)
        s.settimeout(1e6)
        conn, addr = s.accept()
        print 'created connection at ' , addr
        incoming = ''
        command_buffer = []
        while 1:
            conn.settimeout(1e6) # set the timeout large enough so we don't need to worry about breaking the script
            try: # if this faults out lets remake the connection with the host machine
                temp = conn.recv(1024) 
            except:
                conn.close()
                conn, addr = s.accept()
                conn.settimeout(1e6) # set the timeout large enough so we don't need to worry about breaking the script
                temp = conn.recv(1024) # if nothing received the script hangs

            if not temp: break
            incoming = incoming + temp
            if incoming[-1] != '\n':
                if incoming.find('\n'):
                    temp = incoming.split('\n')
                    command_buffer.extend(temp[:-1])
                    incoming = temp[-1]
                else:
                    break
            else:
                command_buffer.extend(incoming.split('\n'))
                incoming = ''
            print "about to try to run the command buffer:",repr(command_buffer)
            for mycommand in command_buffer:
                if len(mycommand) == 0:
                    pass
                else:
                    mycommand = mycommand.split(' ')
                    if mycommand[0] == 'SETATTEN':
                        try:
                            attenuation = float(mycommand[1])
                            attenThread = threading.Thread(target = setAtten,args = (attenuation,1))
                            attenThread.start()
                        except Exception as errtxt:
                            print errtxt
                    elif mycommand[0] == 'LOGPOWER':
                        try:
                            powerThreadStop = threading.Event()
                            powerLogThread = threading.Thread(target = powerLog,args = (mycommand[1],powerConn,powerThreadStop,1))
                            powerLogThread.start()
                        except Exception as errtxt:
                            print errtxt
                    elif mycommand[0] == 'POWERSTOP':
                        powerThreadStop.set()
                    elif mycommand[0] == 'AMPON':
                        try:
                            ampThread = threading.Thread(target = ampOnOff,args = ('0xFF',1))
                            ampThread.start()
                        except Exception as errtxt:
                            print errtxt
                    elif mycommand[0] == 'AMPOFF':
                        try:
                            ampThread = threading.Thread(target = ampOnOff,args = ('0x00',1))
                            ampThread.start()
                        except Exception as errtxt:
                            print errtxt
except KeyboardInterrupt:
    print "closing gracefully...\n"
    if powerLogThread:
        if powerLogThread.isAlive():
            print "Still logging powers, shutting down... \n"
            powerThreadStop.set()
            time.sleep(1.)
            print "Power log stopped.\n"
    del powerConn
    print "closed connection to power meter.\n"
    s.close()
    print "Closed socket connection.\n"
    print "\nGoodbye Dave\n\n"
#}}}
            
