#!/usr/bin/env.python
#/-*-/coding:/utf-8/-*-
# socket server making

import socket
import requests
import serial
import time
import os
postFlg = 0

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
                    print('Huzai-Tsuuti submitted')
    
def LineNotify():
    print('Notification to smart phone via LINE')
    global postFlg
    postFlg = 0
    url = "https://notify-api.line.me/api/notify"

    token = "XXX"
    headers = {"Authorization" : "Bearer "+ token}
    message =  'FuzaiTsuuti'
    payload = {"message" :  message}
    r = requests.post(url ,headers = headers ,params=payload)
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
            #Notification to smart phone via LINE
            LineNotify()
        
if __name__== '__main__':
    main()
    
