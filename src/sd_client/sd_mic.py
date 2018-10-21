#!/usr/bin/env python
# -*- coding: utf-8 -*-

### Sound Detect Client for mic ###############################################
__author__  = "Yoshihiro Kajiki <y-kajiki@ah.jp.nec.com>"
__version__ = "3.11"
__date__    = "Sep 29, 2018"

### Usage: $ python sd_mic.py deviceID                                      ###

###############################################################################
import os
import sys
import threading
import time
import tarfile
import shutil
import numpy as np
import pyaudio as pa
import requests

###############################################################################
def setAudio():
    global chunk
    global msgLevel
    global audioEvent

    # pyaudio
    p_in = pa.PyAudio()

    # find input device
    if msgLevel > 2:
        print('\nSearching a audio input device ..\n')
        sys.stdout.flush()
    recording_device = []
    for i in range(p_in.get_device_count()):
        maxInputChannels = p_in.get_device_info_by_index(i)['maxInputChannels']
        if maxInputChannels > 0 and maxInputChannels < 32:
            if msgLevel > 3:
                print('  Found!: device_index = %d, maxInputChannels = %d' % (i, maxInputChannels))
                print('          defaultSampleRate = %d\n\n' % fs)
            fs = int(p_in.get_device_info_by_index(i)['defaultSampleRate'])
            recording_device.append((i, fs))

    # confirm
    num_recording_device = len(recording_device)
    if num_recording_device == 0:
        print("\nError! Can't find any usuable sound input device.")
        print("  Check your environment or try other computer.")
        sys.exit(1)
    if msgLevel > 2:
        print('Your computer has %d recording device(s).' % num_recording_device)
        sys.stdout.flush()

    # check
    maxDevice = -1
    maxPower = 0
    for (idx, fs) in recording_device:

        if msgLevel > 2:
            print('Checking device #', idx)
            sys.stdout.flush()

        inStream = startRecording(idx, fs, fs)
        audioEvent.wait()
        inStream.close()

        # convert audio chunk into numpy.ndarray of float
        npChunk = np.frombuffer(chunk, dtype=np.int16).astype(np.float) / 2**15
        audioEvent.clear()

        # Calc avarage intensity
        power = 0
        for s in npChunk:
            power += abs(s)
        power /= fs
        if msgLevel > 2:
            print('  power = ', power)
            sys.stdout.flush()

        # compair
        if power > maxPower:
            maxPower = power
            maxDevice = idx

    if maxDevice < 0:
        print("\nError! Can't find any usuable sound input device.")
        print("  All input device seems OFF.")
        print("  Check your environment or try other computer.")
        sys.exit(1)

    if msgLevel > 2:
        print("\nYour environment is OK.")
        print('  use_device_index = ', maxDevice)
        print('  SampleRate = ', fs)
        sys.stdout.flush()

    return maxDevice, fs

def startRecording(deviceIndex, fs, chunkSize):
    global msgLevel

    # pyaudio
    p_in = pa.PyAudio()
    bytes = 2
    py_format = p_in.get_format_from_width(bytes)
    channels = 1

    # generate an input stream
    inStream = p_in.open(format=py_format,
                          channels=channels,
                          rate=fs,
                          input=True,
                          frames_per_buffer=chunkSize,
                          input_device_index=deviceIndex,
                          stream_callback=callback)

    inStream.start_stream()

    if msgLevel > 2:
        print('Set Microphone: ON\n')
        sys.stdout.flush()

    return inStream

def callback(in_data, frame_count, time_info, status):
    global chunk
    global recTime
    global audioEvent

    in_data = np.frombuffer(in_data, dtype=np.int16)
    chunk = in_data.tobytes()
    recTime = time.time()
    audioEvent.set()

    return (in_data, pa.paContinue)

def getSdk(deviceID):
    global proxies
    global msgLevel

    if os.path.exists('sd_sdk.tar.gz'):
        os.remove('sd_sdk.tar.gz')

    request_url = 'https://' + mngServer + '/api/assets/sdk/' + deviceID + '/sd_sdk.tar.gz'

    while True:

        if msgLevel > 2:
            print('Get SDK')
            sys.stdout.flush()
        try:
            res = requests.get(request_url, timeout=5, stream=True, proxies=proxies)
            if (res.status_code > 299):
                print('Error! Can not get SDK.')
                print(res.text)
                sys.exit(1)
            if msgLevel > 2:
                print('  Got it!')
                sys.stdout.flush()
            break
        except:
            if msgLevel > 2:
                print('  No responce. Wait for 2 sec.')
                sys.stdout.flush()
            time.sleep(2)

    # save sdk
    with open('sd_sdk.tar.gz', 'wb') as file:
        res.raw.decode_content = True
        shutil.copyfileobj(res.raw, file)

    # expand tar
    with tarfile.open('sd_sdk.tar.gz', 'r') as tar:
        tar.extractall()
    os.remove('sd_sdk.tar.gz')

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

    if deviceID == '':
        if argc == 2:
            deviceID = argvs[1]
        else:
            sys.exit('\nUsage: $ python %s device_id\n' % argvs[0])
    elif argc > 1:
        sys.exit('\nUsage: $ python %s\n' % argvs[0])

    ### Setup audio device ###
    audioEvent = threading.Event()
    deviceIndex, fsTest = setAudio()

    ### Create sound detector instance ###
    chunkSize = fsTest
    chunkTimeLen = chunkSize / fsTest
    if getSdkFlag: getSdk(deviceID)
    import sd_sdk
    sd = sd_sdk.soundDetector(deviceID, fsTest, chunkSize, useEdgeFlag=useEdgeFlag, localEdgeFlag=localEdgeFlag, eventTriggerFlag=eventTriggerFlag, soundLogFlag=soundLogFlag, soundLogDir=soundLogDir, useHistoryFlag=useHistoryFlag, msgLevel=msgLevel, mngServer=mngServer, remoteControlFlag=remoteControlFlag, senseHatFlag=senseHatFlag, logHost=logHost, fluentHost=fluentHost, fluentPort=fluentPort, proxies=proxies, version=__version__)

    ### Analyze audio signal by sound detector ###
    inStream = startRecording(deviceIndex, fsTest, chunkSize)
    while inStream.is_active():
        if msgLevel > 4:
            print('Wait for a audioEvent.')
            sys.stdout.flush()
        audioEvent.wait()

        # convert audio chunk into numpy.ndarray of float
        npChunk = np.frombuffer(chunk, dtype=np.int16).astype(np.float) / 2**15
        audioEvent.clear()

        ret = sd.analyze(npChunk, recTime-chunkTimeLen, syncMode=syncMode)
        sys.stdout.flush()

