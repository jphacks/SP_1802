#!/usr/bin/env python
# vim:fileencoding=utf-8

### Sound Input Device Tester ##################################################
__author__  = "Yoshihiro Kajiki <y-kajiki@ah.jp.nec.com>"
__version__ = "2.1"
__date__    = "Sep 29, 2018"

import sys
import pyaudio as pa
import threading
import numpy as np

# search sound recording device
def search_record_device():
    # pyaudio
    p_in = pa.PyAudio()
    bytes = 2
    py_format = p_in.get_format_from_width(bytes)
    fs = 0
    channels = 1
    recording_device = []

    # find input device
    print()
    print("device num: {0}".format(p_in.get_device_count()))
    print()
    for i in range(p_in.get_device_count()):
        maxInputChannels = p_in.get_device_info_by_index(i)['maxInputChannels']
        if maxInputChannels > 0 and maxInputChannels < 32:
            print('### Found!: index = %d, maxInputChannels = %d' % (i, maxInputChannels))
            print(p_in.get_device_info_by_index(i))
            print()
            fs = int(p_in.get_device_info_by_index(i)['defaultSampleRate'])
            recording_device.append((i, fs))
        else:
            print(p_in.get_device_info_by_index(i))
            print()

    chank_size = fs * 1

    num_recording_device = len(recording_device)
    if num_recording_device == 0:
        print("\nError! Can't find any usuable sound input device.")
        print("  Check your environment or try other computer.")
        sys.exit(1)
    print('Your computer has %d recording device(s).' % num_recording_device)

    return recording_device

# check sound recording device
def check_recording_device(recording_device):
    global chunk
    global audioEvent

    maxDevice = -1
    maxPower = 0
    for (idx, fs) in recording_device:

        print('Checking device #', idx)

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
        print('  power = ', power)

        # compair
        if power > maxPower:
            maxPower = power
            maxDevice = idx

    if maxDevice < 0:
        print("\nError! Can't find any usuable sound input device.")
        print("  All input device seems OFF.")
        print("  Check your environment or try other computer.")
        sys.exit(1)

    print("\nYour environment is OK.")
    print('  use_device_index = ', maxDevice)
    print('  SampleRate = ', fs)

    return maxDevice, fs

def startRecording(deviceIndex, fs, chunkSize):

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

    return inStream

def callback(in_data, frame_count, time_info, status):
    global chunk
    global recTime
    global audioEvent

    in_data = np.frombuffer(in_data, dtype=np.int16)
    chunk = in_data.tobytes()
    audioEvent.set()

    return (in_data, pa.paContinue)

if __name__ == "__main__":
    global chunk

    audioEvent = threading.Event()
    recording_device = search_record_device()
    check_recording_device(recording_device)

