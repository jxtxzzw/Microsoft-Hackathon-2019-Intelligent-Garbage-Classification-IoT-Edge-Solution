# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for
# full license information.

import time
import sys
import os
import requests
import json

import iothub_client
# pylint: disable=E0611
from iothub_client import IoTHubModuleClient, IoTHubClientError, IoTHubTransportProvider
from iothub_client import IoTHubMessage, IoTHubMessageDispositionResult, IoTHubError
# pylint: disable=E0401

import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)

WHITE = 5
YELLOW = 6
BLUE = 13
GREEN = 19
RED = 26

GPIO.setup(WHITE, GPIO.OUT)
GPIO.setup(YELLOW, GPIO.OUT)
GPIO.setup(BLUE, GPIO.OUT)
GPIO.setup(GREEN, GPIO.OUT)
GPIO.setup(RED, GPIO.OUT)

def show_result_led(classify):
    if classify == '干垃圾':
        light = YELLOW
    elif classify == '湿垃圾':
        light = BLUE
    elif classify == '可回收垃圾':
        light = GREEN
    elif classify == '有害垃圾':
        light = RED
    else:
        light = WHITE
    switch(light)

def switch(light):
    GPIO.output(RED, RED == light)
    GPIO.output(BLUE, BLUE == light)
    GPIO.output(GREEN, GREEN == light)
    GPIO.output(YELLOW, YELLOW == light)
    GPIO.output(WHITE, WHITE == light)

# all lights on
def all_lights():
    GPIO.output(RED, True)
    GPIO.output(BLUE, True)
    GPIO.output(GREEN, True)
    GPIO.output(YELLOW, True)
    GPIO.output(WHITE, True)

# all lights off
def no_lights():
    GPIO.output(RED, False)
    GPIO.output(BLUE, False)
    GPIO.output(GREEN, False)
    GPIO.output(YELLOW, False)
    GPIO.output(WHITE, False)

# status indicator: white light
def processing():
    switch(WHITE)


recoverableItems = ['键盘', '手机', '笔记本电脑', '鼠标', '瓶']
hazardousItems = ['电池']
householdItems = ['瓜', '西瓜', '香蕉']
residualItems = ['眼镜', '食品包装', '笔', '纸巾']

# messageTimeout - the maximum time in milliseconds until a message times out.
# The timeout period starts at IoTHubModuleClient.send_event_async.
MESSAGE_TIMEOUT = 10000

# Choose HTTP, AMQP or MQTT as transport protocol.  
PROTOCOL = IoTHubTransportProvider.MQTT

# global counters
SEND_CALLBACKS = 0

# Send a message to IoT Hub
# Route output1 to $upstream in deployment.template.json
def send_to_hub(strMessage):
    message = IoTHubMessage(bytearray(strMessage, 'utf8'))
    hubManager.send_event_to_output("output1", message, 0)

# Callback received when the message that we send to IoT Hub is processed.
def send_confirmation_callback(message, result, user_context):
    global SEND_CALLBACKS
    SEND_CALLBACKS += 1
    print ( "Confirmation received for message with result = %s" % result )
    print ( "   Total calls confirmed: %d \n" % SEND_CALLBACKS )

# Send an image to the image classifying server
# Return the JSON response from the server with the prediction result
def sendFrameForProcessing(imagePath, imageProcessingEndpoint):
    headers = {'Content-Type': 'application/octet-stream'}

    with open(imagePath, mode="rb") as test_image:
        try:
            processing()
            response = requests.post(imageProcessingEndpoint, headers = headers, data = test_image)
            print("Response from classification service: (" + str(response.status_code) + ") " + json.dumps(response.json()) + "\n")
            total = len(response.json()['predictions'])
            if total > 0: 
                max_p = response.json()['predictions'][0]['probability']
                obj = response.json()['predictions'][0]['tagName']
                for i in range(total):
                    if response.json()['predictions'][i]['probability'] > max_p:
                        max = response.json()['predictions'][i]['probability']
                        obj = response.json()['predictions'][i]['tagName']
                print("Object = " + obj)
                if (obj in recoverableItems):
                    show_result_led('可回收垃圾')
                elif (obj in hazardousItems):
                    show_result_led('有害垃圾')
                elif (obj in householdItems):
                    show_result_led('湿垃圾')
                elif (obj in residualItems):
                    show_result_led('干垃圾')
                else:
                    # The detected tag name belongs to no category
                    all_lights()
            else:
                # Prediction list is empty
                # which means the image file is damaged, or it failed to classify the image, or something wrong with the transmission
                all_lights()
        except Exception as e:
            print(e)
            print("Response from classification service: (" + str(response.status_code))
            all_lights()

    return json.dumps(response.json())

class HubManager(object):
    def __init__(self, protocol, message_timeout):
        self.client_protocol = protocol
        self.client = IoTHubModuleClient()
        self.client.create_from_environment(protocol)
        # set the time until a message times out
        self.client.set_option("messageTimeout", message_timeout)

    # Sends a message to an output queue, to be routed by IoT Edge hub. 
    def send_event_to_output(self, outputQueueName, event, send_context):
        self.client.send_event_async(
            outputQueueName, event, send_confirmation_callback, send_context)



def main(imagePath, imageProcessingEndpoint):
    try:
        print ( "Simulated camera module for Azure IoT Edge. Press Ctrl-C to exit." )

        try:
            global hubManager 
            hubManager = HubManager(PROTOCOL, MESSAGE_TIMEOUT)
        except IoTHubError as iothub_error:
            print ( "Unexpected error %s from IoTHub" % iothub_error )
            return

        print ( "The sample is now sending images for processing and will indefinitely.")

        while True:
            os.system("fswebcam -r 1280x720 --no-banner test_image.jpg")
            classification = sendFrameForProcessing(imagePath, imageProcessingEndpoint)
            send_to_hub(classification)
            time.sleep(1)

    except KeyboardInterrupt:
        print ( "IoT Edge module sample stopped" )

if __name__ == '__main__':
    try:
        # Retrieve the image location and image classifying server endpoint from container environment
        IMAGE_PATH = os.getenv('IMAGE_PATH', "")
        IMAGE_PROCESSING_ENDPOINT = os.getenv('IMAGE_PROCESSING_ENDPOINT', "")
    except ValueError as error:
        print ( error )
        sys.exit(1)

    if ((IMAGE_PATH and IMAGE_PROCESSING_ENDPOINT) != ""):
        main(IMAGE_PATH, IMAGE_PROCESSING_ENDPOINT)
    else: 
        print ( "Error: Image path or image-processing endpoint missing" )