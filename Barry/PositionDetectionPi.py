import cv2
import numpy as np
import matplotlib.pyplot as plt
import socket
import struct
import time
from picamera2 import Picamera2

# set IP address and port number
UDP_IP = '127.0.0.1'
UDP_PORT = 30002

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP

coefficients = ((1, 1, 1), (1, 1, 1), (1, 1, 1), (1, 1, 1), (1, 1, 1))


def find_closest_value(x, i):
    # extract coefficients for ith quadratic equation
    a, b, c = coefficients[i]

    # compute y values for a range of x values
    x_range = np.linspace(0, 30, 100)
    y_values = a * x_range ** 2 + b * x_range + c

    # find index of closest y value to input x
    closest_index = np.abs(y_values - x).argmin()

    # return x value at closest index
    return int(x_range[closest_index] / 3)


def encoder(factor, positions):
    encoded_message = positions[0]
    encoded_message = encoded_message * factor + positions[1]
    encoded_message = encoded_message * factor + positions[2]
    encoded_message = encoded_message * factor + positions[3]
    encoded_message = encoded_message * factor + positions[4]
    print(encoded_message)
    encoded_message = struct.pack('>d', encoded_message)
    print(positions)
    sock.sendto(encoded_message, (UDP_IP, UDP_PORT))


class App:
    def __init__(self):
        # create matrix of blocks
        self.blocks = np.zeros((10, 5))

    def light_up_column(self, finger_num, row_num):
        for i in range(10, 0, -1):
            if i >= 11 - row_num:
                self.blocks[i - 1][finger_num - 1] = 1
            else:
                self.blocks[i - 1][finger_num - 1] = 0

    def update_plot(self):
        # create plot of matrix of blocks
        plt.clf()
        plt.imshow(self.blocks, cmap='Oranges', vmin=0, vmax=1, aspect='auto')
        plt.xticks(range(5), ["Thumb", "Index", "Middle", "Ring", "Pinky"])
        plt.yticks(range(10), [""] * 10)
        plt.xlabel("Fingers")
        plt.ylabel("Positions")
        plt.title("Finger Matrix")

        # add vertical lines between columns
        for i in range(1, 5):
            plt.axvline(x=i - 0.5, color='black', linewidth=1)

        plt.draw()
        plt.pause(0.001)


# define 5 HUE color ranges
color_ranges = [
    ((80, 70, 50), (100, 255, 255)),  # cyan
    ((40, 70, 50), (80, 255, 255)),   # green
    ((10, 70, 50), (15, 255, 255)),   # orange
    ((20, 70, 50), (40, 255, 255)),   # yellow
    ((140, 70, 50), (180, 255, 255))  # pink
]

# set up camera capture
picam2 = Picamera2()
camera_config = picam2.create_preview_configuration()
picam2.configure(camera_config)
picam2.start()

# allow the camera to warm up
time.sleep(0.1)

# create matplotlib app and run event loop
app = App()
positions = [0, 0, 0, 0, 0]

while (True):
    # capture frame from camera
    frame = picam2.capture_array("main")

    # segment image based on HUE color ranges
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    masks = [cv2.inRange(hsv, c[0], c[1]) for c in color_ranges]

    # find contours in each color segment
    contours = [cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2] for mask in masks]

    # find largest rectangle in each color segment
    rects = []
    for i, contour in enumerate(contours):
        if len(contour) > 0:
            # get largest contour and compute bounding rectangle
            max_contour = max(contour, key=cv2.contourArea)
            rect = cv2.boundingRect(max_contour)
            rects.append((i, rect[0], rect[1], rect[2], rect[3]))

            # get color range for this finger
            color_range = color_ranges[i]

            # draw rectangle on frame with color from color range
            color_bgr = [(255, 255, 0), (0, 255, 0), (0, 140, 255), (0, 255, 255), (203, 192, 255)] [i]
            cv2.rectangle(frame, (rect[0], rect[1]), (rect[0]+rect[2], rect[1]+rect[3]), color_bgr, 2)
        else:
            rects.append((i, 0, 0, 0, 0))

        # light up matrix blocks based on largest rectangle size
        pos = find_closest_value(rect[2], i)
        app.light_up_column(i+1, pos)
        positions[i] = pos
        #app.light_up_column(i+1, random.randint(0, 10))

    # display frame with bounding box
    cv2.imshow("frame", frame)
    encoder(11, positions)

    # update matplotlib plot with matrix of blocks
    app.update_plot()
