#Authur: Justin Hartland
#Purpose: To implement a PID controller to achieve CubeSat 1DoF stability

import asyncio
import time
from math import atan2, degrees
import board
import adafruit_mpu6050
import moteus

i2c = board.I2C()  # uses board.SCL and board.SDA
sensor = adafruit_mpu6050.MPU6050(i2c)

# Given a point (x, y) return the angle of that point relative to x axis.
# Returns: angle in degrees

def vector_2_degrees(x, y):
    angle = degrees(atan2(y, x))
    if angle < 0:
        angle += 360
    return angle

# Given an accelerometer sensor object return the inclination angles of X/Z and Y/Z
# Returns: tuple containing the two angles in degrees

def get_inclination(_sensor):
    x, y, z = _sensor.acceleration
    return vector_2_degrees(y, z)

def getAngle(flag, initialAngle):
    angleOfCubeSat = get_inclination(sensor)
    if flag == 1:
        initialAngle = angleOfCubeSat
        flag = 0
    print("YZ angle = {:6.2f}deg".format(
        angleOfCubeSat - initialAngle))
    return angleOfCubeSat, flag, initialAngle
        

async def main():
    c = moteus.Controller()
    await c.set_stop()

    flag = 1
    initialAngle = 0

    desiredAngle = -55

    while True:
        cubeSatAngle, flag, initialAngle = getAngle(flag, initialAngle)
        error = (desiredAngle - cubeSatAngle)
        if error < 0:
            state = await c.set_position(velocity = 5, accel_limit = 100, query=True)
            await asyncio.sleep(0.01)
        else:
            state = await c.set_position(velocity = -5, accel_limit = 100, query=True)
            await asyncio.sleep(0.01)



if __name__ == '__main__':
    asyncio.run(main())