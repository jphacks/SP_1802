#!/usr/bin/env.python
#/-*-/coding:/utf-8/-*-
# socket server making

import sys
import socket
import requests
import serial
import json
import time
import os
import picamera
import pyocr
import cv2
import numpy
from PIL import Image
from time import sleep
sys.path.append('/path/to/dir')

import pyocr
import pyocr.builders

postFlg = 0
txt = 'Posting notice!'
ip = 'xxx.xxx.xxx.xxx'
nec_id = xxxx

def ArduinoSensing():
    global postFlg
    print('distance sensing via Sonic wave sensor ->start!')
    print("CallTest" + str(postFlg))
    ser = serial.Serial('/dev/ttyACM0', 9600)
    time.sleep(2)
    openFlg = 0
    while (postFlg != 1):
        data = ser.read()
        #data = ser.readline()#Loading the data from Arduino
        print(data)
        #data2 = int(data)
        #data2 = int(data.replace(',', ''))
        #print(type(data))
        #data2 = int(data).rstrip().split(',')[:-1]#Convert int
        #print('Distance flag:' + str(data))
        if data == 'O':
            print('Status:Cover of post open')
            time.sleep(0.2)
            openFlg = 1
            #elif data == 'C':
        else:
	    print('Status:Cover of post closed')
	    time.sleep(0.2)
	    #print(str(openFlg))
	    if openFlg == 1:
	        postFlg = 1
                print('Huzai-Tsuuti submitted into the post')
        #else:
        #    print('Error')
def Capture() :
    print('Camera start')
    sleep(2)
    camera = picamera.PiCamera()
    #camera.hflip = True
    #camera.vflip = True
    camera.resolution = (1024,1024)#max size is 1024 x1024 of LINE Notify
    camera.capture('img/test.jpeg')
    #Rotation of the captured image
    img_rotation = cv2.imread('img/test.jpeg')
    asld = img_rotation.transpose(1,0,2)[::-1]
    cv2.imwrite('img/test.jpeg', asld)

    sleep(1)

def Crop() :
    print("Crop start")
    
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
        Image.open('img/test.jpeg'),
        lang='jpn',
        builder=pyocr.builders.TextBuilder()
    )
    print(txt)
        
    
def LineNotify_NEC():
    print("Image recognition via NEC image Engine")
    # Post Search Request
    imgFile = 'img/test.jpeg'
    #imgFile = 'img/test.jpeg'
    nec_files_path = {'image': open(imgFile, "rb")}
    print(nec_files_path)
    #url = "https://www3.arche.blue/api/searcher/v1/%d/search" % gid
    url = 'https://www3.arche.blue/mvp5/v1/%d/search' % nec_id
    print(url)
    res = requests.post(url, files = nec_files_path)
    
    # Get Response
    if res.status_code == 200:
        print("success NEC")
        print("ID:" + str(res.json()[0]['id']))
        #return res.json()[0]['id']
        #print (json.dumps(res.json(), indent=4))
    else:
        print (res.text)
    print('Notification to smart phone via LINE')
    global txt
    global postFlg
    postFlg = 0
    url = "https://notify-api.line.me/api/notify"
    token = "xxxxxxxxx"
    headers = {"Authorization" : "Bearer "+ token}
    
    delivery_corp = res.json()[0]['associatedInfo'][0]
    print(delivery_corp)
    delivery_num = res.json()[0]['associatedInfo'][1]
    print(delivery_num)
    delivery_url = res.json()[0]['associatedInfo'][2]
    print(delivery_url)
    
    message =  delivery_corp+'\n'+delivery_num+'\n'+delivery_url
    payload = {"message" :  message}
    #files = {"imageFullsize" : open("img/image.jpeg", "rb")}
    files = {"imageFile" : open("img/test.jpeg", "rb")}#huzai_02.jpeg
    #r = requests.post(url ,headers = headers ,params=payload )
    r = requests.post(url ,headers = headers ,params=payload ,files=files)
    print("LINE")
    #print("LineNotify" + str(postFlg))
    
    
def main():
    print('Server start')
    # AF = IPv4
    # In TCP/IP case, using SOCArduinoSensingK_STREAM
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # IPaddress and PORT
    s.bind((ip, 50007))
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
            #Crop()
            #OCR()
            LineNotify_NEC()
            print('END')
            break
    conn.close()
    s.close()
    
if __name__== '__main__':
    main()
   
