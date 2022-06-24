import urllib.request
import imaplib
import time
import requests
from threading import Thread
import serial
from datetime import datetime
import smtplib
import numpy as np
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from matplotlib import pyplot as plt

#sending myself emails for commands and notifications
sourceEmail = 'YOUR_EMAIL'
destinationEmail = 'YOUR_EMAIL'

#channel id, url and APIs for thingspeak read/writes
CHANEL_ID = 'YOUR_CHANNEL_ID'
API_KEY_WRITE = 'YOUR_WRITE_API_KEY'
API_KEY_READ = 'YOUR_READ_API_KEY'
BASE_URL = 'https://api.thingspeak.com'

#this is for number of results to be read from the thingspeak API; default value 30
results = [30]

#urls for updating/reading data to/from thingspeak
WRITE_URL = '{}/update?api_key={}'.format(BASE_URL, API_KEY_WRITE)
READ_CHANNEL_URL = '{}/channels/{}/feeds.json?api_key={}'.format(BASE_URL, CHANEL_ID, API_KEY_READ)

#serial communication with arduino
ser = serial.Serial('SERIAL_PORT')
#this is to ensure the serial communication is open
if not ser.is_open:
    ser.open()

#number of motion detections when security mode is on
numberOfDetections = [0]

#data sample is for updating thingspeak; will contain 4 different pieces of data
dataSample = []

#these empty lists are for the data points and the timestamps from thingspeak
almDurationData = []
smDurationData = []
illuminationData = []
temperatureData = []
numberOfDetectionsData = []

almDurationTime = []
smDurationTime = []
temperatureTime = []
numberOfDetectionsTime = []

#this is a function to read, format and split data from thingspeak
def readTSData(READ_FIELD_URL,fieldNumber):
    resp = requests.get(READ_FIELD_URL)
    dataJson = resp.json()
    data = dataJson['feeds']
    dataList = []
    timeList = []
    for i in range(len(data)):
        dataPoint = data[i][fieldNumber]
        if(dataPoint != None):
            dataList.append(float(dataPoint))
            timeList.append(datetime.strftime(datetime.strptime(data[i]['created_at'],"%Y-%m-%dT%H:%M:%SZ"),'%H:%M:%S'))
    return dataList, timeList

#this function used for calculating average temperature/illumination per hour (in this case per minute)
def perHour(data):
    tempData = []
    perHourData = []
    for i in range(len(data)):
        tempData.append(data[i])
        if (i+1)%6 == 0:
            perHourData.append(float(sum(tempData)/len(tempData)))
            tempData.clear()
    if tempData:
        perHourData.append(float(sum(tempData)/len(tempData)))
    return perHourData

#this function is for calculating number of motions per hour (in this case per minute)
def perHourMotion(data):
    tempData = []
    perHourData = []
    for i in range(len(data)):
        tempData.append(data[i])
        if (i+1)%6==0:
            perHourData.append(tempData[-1]-tempData[0])
            tempData.clear()
    if tempData:
        perHourData.append(tempData[-1]-tempData[0])
    return perHourData

#this function is for sending an email report containing gathered data from Arduino
def sendReport():
    #reading all of the different fields
    READ_FIELD1_URL = '{}/channels/{}/fields/{}.json?api_key={}&results={}'.format(BASE_URL, CHANEL_ID, 1, API_KEY_READ,results[0])
    READ_FIELD2_URL = '{}/channels/{}/fields/{}.json?api_key={}&results={}'.format(BASE_URL, CHANEL_ID, 2, API_KEY_READ,results[0])
    READ_FIELD3_URL = '{}/channels/{}/fields/{}.json?api_key={}&results={}'.format(BASE_URL, CHANEL_ID, 3, API_KEY_READ,results[0])
    READ_FIELD4_URL = '{}/channels/{}/fields/{}.json?api_key={}&results={}'.format(BASE_URL, CHANEL_ID, 4, API_KEY_READ,results[0])
    READ_FIELD5_URL = '{}/channels/{}/fields/{}.json?api_key={}&results={}'.format(BASE_URL, CHANEL_ID, 5, API_KEY_READ,results[0])
    #putting all of the data into the data/timestamp lists
    almDurationData, almDurationTime = readTSData(READ_FIELD1_URL, 'field1')
    smDurationData, smDurationTime = readTSData(READ_FIELD2_URL, 'field2')
    illuminationData, illuminationTime = readTSData(READ_FIELD3_URL, 'field3')
    temperatureData, temperatureTime = readTSData(READ_FIELD4_URL, 'field4')
    numberOfDetectionsData, numberOfDetectionsTime = readTSData(READ_FIELD5_URL, 'field5')
    #prepairing values for the report
    averageIlluPerHour = perHour(illuminationData)
    averageTempPerHour = perHour(temperatureData)
    averageDetectionsPerHour = perHourMotion(numberOfDetectionsData)

    minTemperature = min(temperatureData)
    minIllumination = min(illuminationData)

    maxTemperature = max(temperatureData)
    maxIllumination = max(illuminationData)

    dailyAverageTemperature = sum(temperatureData)/len(temperatureData)
    dailyAverageIllumination = sum(illuminationData)/len(illuminationData)

    motionsDetected = numberOfDetectionsData[-1]
    almDurationTotal = almDurationData[-1]
    smDurationTotal = smDurationData[-1]
    #creating figures for representing gathered data
    plt.ioff()
    fig = plt.figure()
    plt.title('Temperature Data')
    plt.ylabel('Temperature °C')
    plt.plot(temperatureTime,temperatureData)
    #saving those figures into pngs, that will be later sent by email
    plt.savefig('fig_url')
    fig = plt.figure()
    plt.title('Illumination Data')
    plt.ylabel('Illuminaiton, Lux')
    plt.plot(illuminationTime, illuminationData)
    plt.savefig('fig_url')
    fig = plt.figure()
    plt.title('Number of Motions Detected per Hour')
    plt.ylabel('Detected Motions')
    plt.stem(averageDetectionsPerHour)
    plt.savefig('fig_url')
    #opening and reading images for the email report
    imageTemperature = open('fig_url', 'rb')
    msgTemperature = MIMEImage(imageTemperature.read())
    imageTemperature.close()
    imageIllumination = open('fig_url', 'rb')
    msgIllumination = MIMEImage(imageIllumination.read())
    imageIllumination.close()
    imageMotion = open('fig_url', 'rb')
    msgMotion = MIMEImage(imageMotion.read())
    imageMotion.close()
    #prepairing the email message using html
    message = MIMEMultipart()
    message['Subject'] = 'Report'
    message['From'] = sourceEmail
    message['To'] = destinationEmail

    message.preamble = '====================================================='
    htmlText = """\
        <html>
        <head></head>
        <body>
            <h1>Daily report on</h1>
            <h3>Temperature</h3>
            <p>
                Minimum temperature: <strong>{:.2f} °C</strong><br>
                Maximum temperature: <strong>{:.2f} °C</strong><br>
                Average temperature: <strong>{:.2f} °C</strong><br>
                Average temperature per minute: <strong>{}</strong><br>
            </p>
            <br><img src="cid:image1">
            <h3>Illumination</h3>
            <p>
                Minimum illumination: <strong>{:.2f} °C</strong><br>
                Maximum illumination: <strong>{:.2f} °C</strong><br>
                Average illumination: <strong>{:.2f} °C</strong><br>
                Average illumination per minute: <strong>{}</strong><br>
            </p>
            <br><img src="cid:image2">
            <p>
                <h3>Motions detected</h3>
                Motions detected: <strong>{}</strong><br>
                Motions detected per hour: <strong>{}</strong></p>
            <br><img src="cid:image3">
            <p>
                <h3>Auto-light and Home-secure modes</h3>
                Auto-light mode duration: <strong>{}</strong>.<br>
                Home-secure mode duration <strong>{}</strong>.
            </p>
        </body>
        </html>
    """.format(
        minTemperature, maxTemperature, dailyAverageTemperature, averageTempPerHour,
        minIllumination, maxIllumination, dailyAverageIllumination, averageIlluPerHour,
        motionsDetected, averageDetectionsPerHour,
        almDurationTotal,
        smDurationTotal
        )
    mimeText = MIMEText(htmlText, 'html')
    
    message.attach(mimeText)
    message.attach(msgTemperature)
    message.attach(msgIllumination)
    message.attach(msgMotion)
    #accessing and logging into the email address
    server = smtplib.SMTP('smtp.gmail.com',587)
    server.starttls()
    r = server.login(sourceEmail,'password')
    r = server.sendmail(sourceEmail,destinationEmail,message.as_string())
    server.quit()

#this function is for sending data to thingspeak
#the values are in the order that they are sent in
def sendData(almDuration,smDuration,illumination,temperature,numOfDetections):
    urllib.request.urlopen("{}&field1={}&field2={}&field3={}&field4={}&field5={}".format(WRITE_URL, almDuration, smDuration, illumination, temperature, numOfDetections))

#this will run as a background thread to read commands sent by email
def checkMail(email, ser):
    email.select('inbox')
    while True:
        #checking if any of the emails with specific subjects are unseen/unread
        #if they are, a command is sent to the Arduino
        retcode, responseTurnOnLight = email.search(None, '(SUBJECT "LED_ON" UNSEEN)')
        retcode, responseTurnOffLight = email.search(None, '(SUBJECT "LED_OFF" UNSEEN)')
        retcode, responseTurnOnHeating = email.search(None, '(SUBJECT "HEAT_ON" UNSEEN)')
        retcode, responseTurnOffHeating = email.search(None, '(SUBJECT "HEAT_OFF" UNSEEN)')
        retcode, responseTurnOnCooling = email.search(None, '(SUBJECT "COOLING_ON" UNSEEN)')
        retcode, responseTurnOffCooling = email.search(None, '(SUBJECT "COOLING_OFF" UNSEEN)')
        retcode, responseTurnOnAutoLight = email.search(None, '(SUBJECT "AUTO_LIGHT_ON" UNSEEN)')
        retcode, responseTurnOffAutoLight = email.search(None, '(SUBJECT "AUTO_LIGHT_OFF" UNSEEN)')
        retcode, responseTurnOnSecureMode = email.search(None, '(SUBJECT "SECURE_MODE_ON" UNSEEN)')
        retcode, responseTurnOffSecureMode = email.search(None, '(SUBJECT "SECURE_MODE_OFF" UNSEEN)')
        retcode, responseReport = email.search(None, '(SUBJECT "SEND_REPORT" UNSEEN)')
        #the response is used to flag the email as seen, so that it's not read again
        if len(responseTurnOnLight[0]) > 0:
            command = "LED_ON"
            #the command is encoded so that it can be read by the Arduino
            ser.write(command.encode('ascii'))
            emailIds = responseTurnOnLight[0].split()
            for id in emailIds:
                email.store(id, '+FLAGS', '\\Seen')
        
        if len(responseTurnOffLight[0]) > 0:
            command = "LED_OFF"
            ser.write(command.encode('ascii'))
            emailIds = responseTurnOffLight[0].split()
            for id in emailIds:
                email.store(id, '+FLAGS', '\\Seen')
        
        if len(responseTurnOnHeating[0]) > 0:
            command = "HEAT_ON"
            ser.write(command.encode('ascii'))
            emailIds = responseTurnOnHeating[0].split()
            for id in emailIds:
                email.store(id, '+FLAGS', '\\Seen')
        
        if len(responseTurnOffHeating[0]) > 0:
            command = "HEAT_OFF"
            ser.write(command.encode('ascii'))
            emailIds = responseTurnOffHeating[0].split()
            for id in emailIds:
                email.store(id, '+FLAGS', '\\Seen')

        if len(responseTurnOnCooling[0]) > 0:
            command = "COOLING_ON"
            ser.write(command.encode('ascii'))
            emailIds = responseTurnOnCooling[0].split()
            for id in emailIds:
                email.store(id, '+FLAGS', '\\Seen')
        
        if len(responseTurnOffCooling[0]) > 0:
            command = "COOLING_OFF"
            ser.write(command.encode('ascii'))
            emailIds = responseTurnOffCooling[0].split()
            for id in emailIds:
                email.store(id, '+FLAGS', '\\Seen')

        if len(responseTurnOnAutoLight[0]) > 0:
            command = "AUTO_LIGHT_ON"
            ser.write(command.encode('ascii'))
            emailIds = responseTurnOnAutoLight[0].split()
            for id in emailIds:
                email.store(id, '+FLAGS', '\\Seen')

        if len(responseTurnOffAutoLight[0]) > 0:
            command = "AUTO_LIGHT_OFF"
            ser.write(command.encode('ascii'))
            emailIds = responseTurnOffAutoLight[0].split()
            for id in emailIds:
                email.store(id, '+FLAGS', '\\Seen')

        if len(responseTurnOnSecureMode[0]) > 0:
            command = "SECURE_MODE_ON"
            ser.write(command.encode('ascii'))
            emailIds = responseTurnOnSecureMode[0].split()
            for id in emailIds:
                email.store(id, '+FLAGS', '\\Seen')
        
        if len(responseTurnOffSecureMode[0]) > 0:
            command = "SECURE_MODE_OFF"
            ser.write(command.encode('ascii'))
            emailIds = responseTurnOffSecureMode[0].split()
            for id in emailIds:
                email.store(id, '+FLAGS', '\\Seen')
        
        #this is the only command that is different, in that no command is sent to the Arduino
        if len(responseReport[0]) > 0:
            numResults = (datetime.now()-now[0]).total_seconds()/10
            results[0] = int(numResults)
            if(results[0]>5):
                sendReport()
            else:
                print('Cannot send report, not enough data has been collected. Please try again later')
            emailIds = responseReport[0].split()
            for id in emailIds:
                email.store(id, '+FLAGS', '\\Seen')
        time.sleep(3)

#receive will run as a background thread to always listen to Arduino messages being sent
def receive(ser):
    while True:
        if ser.in_waiting > 0:
            message = ser.readline()
            message = message.decode('utf-8').strip()
            print(message)
            processMessage(message)
        time.sleep(0.1)

#this function processes the messages that have been received from the Arduino microcontroller
def processMessage(message):
    left = message.partition('_')[0]
    right = message.partition('_')[2]
    #if a data sample has been collected, it is sent to thingspeak
    if(len(dataSample)==4):
        sendData(dataSample[0],dataSample[1],dataSample[2],dataSample[3],numberOfDetections[0])
        dataSample.clear()
    #if the message is data, then it is processed by one function
    if(left=='DATA'):
        processData(right)
    #if the message is a notification, then it is processed by another function
    if(left=='NOTI'):
        processNotification(right)

#there are different types of data that are read from the microcontroller
#the order of execution is important here, as it will determine the order of the data in the dataSample list
def processData(message):
    dataType = message.partition('_')[0]
    data = message.partition('_')[2]
    if(dataType=='DURATION'):
        if(data.partition('_')[0]=='ALM'):
            dataSample.append(int(data.partition('_')[2]))
        else:
            dataSample.append(int(data.partition('_')[2]))
    if(dataType=='ILLU'):
        dataSample.append(float(data))
    if(dataType=='TEMP'):
        dataSample.append(float(data))

#this is a function for sending notifications to the email
#similarly to sending a report, you access the email address and then close the server that had accessed it.
def sendNotification(notificationMessage):
    notification = MIMEMultipart()
    notification['Subject'] = notificationMessage
    notification['From'] = sourceEmail
    notification['To'] = destinationEmail
    server = smtplib.SMTP('smtp.gmail.com',587)
    server.starttls()
    r = server.login(sourceEmail, 'password')
    r = server.sendmail(sourceEmail, destinationEmail, notification.as_string())
    server.quit()

#this is processing notifications from the Arduino microcontroller
#based on the notificatino sent by the Arduino, a different message will be the subject of the email
def processNotification(message):
    if(message.partition('_')[0]=='MOTION'):
        if numberOfDetections:
            numberOfDetections[0]+=1
        else:
            numberOfDetections.append(1)
        sendNotification('Motion detected')
    if(message=='COOLING_ON'):
        sendNotification('Cooling has been turned on')
    if(message=='COOLING_OFF'):
        sendNotification('Cooling has been turned off')
    if(message=='HEATING_ON'):
        sendNotification('Heating has been turned on')
    if(message=='HEATING_OFF'):
        sendNotification('Heating has been turned off')
    if(message=='LED_WAS_ON'):
        sendNotification('The LED was already on')
    if(message=='LED_IS_ON'):
        sendNotification('The LED has been turned on')
    if(message=='LED_WAS_OFF'):
        sendNotification('The LED was already off')
    if(message=='LED_IS_OFF'):
        sendNotification('The LED has been turned off')
    if(message=='LED_ON_ALM'):
        sendNotification('Auto-light mode has turned the LED on')
    if(message=='LED_OFF_ALM'):
        sendNotification('Auto-light mode has turned the LED off')
    if(message=='ALM_ON'):
        sendNotification('Auto-light mode has been turned on')
    if(message=='SM_ON'):
        sendNotification('Home-security mode has been turned on')
    if(message=='ALM_OFF'):
        sendNotification('Auto-light mode has been turned off')
    if(message=='SM_OFF'):
        sendNotification('Home-security mode has been turned off')
    if(message=='HEATER_WAS_ON'):
        sendNotification('Heater was already on')
    if(message=='HEATER_IS_ON'):
        sendNotification('Heater has been turned on')
    if(message=='HEATER_WAS_OFF'):
        sendNotification('Heater was already off')
    if(message=='HEATER_IS_OFF'):
        sendNotification('Heater has been turned off')
    if(message=='COOLING_WAS_ON'):
        sendNotification('Cooling was already on')
    if(message=='COOLING_IS_ON'):
        sendNotification('Cooling has been turned on')
    if(message=='COOLING_WAS_OFF'):
        sendNotification('Cooling was already off')
    if(message=='COOLING_IS_OFF'):
        sendNotification('Cooling has been turned off')
    
#this is starting the thread of receiving data from the Arduino
receivingThread  = Thread(target=receive, args=(ser, ))
receivingThread.start()

email = imaplib.IMAP4_SSL('imap.gmail.com')
email.login('email', 'password')

#this is the thread of checking emails for commands
checkEmailThread  = Thread(target=checkMail, args=(email, ser, ))
checkEmailThread.start()

#this will help determine if enough time has passed for sending a daily (5-minute in this case) report
now = [datetime.now()]

while True:
    if (datetime.now()-now[0]).total_seconds()/60>=5:
        numResults = (datetime.now()-now[0]).total_seconds()/10
        results[0] = int(numResults)
        now[0] = datetime.now()
        sendReport()
        print('report sent')
    time.sleep(10)
