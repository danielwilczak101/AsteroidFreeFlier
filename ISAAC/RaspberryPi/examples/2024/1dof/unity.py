import asyncio
import socket
from adafruit_bno055 import BNO055_I2C
from board import SCL, SDA
from busio import I2C
from contextlib import asynccontextmanager
import math


def quaternion_to_euler(w, x, y, z):
    # Convert quaternion to Euler angles (roll, pitch, yaw)
    t0 = +2.0 * (w * x + y * z)
    t1 = +1.0 - 2.0 * (x * x + y * y)
    roll = math.atan2(t0, t1)

    t2 = +2.0 * (w * y - z * x)
    t2 = +1.0 if t2 > +1.0 else t2
    t2 = -1.0 if t2 < -1.0 else t2
    pitch = math.asin(t2)

    t3 = +2.0 * (w * z + x * y)
    t4 = +1.0 - 2.0 * (y * y + z * z)
    yaw = math.atan2(t3, t4)

    return roll, pitch, yaw  # in radians


# TCP/IP Client Setup
def setup_tcp_client(ip, port):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client.connect((ip, port))
        print(f"Successfully connected to server at {ip}:{port}")
    except Exception as e:
        print(f"Failed to connect to server: {e}")
        raise
    return client

# Read IMU data and send it over TCP
async def read_imu_data(stop: asyncio.Event, tcp_client):
    # Setup for BNO055 sensor
    i2c = I2C(SCL, SDA)
    sensor = BNO055_I2C(i2c)

    while not stop.is_set():
        quat = sensor.quaternion  # Read quaternion from IMU
        if quat:
            # Convert quaternion to Euler angles
            euler_angles = quaternion_to_euler(quat[0], quat[1], quat[2], quat[3])
            euler_data_str = f"Roll: {math.degrees(euler_angles[0]):.2f}, Pitch: {math.degrees(euler_angles[1]):.2f}, Yaw: {math.degrees(euler_angles[2]):.2f}\n"
            print(euler_data_str)
            # Ensure the order is quat_w, quat_x, quat_y, quat_z
            # Adjust according to actual order from the sensor
            data_str = f"{quat[0]},{quat[1]},{quat[2]},{quat[3]}\n"  # Append a newline to indicate the end of this quaternion message
            tcp_client.send(data_str.encode('utf-8'))
            print(f"Sent data: {data_str.strip()}")
        await asyncio.sleep(0.1)  # Sleep to limit the rate of data sending

# Main asynchronous function to control the application
async def main():
    stop_event = asyncio.Event()
    tcp_client = setup_tcp_client('192.168.1.12', 25001)  # Set the IP and port
    try:
        imu_task = asyncio.create_task(read_imu_data(stop_event, tcp_client))
        await stop_event.wait()  # This will pause here until stop_event is set
    finally:
        tcp_client.close()

asyncio.run(main())