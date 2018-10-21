#!/usr/bin/env.python
#/-*-/coding:/utf-8/-*-
# socket server making

import socket
import requests
import serial
import time
import os
import picamera
from time import sleep
import pyocr
from time import sleep
from PIL import Image
import sys
sys.path.append('/path/to/dir')

import pyocr
import pyocr.builders

postFlg = 0
txt = 'Posting notice!'

def ArduinoSensing():
    global postFlg
    print('Light value sesing via CdS sensor ->start!')
    print("CallTest" + str(postFlg))
    ser = serial.Serial('/dev/ttyACM0', 9600)
    time.sleep(2)
    openFlg = 0
	
    while (postFlg != 1):
        data = ser.readline()#Loading the data from Arduino
        data2 = int(data)#Convert int
	print('Light value:' + str(data2))
	if data2 == 2000:
		print('Status:Cover of post open')
		time.sleep(1)
		openFlg = 1
	elif data2 == 1000:
		print('Status:Cover of post closed')
		time.sleep(1)
		print(str(openFlg))
		if openFlg == 1:
                    postFlg = 1
                    print('Huzai-Tsuuti submitted into the post')
    
def Capture() :
    print('Camera start')
    sleep(2)
    ####Camera Test###
    camera = picamera.PiCamera()
    camera.resolution = (1024,1024)#max size is 1024 x1024 of LINE Notify
    camera.capture('img/image.jpeg')
    sleep(1)
    
def OCR() :
    global txt
    print('OCR start')
    ###OCR###
    tools = pyocr.get_available_tools()
    if len(tools) == 0:
        #print("No OCR tool found")
        sys.exit(1)
    tool = tools[0]
    #print("Will use tool '%s'" % (tool.get_name()))

    langs = tool.get_available_languages()
    #print("Available languages: %s" % ", ".join(langs))

    txt = tool.image_to_string(
        Image.open('img/huzai_02.jpeg'),
        lang='jpn',
        builder=pyocr.builders.TextBuilder()
    )
    print(txt)
        
    
def LineNotify():
    print('Notification to smart phone via LINE')
    global txt
    global postFlg
    postFlg = 0
    url = "https://notify-api.line.me/api/notify"
    token = "XXX"
    headers = {"Authorization" : "Bearer "+ token}
    message =  txt
    payload = {"message" :  message}
    #files = {"imageFullsize" : open("img/image.jpeg", "rb")}
    files = {"imageFile" : open("img/image.jpeg", "rb")}#huzai_02.jpeg
    #r = requests.post(url ,headers = headers ,params=payload )
    r = requests.post(url ,headers = headers ,params=payload ,files=files)
    print("LINE")
    print("LineNotify" + str(postFlg))
    
    
def main():
    print('Server start')
    # AF = IPv4
    # In TCP/IP case, using SOCArduinoSensingK_STREAM
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # IPaddress and PORT
    s.bind(('172.20.10.7', 50007))
    # 1 Connection
    s.listen(1)
    # Waiting until connection
    conn, addr = s.accept()
    
    if conn is None:
        print('conn is None')
    print('Connected by'+str(addr))
    while True:
        data = conn.recv(1024)
        print('data: {}, addr: {}'.format(data, addr))
        if data is not None:
            #Data recieving from Rasberry Pi baesd osn NEC API
            ArduinoSensing()

        if postFlg == 1:
            Capture()
            #OCR()
            #Notification to smart phone via LINE
            LineNotify()
            break
    conn.close()
    s.close()
    
if __name__== '__main__':
    main()
    
