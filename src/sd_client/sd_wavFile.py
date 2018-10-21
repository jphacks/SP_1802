#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import math
import numpy as np
import time
import soundfile as sf
import requests

### Sound Detect Client for wav file ##########################################
__author__  = "Yoshihiro Kajiki <y-kajiki@ah.jp.nec.com>"
__version__ = "3.2"
__date__    = "Sep 20, 2018"

### Usage: $ python sd_wavFile.py deviceID soundFile.wav                   ###

###############################################################################
def getSdk(deviceID):
    request_url = 'https://' + mngServer + '/api/assets/sdk/' + deviceID + '/sd_sdk.py'
    proxies = ''
    res = requests.get(request_url, proxies=proxies)
    with open('sd_sdk.py', 'w') as f:
        f.write(res.text)

###############################################################################
if __name__ == "__main__":

    ### Read and Set Configuration ###
    import sd_config

    deviceID = sd_config.deviceID
    msgLevel = sd_config.msgLevel
    getSdkFlag = sd_config.getSdkFlag
    useEdgeFlag = sd_config.useEdgeFlag
    localEdgeFlag = sd_config.localEdgeFlag
    eventTriggerFlag = sd_config.eventTriggerFlag
    soundLogFlag = sd_config.soundLogFlag
    soundLogDir = sd_config.soundLogDir
    useHistoryFlag = sd_config.useHistoryFlag
    remoteControlFlag = sd_config.remoteControlFlag
    senseHatFlag = sd_config.senseHatFlag
    mngServer = sd_config.mngServer
    logHost = sd_config.logHost
    fluentHost = sd_config.fluentHost
    fluentPort = sd_config.fluentPort
    syncMode = sd_config.syncMode
    proxies = sd_config.proxies

    ### Get commandline variables ###
    argvs = sys.argv
    argc = len(argvs)

    if deviceID != '':
        if argc == 2:
            soundFile = argvs[1]
        else:
            print('\nUsage: $ python %s soundFile.wav\n' % argvs[0])
            sys.exit()
    elif argc == 3:
        deviceID = argvs[1]
        soundFile = argvs[2]
    else:
        print('\nUsage: $ python %s deviceID soundFile.wav\n' % argvs[0])
        sys.exit()

    ### Read the test sound file ###
    if not os.path.exists(soundFile):
        print('\nError: Sound file %s not found.\n' % soundFile)
        sys.exit()

    try:
        signalTest, fsTest = sf.read(soundFile)
    except:
        print('\nError: Can not read the sound file [%s].\n' % soundFile)
        sys.exit()

    if len(signalTest.shape) > 1:
        noTracks = signalTest.shape[1]
    else:
        noTracks = 1

    track = 1
    if noTracks > 1:
        signalTest = np.delete(signalTest, np.s_[track:], axis=1)
        signalTest = np.delete(signalTest, np.s_[:track-1], axis=1)
        signalTest = signalTest.T[0]

    ### Create sound detector instance ###
    #chunkSize = fsTest * 15
    chunkSize = fsTest
    chunkTimeLen = chunkSize / fsTest
    if getSdkFlag: getSdk(deviceID)
    import sd_sdk
    sd = sd_sdk.soundDetector(deviceID, fsTest, chunkSize, useEdgeFlag=useEdgeFlag, localEdgeFlag=localEdgeFlag, eventTriggerFlag=eventTriggerFlag, soundLogFlag=soundLogFlag, soundLogDir=soundLogDir, useHistoryFlag=useHistoryFlag, msgLevel=msgLevel, mngServer=mngServer, remoteControlFlag=remoteControlFlag, senseHatFlag=senseHatFlag, logHost=logHost, fluentHost=fluentHost, fluentPort=fluentPort, proxies=proxies, version=__version__)

    ### Analyze audio signal by sound detector ###
    print('\nDetecting events in track no. %d of %s\n' % (track, soundFile))
    numChunks = math.ceil(signalTest.shape[0] / chunkSize)
    startTime = 0
    for st in range(0,numChunks*chunkSize,chunkSize):
        chunk = signalTest[st:st+chunkSize]
        ret = sd.analyze(chunk, startTime, syncMode=syncMode)
        startTime += chunkTimeLen

