# -*- coding: utf-8 -*-

### Sound Detect SDK ##########################################################
__author__  = "Yoshi Kajiki <y-kajiki@ah.jp.nec.com>"
__version__ = "5.15"
__date__    = "Sep 29, 2018"

### global valiables
global_useEdgeFlag = True
global_localEdgeFlag = False
global_soundLogFlag = True
global_soundLogDir = ''
global_useRemoteControlFlag = False
global_apiEndpoint = ''
global_edgeEndpoint = ''
global_socketPort = ''
global_deviceId = ''
global_edgeId = ''
global_fs = 0
global_resetTime = 0
global_powerAnnotationFlag = False
global_spectrumAnnotationFlag = False
global_analyzeFlag = True
global_recordFlag = False
global_exitFlag = False
global_senseHatFlag = False
global_proxies = ''

### import modules
import os
import sys
import io
import glob
import math
import random
import string
import time
import copy
import threading
import json
import queue
import datetime
import csv
import socket
import struct

import numpy as np
from scipy import arange, ceil, dot, exp, hamming, log2, zeros, signal, ndimage, complex128, float64
from scipy import pi as mpi
from scipy.fftpack import fft
from scipy.sparse import lil_matrix, csr_matrix
import requests
import soundfile as sf
import bson

### define constants
two_pi_j = 2 * mpi * 1j

### local functions ###########################################################
def get_num_freq(fmin, fmax, fratio):
    return int(round(log2(float(fmax) / fmin) / fratio)) + 1

def get_freqs(fmin, nfreq, fratio):
    return fmin * (2 ** (arange(nfreq) * fratio))

def create_edge():
    global global_apiEndpoint
    global global_edgeEndpoint
    global global_deviceId
    global global_edgeId
    global global_proxies

    print("Get Edge ID")
    request_url = global_apiEndpoint + '/v1/' + global_deviceId + "/edge"
    try:
        r = requests.post(request_url, timeout=10, proxies=global_proxies)
    except:
        print('Error! Fail to connect to management server.')
        sys.exit()
    if (r.status_code > 299):
        print(r.text)
        print('Error! Fail to request management server. http status = '+str(r.status_code))
        print('It may caused by incorrect Device ID.')
        sys.exit()

    resp = r.json()
    if "edge_id" in resp:
        global_edgeId = r.json()["edge_id"]
    else:
        print('Error! Fail to get edge_id.')
        sys.exit()

    edgeinfo = get_edge_info()
    if edgeinfo["ready"] == False and edgeinfo["error"] == False:
        print("\nNow creating your Cloud Edge Server. Please wait for approx 60 sec ..")

        edgeinfo = get_edge_info()
        sys.stderr.write("Progress %3s%%" % (edgeinfo["progress"]))
        pre_progress = int(edgeinfo["progress"])
        progress = int(edgeinfo["progress"])
        while ((edgeinfo["ready"] == False) and (edgeinfo["error"] == False)):
            time.sleep(3)
            edgeinfo = get_edge_info()
            new_progress = int(edgeinfo["progress"])
            if(pre_progress == new_progress):
                progress += 1
            else:
                progress = int(new_progress)
                pre_progress = progress

            sys.stderr.write("\rProgress %3s%%" % (progress))
        sys.stderr.write("\n")

        if(edgeinfo["error"]):
            print('Fail to create your Cloud Edge.')
            sys.exit()
        else:
            print('Created.\n')

    edgeIpAddr = edgeinfo["ip_address"]
    global_edgeEndpoint = 'http://' + edgeIpAddr

    return

def get_edge_info():
    global global_apiEndpoint
    global global_deviceId
    global global_edgeId
    global global_proxies

    if(global_edgeId == ""):
        print ("Error! Edge ID Lost.")
        sys.exit()

    request_url = global_apiEndpoint + '/v1/' + global_deviceId + "/edge/" + global_edgeId
    try:
        r = requests.get(request_url, timeout=10, proxies=global_proxies)
    except:
        print ('Error! Fail to connect to the management server.')
        sys.exit()
    if (r.status_code > 299):
        print('Error! Fail to create a cloud edge server. http status = '+str(r.status_code))
        sys.exit()

    data = r.json()
    if(data["error"]):
        print('Error! Fail to start edge server.')
        sys.exit()

    return data

def resetEdge():
    global global_deviceId
    global global_useEdgeFlag
    global global_localEdgeFlag
    global global_edgeEndpoint
    global global_proxies
    global global_resetTime
    global global_eventTriggerFlag
    global global_useHistoryFlag
    global global_apiEndpoint
    global global_logEndpoint
    global global_fluentHost
    global global_fluentPort

    if global_useEdgeFlag:
        print('Reset Edge')
        url = global_edgeEndpoint + '/v1/reset'
        requestParameter = {
            'apiEndpoint' : global_apiEndpoint,
            'device_id' : global_deviceId,
            'logEndpoint' : global_logEndpoint,
            'fluentHost' : global_fluentHost,
            'fluentPort' : global_fluentPort,
        }
        if global_localEdgeFlag:
            requestParameter['proxies'] = global_proxies

        global_resetTime = time.time()
        global_useEdgeFlag = False
        try:
            res = requests.put(url, json=requestParameter, timeout=15, proxies=global_proxies)
        except:
            print('Error! Reset Edge fail')

        # Set Trigger Mode
        if global_eventTriggerFlag:
            url = global_edgeEndpoint + '/v1/trigger/on'
            print('Set Trigger Mode: ON')
        else:
            url = global_edgeEndpoint + '/v1/trigger/off'
            print('Set Trigger Mode: OFF')
        try:
            res = requests.put(url, timeout=10, proxies=global_proxies)
            if res.status_code != 200:
                print('Error occured at Set Trigger Mode.')
                print(res.text)
        except:
            print('Error! Can not connect to your Cloud Edge: %s' % url)

        # Set History Mode
        if global_useHistoryFlag:
            url = global_edgeEndpoint + '/v1/history/on'
            print('Set History Mode: ON')
        else:
            url = global_edgeEndpoint + '/v1/history/off'
            print('Set History Mode: OFF')
        try:
            res = requests.put(url, timeout=10, proxies=global_proxies)
            if res.status_code != 200:
                print('Error occured at Set History Mode.')
                print(res.text)
        except:
            print('Error! Can not connect to your Cloud Edge: %s' % url)

        global_useEdgeFlag = True

def watchDogClient():
    global global_edgeEndpoint

    reset_interval_nor = 60*10
    reset_interval_err = 60*1
    reset_interval = reset_interval_nor

    while True:
        time.sleep(reset_interval)

        request_url = global_edgeEndpoint + '/v1/watch_dog'
        try:
            r = requests.get(request_url, timeout=10, proxies=global_proxies)
            print('----------------------- Reset watchDog -----------------------')
            reset_interval = reset_interval_nor
        except:
            print('Error! Fail to reset watchDog.')
            reset_interval = reset_interval_err

def shutdown():
    global global_senseHatFlag
    global global_sense
    global global_analyzeFlag
    global global_recordFlag

    global_analyzeFlag = False
    global_recordFlag = False

    if global_senseHatFlag:
        global_senseHatFlag = False
        global_sense.clear(255, 0, 0)
        time.sleep(0.3)
        global_sense.clear()

    print("sudo shutdown -h now")
    os.system("sudo shutdown -h now")

def reboot():
    global global_senseHatFlag
    global global_sense
    global global_analyzeFlag
    global global_recordFlag

    global_analyzeFlag = False
    global_recordFlag = False

    if global_senseHatFlag:
        global_senseHatFlag = False
        global_sense.clear(255, 0, 0)
        time.sleep(0.3)
        global_sense.clear()

    print("sudo shutdown -r now")
    os.system("sudo shutdown -r now")

### Sound Detecter Class ######################################################
class soundDetector():

    ### Constructor ###
    def __init__(self, deviceId, fs, chunkSize, useEdgeFlag=True, localEdgeFlag=False, eventTriggerFlag=True, soundLogFlag=True, soundLogDir='soundLog', useHistoryFlag=True, powerAnnotationFile='', spectrumAnnotationFile='', msgLevel=3, version=3, mngServer='www6.arche.blue', remoteControlFlag=False, senseHatFlag=False, logHost='log1.arche.blue', fluentHost = 'www6.arche.blue', fluentPort=24224, proxies=''):
        """
        Constructor
        @return void
        """

        global global_mngServer
        global global_useEdgeFlag
        global global_localEdgeFlag
        global global_soundLogFlag
        global global_soundLogDir
        global global_proxies
        global global_apiEndpoint
        global global_edgeEndpoint
        global global_socketPort
        global global_deviceId
        global global_edgeId
        global global_fs
        global global_eventTriggerFlag
        global global_useHistoryFlag
        global global_resetTime
        global global_powerAnnotationFlag
        global global_spectrumAnnotationFlag
        global global_msgLevel
        global global_clientVersion
        global global_queue
        global global_useRemoteControlFlag
        global global_logEndpoint
        global global_fluentHost
        global global_fluentPort
        global global_senseHatFlag
        global global_sense

        # set global valiables
        global_deviceId = deviceId
        global_fs = fs
        global_eventTriggerFlag = eventTriggerFlag
        global_useHistoryFlag = useHistoryFlag
        global_useEdgeFlag = useEdgeFlag
        global_localEdgeFlag = localEdgeFlag
        global_soundLogFlag = soundLogFlag
        global_soundLogDir = soundLogDir
        global_apiEndpoint = 'https://' + mngServer + '/api'
        global_mngServer = mngServer
        global_socketPort = 50002
        global_proxies = proxies
        global_msgLevel = msgLevel
        global_clientVersion = version
        global_queue = queue.Queue()
        global_useRemoteControlFlag = remoteControlFlag
        global_logEndpoint = 'https://' + logHost + '/api'
        global_fluentHost = fluentHost
        global_fluentPort = fluentPort
        global_senseHatFlag = senseHatFlag

        # initialize Senser Hat
        if global_senseHatFlag:
            from sense_hat import SenseHat
            global_sense = SenseHat()
            global_sense.clear(0, 0, 255)
            for event in global_sense.stick.get_events():
                if event.action == "pressed":
                    shutdown()

        # set class constants
        if chunkSize < fs:
            print('Error! chunkSize must be larger than fs.')
            sys.exit()
        self.chunkSize = chunkSize

        # remove old tempFile
        files = glob.glob('*.npy')
        for file in files:
            try:
                os.remove(file)
            except:
                print('Warrning: os.remove(%s) failed.' % file)

        # init cloud edge
        if global_useEdgeFlag:
            if localEdgeFlag:
                global_edgeEndpoint = 'http://127.0.0.1:5001'
                global_edgeId = 'edge-00000000000000'

                while True:
                    # Edge health check
                    print('Check Edge')
                    url = global_edgeEndpoint + '/v1/watch_dog'
                    try:
                        res = requests.get(url, timeout=1, proxies=global_proxies)
                        if res.status_code != 200:
                            print('Error occured at Cloud Edge Health Check.')
                            print(res.text)
                            sys.exit()
                        print('  It works!')
                        break
                    except:
                        print('  No responce. Wait for 2 sec.')
                        time.sleep(2)

            else:
                # Create edge
                create_edge()

                # Edge health check
                print('Check Edge')
                url = global_edgeEndpoint + '/v1/watch_dog'
                try:
                    res = requests.get(url, timeout=10, proxies=global_proxies)
                    if res.status_code != 200:
                        print('Error occured at Cloud Edge Health Check.')
                        print(res.text)
                        sys.exit()
                except:
                    print('Error! Can not connect to your Cloud Edge: %s' % url)
                    sys.exit()

            th_watchDogClient = threading.Thread(target=watchDogClient, name='watchDogClient')
            th_watchDogClient.setDaemon(True)
            th_watchDogClient.start()

            # Reset Edge
            resetEdge()

        # Create signal buffer
        self.sigMargin = int(round(0.1 * fs))
        sigBuffSize = chunkSize + 3 * fs
        self.sigBuff = np.zeros(sigBuffSize)

        # Initialize CQT
        fmin = 55                           # minimum frequency
        fmax = 14080                        # maximum frequency
        f_bins = 12                         # freq bins per 1 octave
        q_fact = 20.                        # quality factor
        spThresh = 0.0054                   # threshold of sparse kernel
        nhop = int(self.sigMargin / int(self.sigMargin / (0.02 * fs)))    # step of frames of spectrogrum
        self.setKernel(fs, fmin, fmax, f_bins, q_fact, spThresh, nhop)

        # Create spectrogram buffer
        self.chunkSpecSize = int(chunkSize / nhop)
        self.spectMargin = int(self.sigMargin / nhop)
        self.spectBuffSize = self.chunkSpecSize + int(round(3.0 * fs / nhop))
        self.spectBuff = np.zeros((self.spectBuffSize, self.nfreq))
        self.accommoSpectBuff = np.zeros((self.spectBuffSize, self.nfreq))
        self.powerBuff = np.zeros((self.spectBuffSize))

        # Set accommodation variables
        self.accommoLen = round(0.2 / (nhop / fs))
        self.accommoFact = (self.accommoLen - 1) / self.accommoLen
        self.accommoBuff = np.zeros(self.nfreq)

        # Set power event evaluation parameters
        self.agcFlag = True
        self.powerMaxThRetio = 0.1
        self.powerThDecayInitTime = (60 * 15) / (chunkSize / fs)
        self.powerThDecayInit = 0.5 ** ((chunkSize / fs) / 60.)
        self.powerThDecay = 0.5 ** ((chunkSize / fs) / (60. * 60. * 24.))
        self.powerCount = 0.
        powerCountTime = 60. * 5.
        self.powerCountDecay = 0.5 ** ((chunkSize / fs) / powerCountTime)
        self.powerCountAdoptInterval = round(powerCountTime / (chunkSize / fs))
        self.powerCountMax = 20.
        self.powerCountAdoptRate = 1.5
        if os.path.exists('powerTh.txt'):
            f = open('powerTh.txt', 'r')
            self.powerTh = float(f.readline())
            f.close
            self.cCount = int(self.powerCountAdoptInterval + 1)
        else:
            self.powerTh = 0
            self.cCount = 0
        self.eventStFlag = False
        self.eventEdFlag = False
        self.eventFixFlag = False
        self.eventSt = 0
        self.eventEt = 0
        self.eventStPower = 0
        self.eventPeakPower = 0
        self.eventPeakT = 0
        self.eventPeakPower = 0
        self.eventPeakT = 0
        self.eventHalfPower = 0
        self.eventHalfT = 0
        self.eventMinLen = round(0.01 / (nhop / fs))
        self.eventMaxLen = round(3.0 / (nhop / fs))
        self.eventDisappear = 0
        self.eventDisappearMax = round(0.3 / (nhop / fs))

        # Set cochlear band
        self.dfreq = round(f_bins / 8)
        self.nBand = 3
        self.nTrack = 3
        cross = 5
        self.band = [[0,int(self.nfreq/3+cross)],[int(self.nfreq/3-cross),int(self.nfreq/3*2+cross)],[int(self.nfreq/3*2-cross),self.nfreq-self.dfreq]]

        # Set sharp spectrum event evaluation parameters
        self.spectrumMaxThRetio = 0.1
        self.spectrumThDecayInitTime = (60 * 15) / (chunkSize / fs)
        self.spectrumThDecayInit = 0.5 ** ((chunkSize / fs) / 60.)
        self.spectrumThDecay = 0.5 ** ((chunkSize / fs) / (60. * 60. * 24.))
        self.spectrumCount = 0.
        spectrumCountTime = 60. * 5.
        self.spectrumCountDecay = 0.5 ** ((chunkSize / fs) / spectrumCountTime)
        self.spectrumCountAdoptInterval = round(spectrumCountTime / (chunkSize / fs))
        self.spectrumCountMax = 20.
        self.spectrumCountAdoptRate = 1.5
        if os.path.exists('spectrumTh.txt'):
            f = open('spectrumTh.txt', 'r')
            self.spectrumTh = float(f.readline())
            f.close
        else:
            self.spectrumTh = 0

        # Set spectrum peak tracker
        self.trackL = 4.0
        self.trackW = 3
        self.peakTrack = np.array([[-1.,0.,0.,0.,0.,0.,0.] for ii in range(self.nTrack * self.nBand)])
        # 0: f, 1: power, 2: freq differance, 3: power differance, 4: alive time, 5: lost time
        self.peakLostMax = 3
        self.peakDurTh = round(0.3 / (nhop / fs))
        self.peakDurMax = round(2.0 / (nhop / fs))
        self.peakErr = round(0.3 / (nhop / fs))

        # Make Sound Log Dir
        if global_soundLogFlag:
            if not os.path.exists(global_soundLogDir):
                os.makedirs(global_soundLogDir)

        # Set annotation mode
        if powerAnnotationFile != '':
            global_powerAnnotationFlag = True
            self.powerAnnotationFd = open(powerAnnotationFile, mode='w')

        if spectrumAnnotationFile != '':
            global_spectrumAnnotationFlag = True
            self.spectrumAnnotationFd = open(spectrumAnnotationFile, mode='w')

        # Initialize record buffer
        self.wavRecord = []
        self.recordMaxLen = 180

        # Start message consumer thread
        if global_useRemoteControlFlag:
            self.initSocket()
            self.recvTime = time.time()
            th_socketWatchDog = threading.Thread(target=self.socketWatchDog, name='socketWatchDog')
            th_socketWatchDog.setDaemon(True)
            th_socketWatchDog.start()

        if global_msgLevel > 2:
            print('Initialized SDK')

        # clear Senser Hat LED
        if global_senseHatFlag:
            global_sense.clear()

        return

    ### Analyze Event with Cloud Edge ###
    def analyzeEvent(self, Sx, Vx, stUxTime, feature, queue):
        global global_edgeEndpoint
        global global_deviceId
        global global_edgeId
        global global_fs
        global global_resetTime
        global global_proxies
        global global_soundLogFlag
        global global_msgLevel
        global global_clientVersion
        global global_senseHatFlag
        global global_sense

        st_time = time.time()

        # post the sound event to the edge server
        detectFlag = False
        if global_useEdgeFlag:
            memfile = io.BytesIO()
            np.save(memfile, Vx)
            memfile.seek(0)
            Vx_serialized = json.dumps(memfile.read().decode('latin-1'))
            requestParameter = {
                'samplingFrequency' : global_fs,
                'startTime' : stUxTime,
                'feature' : feature,
                'Vx' : Vx_serialized
            }
            url = global_edgeEndpoint + '/v1/query2/' + global_deviceId + '/edge/' + global_edgeId
            postFlag = False
            try:
                res = requests.post(url, json=requestParameter, timeout=30, proxies=global_proxies)
                postFlag = True
            except:
                print('Warning! Fail to post the event to your cloud edge.')
                if time.time() - global_resetTime > 300:
                    resetEdge()
                sys.exit()

            if postFlag:
                if res.status_code != 200:
                    print(res.text)
                    print('Error! Fail to analyze the event on your cloud edge.')
                    if time.time() - global_resetTime > 60:
                        resetEdge()
                    sys.exit()

            if global_msgLevel > 3:
                print('XXXXXXXXX Cloud Edge Analyze %.2f sec' % (time.time()-st_time))

            detectFlag = False
            loc = time.strftime("%H:%M:%S", time.localtime(stUxTime))
            if postFlag:
                try:
                    res_json = res.json()
                    queue.put(res_json)
                    detectFlag = res_json['detectFlag']
                    if detectFlag:
                        eventName = res.json()['eventName']
                        eventScore = res.json()['eventScore']
                        if global_msgLevel > 2:
                            print('                                                    %s Detect %s, score = %f' % (loc,eventName,eventScore))
                        if global_senseHatFlag and global_analyzeFlag:
                            global_sense.show_letter(eventName[0])
                    else:
                        if global_msgLevel > 2:
                            print('                                                    %s Not Detect' % loc)
                        if global_senseHatFlag and global_analyzeFlag:
                            global_sense.set_pixel(3, 7, [0, 0, 255])
                            global_sense.set_pixel(4, 7, [0, 0, 255])
                    if 'powerTh' in res_json:
                        self.powerTh = res_json['powerTh']
                    if 'spectrumTh' in res_json:
                        self.spectrumTh = res_json['spectrumTh']
                    if 'agcFlag' in res_json:
                        self.agcFlag = res_json['agcFlag']
                except:
                    print('Warrning: query failed. (%s)' % res.text)
                    sys.exit()

        # save the sound event
        if global_soundLogFlag:
            category = feature["category"]

            if stUxTime > 60*60*24*365:
                dt = datetime.datetime.fromtimestamp(stUxTime)
                dt_ymd = dt.strftime('%Y-%m-%d')
                dt_hms = dt.strftime('%H-%M-%S.%f')
                outDir = global_soundLogDir + '/' + dt_ymd + '/' + category
                if not os.path.exists(outDir):
                    os.makedirs(outDir)
                outFilePrefix = outDir + '/' + dt_hms + '_'
            else:
                timeStr = str(round(stUxTime, 1))
                outDir = global_soundLogDir + '/' + category
                if not os.path.exists(outDir):
                    os.makedirs(outDir)
                outFilePrefix = outDir + '/' + timeStr + '_'

            if detectFlag:
                outFileSufix = '_' + eventName
            else:
                outFileSufix = ''

            if category == "power":
                outFile = outFilePrefix + 'P%.1f-f%.1fHz' % (feature["freqPower"],feature["frequency"]) + outFileSufix + '.wav'
            elif category == "spectrum":
                outFile = outFilePrefix + 'f%.1fHz-P%.1f' % (feature["frequency"],feature["freqPower"]) + outFileSufix + '.wav'
            sf.write(outFile, Sx, global_fs)

        return

    def initSocket(self):
        global global_mngServer
        global global_socketPort

        try:
            self.sock = socket.socket()
            self.sock.connect((global_mngServer,global_socketPort))
            tuple = {
                 'key': global_deviceId
            }
            raw = bson.dumps(tuple)
            self.sock.settimeout(2.0)
            self.sock.send(raw)
            self.sock.settimeout(None)
            th_messageConsumer = threading.Thread(target=self.messageConsumer, name='messageConsumer')
            th_messageConsumer.setDaemon(True)
            th_messageConsumer.start()
            print('Remote Control: ON')
        except:
            print('xxxx Warning! Fail to initSocket()')

    def messageConsumer(self):
        global global_deviceId
        global global_msgLevel

        while True:
            try:
                raw = self.sock.recv(4096)
                self.recvTime = time.time()
            except:
                print('xxxx Warning! Connection failed in messageConsumer')
                return
            if raw != '':
                tuple = bson.loads(raw)
                if 'control' in tuple:
                    if tuple['control'] == 'echo':
                        retTuple = {'responce' : 'works'}
                    else:
                        retTuple = {'responce' : 'unknown control'}
                else:
                    if global_msgLevel > 3:
                        print('xxxx command = ', tuple)
                    retTuple = self.remoteCommand(tuple)
                    if global_msgLevel > 3:
                        print('xxxx response = ', retTuple)
                raw = bson.dumps(retTuple)
                rawLen = struct.pack('>I', len(raw))
                try:
                    self.sock.settimeout(2.0)
                    self.sock.send(rawLen)
                    self.sock.settimeout(180.0)
                    self.sock.sendall(raw)
                    self.sock.settimeout(None)
                except:
                    print('xxxx Warning! Exception occured in messageConsumer')
                    return
            else:
                print('xxxx Warning! Null response send in messageConsumer')
                return

    def queueClear(self):
        self.sock.settimeout(0.1)
        raw = self.sock.recv(4096)
        self.sock.settimeout(None)
        return

    def socketWatchDog(self):
        while True:
            time.sleep(360)
            if time.time() - self.recvTime > 360:
                print('xxxx Warning! socketWatchDog timeout at  %s' % datetime.datetime.now())
                self.initSocket()
            else:
                print('xxxx socketWatchDog: confirm the socket at %s' % datetime.datetime.now())

    def remoteCommand(self, data):
        global global_analyzeFlag
        global global_recordFlag
        global global_recordFile
        global global_exitFlag
        global global_fs
        global global_msgLevel
        global global_senseHatFlag
        global global_sense

        if global_msgLevel > 4:
            print('remoteCommand', data)

        if data['cmd'] == '/v1/status':
            msg = {
                'detect' : global_analyzeFlag,
                'record' : global_recordFlag
                }
            if global_recordFlag:
                msg['recordData'] = global_recordFile
            return msg

        elif data['cmd'] == '/v1/detect/stop':
            if global_msgLevel > 2:
                print('Stop the sound detection.')
            global_analyzeFlag = False
            if global_senseHatFlag:
                global_sense.clear()
            msg = {
                'token' : data['token']
                }
            return msg

        elif data['cmd'] == '/v1/detect/start':
            if global_recordFlag:
                global_recordFlag = False
                if global_msgLevel > 2:
                    print('Stop the sound recording.')
                outDir = global_soundLogDir + '/record/'
                sf.write(outDir + global_recordFile, np.array(self.wavRecord), global_fs)
                if global_msgLevel > 2:
                    print('Saved the sound to %s.' % global_recordFile)
                self.wavRecord = []

            if global_msgLevel > 2:
                print('Restart the sound detection.')
            global_analyzeFlag = True
            if global_senseHatFlag:
                global_sense.clear()

            msg = {
                'token' : data['token']
                }
            return msg

        elif data['cmd'] == '/v1/record/start':
            if global_msgLevel > 2:
                print('Start the sound recording.')
            global_analyzeFlag = False
            outDir = global_soundLogDir + '/record/'
            global_recordFile = data['key']
            if not os.path.exists(outDir):
                os.makedirs(outDir)
            global_recordFlag = True
            if global_senseHatFlag:
                global_sense.clear()

            msg = {
                'token' : data['token']
                }
            return msg

        elif data['cmd'] == '/v1/record/stop':
            if global_msgLevel > 2:
                print('Stop the sound recording.')
            if global_recordFlag:
                global_recordFlag = False
                outDir = global_soundLogDir + '/record/'
                sf.write(outDir + global_recordFile, np.array(self.wavRecord), global_fs)
                if global_msgLevel > 2:
                    print('Saved the sound to %s.' % global_recordFile)
                self.wavRecord = []
            if global_senseHatFlag:
                global_sense.clear()
            msg = {
                'token' : data['token']
                }
            return msg

        elif data['cmd'] == '/v1/recordList':
            recordList = []
            outDir = global_soundLogDir + '/record/'
            if os.path.exists(outDir):
                dataList = os.listdir(outDir)
            else:
                os.makedirs(outDir)
                dataList = []
            recordListFile = global_soundLogDir + '/recordList.csv'
            if os.path.exists(recordListFile):
                with open(recordListFile, "r", encoding="utf_8") as f:
                    recordListOld = csv.reader(f, delimiter=",", doublequote=True, lineterminator="\n", quotechar='"', skipinitialspace=True)
                    for line in recordListOld:
                        data = line[2]
                        if data in dataList:
                            recordList.append(line)
                    for data in dataList:
                        found = False
                        for line in recordList:
                            if data == line[2]:
                                found = True
                                break
                        if not found:
                            recordList.append(['','',data,''])
            else:
                for data in dataList:
                    recordList.append(['','',data,''])
            with open(recordListFile, "w") as f:
                writer = csv.writer(f, lineterminator='\n')
                writer.writerows(recordList)
            res = {
                'num' : len(recordList),
                'list' : recordList
            }
            return res

        elif data['cmd'] == '/v1/recordData/update':
            recordList = []
            eventName = data['eventName']
            subName = data['subName']
            fileName = data['fileName']
            remarks = data['remarks']
            outDir = global_soundLogDir + '/record/'

            recordListFile = global_soundLogDir + '/recordList.csv'
            if os.path.exists(recordListFile):
                with open(recordListFile, "r", encoding="utf_8") as f:
                    recordListOld = csv.reader(f, delimiter=",", doublequote=True, lineterminator="\n", quotechar='"', skipinitialspace=True)
                    for line in recordListOld:
                        data = line[2]
                        if data == fileName:
                            line = [eventName, subName, fileName, remarks]
                        recordList.append(line)
            else:
                msg = {
                    'token' : data['token'],
                    'error' : 'recordList not found.'
                    }
                return msg

            with open(recordListFile, "w") as f:
                writer = csv.writer(f, lineterminator='\n')
                writer.writerows(recordList)

            res = {
                'num' : len(recordList),
                'list' : recordList
            }
            return res

        elif data['cmd'] == '/v1/recordData/get':
            key = data['key']
            recordFile = global_soundLogDir + '/record/' + data['key']
            if os.path.exists(recordFile):
                with open(recordFile, 'rb') as f:
                    wavData = f.read()

                msg = {
                    'token' : data['token'],
                    'wavData' : wavData
                    }
                if global_msgLevel > 2:
                    print('Send a record data to cloud: ', key)
                return msg
            else:
                msg = {
                    'token' : data['token'],
                    'error' : 'Can not exist the record data [%s].' % key
                    }
                return msg

        elif data['cmd'] == '/v1/recordData/delete':
            key = data['key']
            recordFile = global_soundLogDir + '/record/' + data['key']
            if os.path.exists(recordFile):
                try:
                    os.remove(recordFile)
                    if global_msgLevel > 2:
                        print('Delete a record data %s.' % key)
                except:
                    print('Error: Fail to delete ' + key)
                    msg = {
                        'token' : data['token']
                        }
                    return msg

            recordList = []
            recordListFile = global_soundLogDir + '/recordList.csv'
            if os.path.exists(recordListFile):
                with open(recordListFile, "r", encoding="utf_8") as f:
                    recordListOld = csv.reader(f, delimiter=",", doublequote=True, lineterminator="\n", quotechar='"', skipinitialspace=True)
                    for line in recordListOld:
                        data = line[2]
                        if data != key:
                            recordList.append(line)

                with open(recordListFile, "w") as f:
                    writer = csv.writer(f, lineterminator='\n')
                    writer.writerows(recordList)

                res = {
                    'num' : len(recordList),
                    'list' : recordList
                }
                return res

            else:
                msg = {
                    'token' : data['token']
                    }
                return msg

        elif data['cmd'] == '/v1/recordData/play':
            key = data['key']
            if global_msgLevel > 2:
                print('Play a record data %s.' % key)
            msg = {
                'token' : data['token']
                }
            return msg

        elif data['cmd'] == '/v1/client/stop':
            key = data['key']
            if global_msgLevel > 2:
                print('Stop this client.')
            msg = {
                'token' : data['token']
                }
            global_exitFlag = True
            return msg

        elif data['cmd'] == '/v1/client/shutdown':
            key = data['key']
            if global_msgLevel > 2:
                print('Shutdown this client.')
            msg = {
                'token' : data['token']
                }
            th_shutdown = threading.Thread(target=shutdown, name='shutdown')
            th_shutdown.start()
            return msg

        elif data['cmd'] == '/v1/client/reboot':
            key = data['key']
            if global_msgLevel > 2:
                print('Reboot this client.')
            msg = {
                'token' : data['token']
                }
            th_reboot = threading.Thread(target=reboot, name='reboot')
            th_reboot.start()
            return msg

    ### Analyze ###
    def analyze(self, chunk, startTime, syncMode=False, trainMode=False):
        global global_analyzeFlag
        global global_recordFlag
        global global_exitFlag
        global global_senseHatFlag
        global global_sense

        if global_senseHatFlag:
            for event in global_sense.stick.get_events():
                if event.action == "pressed":
                    shutdown()

        if global_exitFlag:
            sys.exit()
        elif global_analyzeFlag:
            return self.analyzeChunk(chunk, startTime, syncMode, trainMode)
        elif global_recordFlag:
            self.recordChunk(chunk, startTime, syncMode)

    ### Record Chunk ###
    def recordChunk(self, chunk, startTime, syncMode):
        global global_fs
        global global_soundLogDir
        global global_recordFlag
        global global_recordFile
        global global_senseHatFlag
        global global_sense

        if global_senseHatFlag:
            global_sense.clear()

        if len(self.wavRecord) < global_fs * self.recordMaxLen:
            self.wavRecord.extend(chunk)
            if global_senseHatFlag:
                time.sleep(0.2)
                global_sense.set_pixel(3, 3, [255, 0, 0])
                global_sense.set_pixel(3, 4, [255, 0, 0])
                global_sense.set_pixel(4, 3, [255, 0, 0])
                global_sense.set_pixel(4, 4, [255, 0, 0])
        else:
            global_recordFlag = False
            outDir = global_soundLogDir + '/record/'
            sf.write(outDir + global_recordFile, np.array(self.wavRecord), global_fs)
            if global_msgLevel > 2:
                print('Saved the sound to %s.' % global_recordFile)
            self.wavRecord = []

        return

    ### Analyze Chunk ###
    def analyzeChunk(self, chunk, startTime, syncMode, trainMode):

        global global_fs
        global global_msgLevel
        global global_clientVersion
        global global_queue
        global global_senseHatFlag
        global global_sense

        self.cCount += 1
        chunkClkSize = chunk.shape[0]
        chunkSpecSize = int(chunkClkSize / self.nhop)
        if trainMode: eventList = []
        stTime = time.time()
        if global_msgLevel > 3:
            print('### Analyze Chunk No.%s ###' % self.cCount) # XXXXXXXXXX
        if global_senseHatFlag:
            global_sense.clear()

        # shift time
        if self.eventStFlag == True:
            self.eventSt -= chunkSpecSize
            self.eventEt -= chunkSpecSize
            self.eventPeakT -= chunkSpecSize
            self.eventHalfT -= chunkSpecSize

        # update threshold of events (auto gain control)
        if self.agcFlag:
            # update power threshold
            if self.cCount % self.powerCountAdoptInterval == 0:
                if self.powerCount > self.powerCountMax:
                    self.powerTh *= self.powerCountAdoptRate
                with open('powerTh.txt', mode='w') as f:
                    f.write(str(self.powerTh))
            elif self.cCount < self.powerThDecayInitTime:
                self.powerTh *= self.powerThDecayInit
            else:
                self.powerTh *= self.powerThDecay

            # update spectrum threshold
            if self.cCount % self.spectrumCountAdoptInterval == 0:
                if self.spectrumCount > self.spectrumCountMax:
                    self.spectrumTh *= self.spectrumCountAdoptRate
                with open('spectrumTh.txt', mode='w') as f:
                    f.write(str(self.spectrumTh))
            elif self.cCount < self.spectrumThDecayInitTime:
                self.spectrumTh *= self.spectrumThDecayInit
            else:
                self.spectrumTh *= self.spectrumThDecay

        # decay count
        self.powerCount *= self.powerCountDecay
        self.spectrumCount *= self.spectrumCountDecay

        # calc spectrogrum
        self.sigBuff = np.append(self.sigBuff[chunkClkSize:], chunk)
        currSig = self.sigBuff[-chunkClkSize-self.sigMargin*2:]
        Vf = self.cq_fft(currSig)
        Vf_abs = abs(Vf)
        #print('## calc spectrogrum time = %f' % (time.time() - stTime)) # XXXXXXXXXX
        lapTime = time.time()

        # calc sound power
        Ptt = np.sum(Vf_abs, axis=1)

        # calc accommodation
        tSize = Vf_abs.shape[0]
        Vt_accommo = np.empty((tSize,self.nfreq))
        for t in range(tSize):
            for f in range(self.nfreq):
                self.accommoBuff[f] *= self.accommoFact
                self.accommoBuff[f] += Vf_abs[t][f]
                Vt_accommo[t][f] = self.accommoBuff[f] / self.accommoLen

        # marge to buffer
        self.spectBuff = np.concatenate([self.spectBuff[chunkSpecSize:], Vf_abs[self.spectMargin:-self.spectMargin]], axis=0)
        self.accommoSpectBuff = np.concatenate([self.accommoSpectBuff[chunkSpecSize:], Vt_accommo[self.spectMargin:-self.spectMargin]], axis=0)
        self.powerBuff = np.concatenate([self.powerBuff[chunkSpecSize:], Ptt[self.spectMargin:-self.spectMargin]])

        # extract analyzing window
        Vfa = self.spectBuff[self.spectBuffSize-chunkSpecSize-self.spectMargin:self.spectBuffSize-self.spectMargin]

        # power event tracker
        for t in range(self.spectBuffSize-chunkSpecSize-self.spectMargin,self.spectBuffSize-self.spectMargin):
            Pt = self.powerBuff[t]

            # search strong sound events
            if self.eventStFlag == False:
                if Pt > self.powerTh:
                    # find a event
                    self.eventStFlag = True
                    self.eventEdFlag = False
                    self.eventSt = t
                    self.eventStPower = Pt
                    self.eventPeakPower = self.eventStPower
                    self.eventPeakT = t
                    self.eventPeakPower = self.eventStPower
                    self.eventPeakT = t
                    self.eventHalfPower = self.eventStPower
                    self.eventHalfT = t
                    #print('# find a event at %d' % t)   # XXXXXXXXXXXX
            else:
                if Pt > self.eventPeakPower:    # eventPeak
                    self.eventPeakPower = Pt
                    self.eventPeakT = t

                    if Pt / 4 > self.eventStPower:
                        eventSt = self.eventSt
                        PtTh = Pt / 4
                        while PtTh > self.powerBuff[eventSt]:
                            eventSt += 1
                        self.eventSt = eventSt-1
                        self.eventStPower = self.powerBuff[eventSt-1]

                if Pt < self.eventPeakPower / 2:    # eventHalf
                    self.eventHalfPower = Pt
                    self.eventHalfT = t

                if self.eventEdFlag:    # anti chattering
                    if t - self.eventSt > self.eventMaxLen:
                        self.eventFixFlag = True
                    elif Pt < self.powerTh:
                        self.eventDisappear += 1
                        if self.eventDisappear > self.eventDisappearMax:
                            self.eventFixFlag = True
                    else:
                        self.eventEdFlag = False

                else:
                    if Pt < self.eventPeakPower / 4 or t - self.eventSt > self.eventMaxLen: # eventEd
                        self.eventEdFlag = True
                        self.eventEt = t
                        self.eventDisappear = 0
                        self.eventFixFlag = False

                        # update threshold of power events
                        if self.eventPeakPower > self.powerTh / self.powerMaxThRetio:
                            self.powerTh = self.eventPeakPower * self.powerMaxThRetio

                if self.eventFixFlag:
                    self.eventStFlag = False
                    self.eventFixFlag = False

                    # post to the cloudEdge
                    if self.eventEt - self.eventSt > self.eventMinLen:
                        self.powerCount += 1.
                        st = self.eventSt
                        ed = self.eventEt
                        if st < 0: st = 0
                        stClk = (st - self.spectMargin) * self.nhop
                        edClk = (ed - self.spectMargin) * self.nhop
                        stChunkClk = stClk - (self.chunkSize + 3 * global_fs - chunkClkSize)
                        edChunkClk = edClk - (self.chunkSize + 3 * global_fs - chunkClkSize)
                        stUxTime = startTime + stChunkClk / global_fs
                        edUxTime = startTime + edChunkClk / global_fs
                        if st > 1:
                            Af = self.accommoSpectBuff[st-1]
                        else:
                            Af = self.accommoSpectBuff[st]
                        Sx = self.sigBuff[-round(0.2*global_fs)+stClk:edClk]
                        Vx = self.spectBuff[st:ed+1].T * 1.0e5
                        Vx[:,0] = Af * 1.0e5
                        maxFreq = 0
                        maxFreqPower = self.spectBuff[self.eventPeakT][0]
                        for f in range(1,self.nfreq):
                            if self.spectBuff[self.eventPeakT][f] > maxFreqPower:
                                maxFreqPower = self.spectBuff[self.eventPeakT][f]
                                maxFreq = f
                        maxFreqPower /= Vx.shape[1]
                        eventPeakT = self.eventPeakT-self.eventSt
                        eventHalfT = self.eventHalfT-self.eventSt
                        feature = {
                            "category" : "power",
                            "frequency" : self.freqs[maxFreq],
                            "freqPower" : maxFreqPower,
                            "eventStPower" : self.eventStPower,
                            "eventPeakT" : eventPeakT,
                            "eventPeakPower" : self.eventPeakPower,
                            "eventHalfT" : eventHalfT,
                            "eventHalfPower" : self.eventHalfPower,
                            "eventDuration" : t - self.eventSt
                        }
                        if global_msgLevel > 0:
                            #print('XXXX find a power event at %d:%d, P = %.2f' % (self.eventSt,t,maxFreqPower)) # XXXXXXXXX
                            #print('XXXX find a power event at %.1f:%.1f, P = %.2f' % (stUxTime,edUxTime,maxFreqPower)) # XXXXXXXXX
                            if stUxTime > 60*60*24*365:
                                loc = time.strftime("%H:%M:%S", time.localtime(stUxTime))
                            else:
                                loc = str(round(stUxTime, 1))
                            print('%s find a power event, P = %.2f' % (loc, maxFreqPower*10000)) # XXXXXXXXX
                            if global_senseHatFlag and global_analyzeFlag:
                                p = int(maxFreqPower * 500)
                                # print('p = ',p) # XXXXXXXXXX
                                if p > 7: p = 7
                                for ii in range(p+1):
                                    global_sense.set_pixel(0, 7-ii, [0, 255, 0])
                                feature['temperature'] = global_sense.get_temperature()
                                feature['pressure'] = global_sense.get_pressure()
                                feature['humidity'] = global_sense.get_humidity()
                        if trainMode:
                            eventList.append((Sx,Vx,stUxTime,feature))
                        elif syncMode:
                            self.analyzeEvent(Sx,Vx,stUxTime,feature,global_queue)
                        else:
                            if global_msgLevel > 3:
                                print('Debug: thread num = %d' % threading.active_count())
                            if threading.active_count() < 10:
                                th = threading.Thread(target=self.analyzeEvent, name='analyzeEvent', args=(Sx,Vx,stUxTime,feature,global_queue))
                                th.setDaemon(True)
                                th.start()
                            else:
                                print('Warning! There are too many thread. n = %d' % threading.active_count())

                        # annotation
                        if global_powerAnnotationFlag:
                            self.powerAnnotationFd.write('%f, powEvent start\n' % stUxTime)
                            self.powerAnnotationFd.write('%f, powEvent end\n' % edUxTime)

                        """
                        import matplotlib.pyplot as plt

                        fig = plt.figure(1, figsize=(6, 2))
                        ax = fig.add_subplot(111)
                        ax.plot(Sx)
                        ax.set_title("test signal")
                        ax.set_xlabel("time")
                        ax.set_ylabel("signal")
                        plt.show()

                        Vt_log = np.log(Vx)
                        plt.imshow(Vt_log, aspect="auto", origin = "lower", cmap='jet')
                        plt.xticks(fontsize = 8)
                        plt.yticks(np.arange(self.nfreq)[::24], self.freqs[::24], fontsize = 8)
                        plt.xlabel("time [s]")
                        plt.ylabel("frequency [Hz]")
                        plt.colorbar()
                        plt.show()

                        """

        #print('## power event detection time = %f' % (time.time() - lapTime)) # XXXXXXXXXX
        lapTime = time.time()

        # calc delta Vfa
        dVfa = np.empty((Vfa.shape[0],Vfa.shape[1]-self.dfreq))
        for t in range(Vfa.shape[0]):
            for f in range(self.nfreq-self.dfreq):
                dVfa[t][f] = Vfa[t][f+self.dfreq] - Vfa[t][f]
                if dVfa[t][f] < 0: dVfa[t][f] = 0

        # peak tracker
        for t in range(chunkSpecSize):
            for i in range(self.nBand):
                dVfaPeak = 0
                fPeak = 0
                raiseFlag = False
                peak = [[-1,0] for ii in range(self.nTrack)]
                for f in range(self.band[i][0], self.band[i][1]):
                    # peak detection
                    if dVfa[t][f] > dVfaPeak:
                        dVfaPeak = dVfa[t][f]
                        fPeak = f
                        raiseFlag = True
                    elif raiseFlag: # detect a peak
                        #print('Detect a peak at f = %d' % fPeak) # XXXXXXXXX
                        raiseFlag = False
                        for j in range(self.nTrack):
                            if peak[j][1] < dVfaPeak:
                                #print('It is stronger than peak[%d]' % j) # XXXXXXX
                                if j+1 < self.nTrack-1:
                                    #print('Therefore, insert the peak into %d' % j) # XXXXXXX
                                    for k in range(self.nTrack-1, j, -1):
                                        #print('shift %d' % k) # XXXXXXXXXXXXX
                                        peak[k][0] = peak[k-1][0]
                                        peak[k][1] = peak[k-1][1]
                                        #print('shifted peak', peak) # XXXXXXXXXXXXX
                                peak[j][0] = fPeak
                                peak[j][1] = dVfaPeak
                                #print('inserted peak', peak) # XXXXXXXXXXXXX
                                break

                #print('  peak', peak) # XXXXXXXXXXXX
                #print('  self.peakTrack', self.peakTrack) # XXXXXXXXXXXX

                # peak track
                for j in range(self.nTrack):
                    if self.peakTrack[self.nTrack*i+j][0] < 0: continue

                    # find the nearest peak
                    fDiffMin = self.nfreq
                    nearest = -1
                    for k in range(self.nTrack):
                        if peak[k][0] == -1: break

                        fDiff = abs(peak[k][0] - self.peakTrack[self.nTrack*i+j][0])
                        if fDiff < fDiffMin:
                            fDiffMin = fDiff
                            nearest = k

                    # rule the peak is in the same track or not
                    if fDiffMin <= self.trackW:
                        # adopt to track
                        #print('    track f=%d by tracker No.%d' % (peak[nearest][0], self.nTrack*i+j)) # XXXXXXXXXXXX

                        # freq differance
                        self.peakTrack[self.nTrack*i+j][2] *= (2.0/3.0)
                        self.peakTrack[self.nTrack*i+j][2] += (peak[nearest][0] - self.peakTrack[self.nTrack*i+j][0]) / 3.0
                        # freq
                        self.peakTrack[self.nTrack*i+j][0] = peak[nearest][0]
                        # power differance
                        self.peakTrack[self.nTrack*i+j][3] *= (2.0/3.0)
                        self.peakTrack[self.nTrack*i+j][3] += (dVfa[t][peak[nearest][0]] - self.peakTrack[self.nTrack*i+j][1]) / 3.0
                        # power
                        self.peakTrack[self.nTrack*i+j][1] *= (self.trackL-1.0)/self.trackL
                        self.peakTrack[self.nTrack*i+j][1] += dVfa[t][peak[nearest][0]]/self.trackL
                        # alive time
                        self.peakTrack[self.nTrack*i+j][4] += 1
                        # lost time
                        self.peakTrack[self.nTrack*i+j][5] = 0
                        #print('    power = %f -> %f' % (dVfa[t][peak[nearest][0]], self.peakTrack[self.nTrack*i+j][1])) # XXXXXXXXXX

                        # clear peak
                        peak[nearest][0] = -1
                        peak[nearest][1] = 0

                    else: # lost peak
                        # lost time
                        self.peakTrack[self.nTrack*i+j][0] += self.peakTrack[self.nTrack*i+j][2]
                        self.peakTrack[self.nTrack*i+j][1] *= (self.trackL-1.0)/self.trackL
                        self.peakTrack[self.nTrack*i+j][4] += 1
                        self.peakTrack[self.nTrack*i+j][5] += 1
                        #print('    lost time = ', self.peakTrack[self.nTrack*i+j][5]) # XXXXXXXXXX

                # new peak
                for j in range(self.nTrack):
                    if peak[j][0] == -1: continue

                    # search a blank tracker
                    for k in range(self.nTrack):
                        if self.peakTrack[self.nTrack*i+k][0] == -1: # find a blank tracker
                            #print('    set a new tracker No.%d' % (self.nTrack*i+k)) # XXXXXXXXXXXX

                            # set to a new peak tracker
                            self.peakTrack[self.nTrack*i+k][0] = peak[j][0]
                            self.peakTrack[self.nTrack*i+k][1] = dVfa[t][peak[j][0]]/self.trackL
                            self.peakTrack[self.nTrack*i+k][2] = 0
                            self.peakTrack[self.nTrack*i+k][3] = 0
                            self.peakTrack[self.nTrack*i+k][4] = 0
                            self.peakTrack[self.nTrack*i+k][5] = 0
                            self.peakTrack[self.nTrack*i+k][6] = 0
                            peak[j][0] = -1
                            peak[j][1] = 0
                            break
                    if peak[j][0] == -1: continue

                    # replace into a current tracker
                    pMin = self.peakTrack[self.nTrack*i][1]
                    idx = self.nTrack*i
                    for k in range(1,self.nTrack):
                        if self.peakTrack[self.nTrack*i+k][1] < pMin:
                            pMin = self.peakTrack[self.nTrack*i+k][1]
                            idx = self.nTrack*i+k
                    if pMin < peak[j][1]:
                        #print('    replace to new tracker No.%d' % idx) # XXXXXXXXXXXX

                        # replace to new tracker
                        self.peakTrack[idx][0] = peak[j][0]
                        self.peakTrack[idx][1] = dVfa[t][peak[j][0]]
                        self.peakTrack[idx][2] = 0
                        self.peakTrack[idx][3] = 0
                        self.peakTrack[idx][4] = 0
                        self.peakTrack[idx][5] = 0
                        self.peakTrack[idx][6] = 0
                        peak[j][0] = -1
                        peak[j][1] = 0

            # evaluate spectrum peakTrack
            for band in range(self.nBand):
                for track in range(self.nTrack):
                    spectrumEventFlag = False
                    i = band * self.nTrack + track

                    # check the end of the peak track
                    if self.peakTrack[i][5] > self.peakLostMax:
                        # check if the track was already adopted to an event
                        if self.peakTrack[i][6] > 0:
                            # initialize the peak track
                            self.peakTrack[i][0] = -1
                            self.peakTrack[i][1] = 0
                            self.peakTrack[i][2] = 0
                            self.peakTrack[i][3] = 0
                            self.peakTrack[i][4] = 0
                            self.peakTrack[i][5] = 0
                            self.peakTrack[i][6] = 0

                        # check duration
                        elif self.peakTrack[i][4] > self.peakDurTh: # event candidate
                            spectrumEventFlag = True
                            # print('Adopt the candidate due to long lost. i = ', i) # XXXXXXXXX

                            # check other peak track
                            for j in range(self.nBand*self.nTrack):
                                if i == j: continue
                                if self.peakTrack[j][6] > 0: continue
                                if abs(self.peakTrack[j][4]-self.peakTrack[i][4]) < self.peakErr:
                                    # compare freqPower of the candidate with other peak track
                                    if self.peakTrack[j][1] > self.peakTrack[i][1]:
                                        # ignore the candidate if weaker than other peak track
                                        spectrumEventFlag = False
                                    else:
                                        # adopt the candidate and initialize the peak track
                                        self.peakTrack[j][0] = -1
                                        self.peakTrack[j][1] = 0
                                        self.peakTrack[j][2] = 0
                                        self.peakTrack[j][3] = 0
                                        self.peakTrack[j][4] = 0
                                        self.peakTrack[j][5] = 0
                                        self.peakTrack[j][6] = 0

                    # check duration of the peak track
                    if self.peakTrack[i][4] > self.peakDurMax: # event candidate
                        # check if the track was not already adopted to an event
                        if self.peakTrack[i][6] == 0:
                            # adopt the candidate
                            spectrumEventFlag = True
                            # print('Adopt the candidate due to long duration. i= ', i) # XXXXXXXXX
                            # set end power and continue to track
                            self.peakTrack[i][6] = self.peakTrack[i][1]
                        # check if power of the track is learger than the end power * 2
                        elif self.peakTrack[i][1] > self.peakTrack[i][6] * 2:
                            self.peakTrack[i][4] = t
                            self.peakTrack[i][6] = 0
                            # print('Reset the track due to strong peak. i= ', i) # XXXXXXXXX

                    # adopt the candidate to a spectrum event
                    if spectrumEventFlag:
                        st = int(t-self.peakTrack[i][4])
                        ed = int(t-self.peakLostMax)
                        stSpec = st - self.spectMargin*2
                        edSpec = ed - self.spectMargin*2
                        stClk = stSpec * self.nhop
                        edClk = edSpec * self.nhop
                        stUxTime = startTime + stClk / global_fs
                        edUxTime = startTime + edClk / global_fs
                        Sx = self.sigBuff[-round(0.2*global_fs)-chunkClkSize+stClk:-chunkClkSize+edClk]
                        Vx = self.spectBuff[-chunkSpecSize+stSpec:-chunkSpecSize+edSpec+1].T * 1.0e5
                        if -chunkSpecSize+stSpec > 1:
                            Af = self.accommoSpectBuff[-chunkSpecSize+stSpec-1]
                        else:
                            Af = self.accommoSpectBuff[-chunkSpecSize+stSpec]
                        freqPower = np.sum(Vx, axis=1)
                        maxFreq = 0
                        maxFreqPower = freqPower[0]
                        for f in range(1,self.nfreq):
                            if freqPower[f] > maxFreqPower:
                                maxFreqPower = freqPower[f]
                                maxFreq = f
                        maxFreqPower /= Vx.shape[1]

                        # update threshold of spectrum events
                        if maxFreqPower > self.spectrumTh / self.spectrumMaxThRetio:
                            self.spectrumTh = maxFreqPower * self.spectrumMaxThRetio

                        # rule spectrum event or not
                        if maxFreqPower > self.spectrumTh:
                            self.spectrumCount += 1.
                            feature = {
                                "category" : "spectrum",
                                "frequency" : self.freqs[maxFreq],
                                "freqPower" : maxFreqPower,
                                "freqDiff" : self.peakTrack[i][2],
                                "powerDiff" : self.peakTrack[i][3],
                                "eventDuration" : ed-st
                            }
                            if global_msgLevel > 0:
                                #print('XXXX find a spectrum event at %.1f:%.1f, f = %.1fHz' % (stUxTime,edUxTime,self.freqs[maxFreq])) # XXXXXXXXX
                                if stUxTime > 60*60*24*365:
                                    loc = time.strftime("%H:%M:%S", time.localtime(stUxTime))
                                else:
                                    loc = str(round(stUxTime, 1))
                                print('%s find a spectrum event, f = %.1fHz' % (loc,self.freqs[maxFreq])) # XXXXXXXXX
                            if global_senseHatFlag and global_analyzeFlag:
                                f = int(maxFreq/12)
                                # print('f = ', f) # XXXXXXXXXXXXXXXX
                                if f > 7: f = 7
                                global_sense.set_pixel(7, 7-f, [255, 0, 0])
                                feature['temperature'] = global_sense.get_temperature()
                                feature['pressure'] = global_sense.get_pressure()
                                feature['humidity'] = global_sense.get_humidity()
                            if trainMode:
                                eventList.append((Sx,Vx,stUxTime,feature))
                            elif syncMode:
                                self.analyzeEvent(Sx,Vx,stUxTime,feature,global_queue)
                            else:
                                if global_msgLevel > 3:
                                    print('Debug: thread num = %d' % threading.active_count())
                                if threading.active_count() < 10:
                                        th = threading.Thread(target=self.analyzeEvent, name='analyzeEvent', args=(Sx,Vx,stUxTime,feature,global_queue))
                                        th.setDaemon(True)
                                        th.start()
                                else:
                                    print('Warning! There are too many thread. n = %d' % threading.active_count())

                            # annotation
                            if global_spectrumAnnotationFlag:
                                self.spectrumAnnotationFd.write('%f, spectEvent start\n' % stUxTime)
                                self.spectrumAnnotationFd.write('%f, spectEvent end\n' % edUxTime)

                            """
                            import matplotlib.pyplot as plt
                            Vt_log = np.log(Vx)
                            plt.imshow(Vt_log, aspect="auto", origin = "lower", cmap='jet')
                            plt.xticks(fontsize = 8)
                            plt.yticks(np.arange(self.nfreq)[::24], self.freqs[::24], fontsize = 8)
                            plt.xlabel("time [s]")
                            plt.ylabel("frequency [Hz]")
                            plt.colorbar()
                            plt.show()
                            """

                        if self.peakTrack[i][6] == 0:
                            self.peakTrack[i][0] = -1
                            self.peakTrack[i][1] = 0
                            self.peakTrack[i][2] = 0
                            self.peakTrack[i][3] = 0
                            self.peakTrack[i][4] = 0
                            self.peakTrack[i][5] = 0
                            self.peakTrack[i][6] = 0

        #print('## spectrum event detection time = %f' % (time.time() - lapTime)) # XXXXXXXXXX
        lapTime = time.time()

        #print('### total analyze time = %f' % (time.time() - stTime)) # XXXXXXXXXX

        sys.stdout.flush()

### For debug #################################################################
        """
        # Log(spectBuff)
        plt.imshow(self.spectBuff.T, aspect="auto", origin = "lower", cmap='jet')
        plt.xticks(fontsize = 8)
        plt.yticks(np.arange(self.nfreq)[::24], self.freqs[::24], fontsize = 8)
        plt.xlabel("time [s]")
        plt.ylabel("frequency [Hz]")
        plt.colorbar()
        plt.show()

        # dVfa
        plt.imshow(dVfa.T, aspect="auto", origin = "lower", cmap='jet')
        plt.xticks(fontsize = 8)
        plt.yticks(np.arange(self.nfreq)[::24], self.freqs[::24], fontsize = 8)
        plt.xlabel("time [s]")
        plt.ylabel("frequency [Hz]")
        plt.colorbar()
        plt.show()

        # sigBuff
        fig = plt.figure(1, figsize=(6, 2))
        ax = fig.add_subplot(111)
        ax.plot(self.sigBuff)
        ax.set_title("test signal")
        ax.set_xlabel("time")
        ax.set_ylabel("signal")
        plt.show()
        """

### For debug #################################################################

        if trainMode:
            return eventList

        results = []
        while not global_queue.empty():
            result = global_queue.get()
            if global_msgLevel > 3:
                print(json.dumps(result, sort_keys=True, indent=4))
            if result['detectFlag']:
                results.append(result)

        return results

    def setKernel(self, fs, fmin, fmax, f_bins, q_fact, spThresh, nhop):
        """
        Constructor
        @fmin = 110                     # min of frequency
        @fmax = 7040                    # max of frequency
        @f_bins = 24                    # freq bins per 1 octave
        @q_fact = 20.                   # quality factor
        @spThresh = 0.0054              # threshold of sparse kernel
        @return void
        """

        self.f_bins = f_bins
        self.nhop = nhop

        # print('Calc New Kernel')

        # Calculate Constant-Q Properties
        fratio = 1.0 / f_bins
        nfreq = get_num_freq(fmin, fmax, fratio) # number of freq bins
        freqs = get_freqs(fmin, nfreq, fratio) # freqs [Hz]
        q_rate = q_fact * fratio # quality rate
        Q = int((1. / ((2 ** fratio) - 1)) * q_rate) # Q value

        # N  > max(N_k)
        fftLen = int(2 ** (ceil(log2(int(float(fs * Q) / freqs[0])))))

        sparseKernel = zeros([nfreq, fftLen], dtype = complex128)
        for k in range(nfreq):
            tmpKernel = zeros(fftLen, dtype = complex128)
            freq = freqs[k]
            # N_k
            N_k = int(float(fs * Q) / freq)
            # Adjust the center of fft window with analyzing part
            startWin = int((fftLen - N_k) / 2)
            tmpKernel[startWin : startWin + N_k] = (hamming(N_k) / N_k) * exp(two_pi_j * Q * arange(N_k, dtype = float64) / N_k)
            # FFT (kernel matrix)
            sparseKernel[k] = fft(tmpKernel)

        sparseKernel[abs(sparseKernel) <= spThresh] = 0

        sparseKernel = csr_matrix(sparseKernel)
        sparseKernel = sparseKernel.conjugate() / fftLen

        self.sparseKernel = sparseKernel
        self.nfreq = nfreq
        self.freqs = freqs
        self.fftLen = fftLen
        self.Q = Q

        return

    def cq_fft(self, sig):

        # Preparation
        L = len(sig)
        nframe = int(L / self.nhop) # number of time frames

        ### New signal (for Calculation)
        new_sig = zeros(len(sig) + self.fftLen, dtype = float64)
        h_fftLen = int(self.fftLen / 2)
        new_sig[h_fftLen : -h_fftLen] = sig

        cq_spect = zeros([nframe, self.nfreq], dtype = complex128)
        for iiter in range(nframe):
            istart = iiter * self.nhop
            iend = istart + self.fftLen
            # FFT (input signal)
            sig_fft = fft(new_sig[istart : iend])
            # Matrix product
            cq_spect[iiter] = sig_fft * self.sparseKernel.T

        return cq_spect
