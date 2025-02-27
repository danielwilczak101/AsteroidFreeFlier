#!/usr/bin/python
#The MIT License (MIT)
#
#Copyright (c) 2015 Stephen P. Smith
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in all
#copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#SOFTWARE.

import time, math
import RPi.GPIO as GPIO

class max31856(object):
	"""Read Temperature on the Raspberry PI from the MAX31856 chip using GPIO
	   Any pins can be used for CS (chip select), MISO, MOSI and CLK
	"""

	def __init__(self, csPin = 8, misoPin = 9, mosiPin = 10, clkPin = 11):
		self.csPin = csPin
		self.misoPin = misoPin
		self.mosiPin = mosiPin
		self.clkPin = clkPin
		self.setupGPIO()
		#
		# Config Register 2
		# ------------------
		# bit 7: Reserved                                -> 0 
		# bit 6: Averaging Mode 1 Sample                 -> 0 (default)
		# bit 5: Averaging Mode 1 Sample                 -> 0 (default)
		# bit 4: Averaging Mode 1 Sample                 -> 0 (default)
		# bit 3: Thermocouple Type -> K Type (default)   -> 0 (default)
		# bit 2: Thermocouple Type -> K Type (default)   -> 0 (default)
		# bit 1: Thermocouple Type -> K Type (default)   -> 1 (default)
		# bit 0: Thermocouple Type -> K Type (default)   -> 1 (default)
		#
		#Uncomment one of the following to select thermocouple type
		#self.writeRegister(1, 0x00) #for B Type
		#self.writeRegister(1, 0x01) #for E Type
		#self.writeRegister(1, 0x02) #for J Type
		self.writeRegister(1, 0x03) #for K Type
		#self.writeRegister(1, 0x04) #for N Type
		#self.writeRegister(1, 0x05) #for R Type
		#self.writeRegister(1, 0x06) #for S Type
		#self.writeRegister(1, 0x07) #for T Type
		
	def setupGPIO(self):
		GPIO.setwarnings(False)
		GPIO.setmode(GPIO.BCM)
		GPIO.setup(self.csPin, GPIO.OUT)
		GPIO.setup(self.misoPin, GPIO.IN)
		GPIO.setup(self.mosiPin, GPIO.OUT)
		GPIO.setup(self.clkPin, GPIO.OUT)

		GPIO.output(self.csPin, GPIO.HIGH)
		GPIO.output(self.clkPin, GPIO.LOW)
		GPIO.output(self.mosiPin, GPIO.LOW)	
	
	def readThermocoupleTemp(self):
		self.requestTempConv()

		# read 4 registers starting with register 12
		out = self.readRegisters(0x0c, 4) 
		
		[tc_highByte, tc_middleByte, tc_lowByte] = [out[0], out[1], out[2]]	
		temp = ((tc_highByte << 16) | (tc_middleByte << 8) | tc_lowByte) >> 5
		
		if (tc_highByte & 0x80):
			temp -= 0x80000
		
		temp_C = temp * 0.0078125
		
		fault = out[3]
		
		if ((fault & 0x80) != 0):
			raise FaultError("Cold Junction Out-of-Range")
		if ((fault & 0x40) != 0):
			raise FaultError("Thermocouple Out-of-Range")
		if ((fault & 0x20) != 0):
			raise FaultError("Cold-Junction High Fault")
		if ((fault & 0x10) != 0):
			raise FaultError("Cold-Junction Low Fault")
		if ((fault & 0x08) != 0):
			raise FaultError("Thermocouple Temperature High Fault")
		if ((fault & 0x04) != 0):
			raise FaultError("Thermocouple Temperature Low Fault")
		if ((fault & 0x02) != 0):
			raise FaultError("Overvoltage or Undervoltage Input Fault")
		if ((fault & 0x01) != 0):
			raise FaultError("Thermocouple Open-Circuit Fault")
				
		return temp_C
				
	def readJunctionTemp(self):
		self.requestTempConv()
		
		# read 3 registers starting with register 9
		out = self.readRegisters(0x09, 3)
		
		offset = out[0]
		
		[junc_msb, junc_lsb] = [out[1], out[2]]
		
		temp = ((junc_msb << 8) | junc_lsb) >> 2
		temp = offset + temp
		
		if (junc_msb & 0x80):
			temp -= 0x4000
		
		temp_C = temp * 0.015625
		
		return temp_C
	
	def requestTempConv(self):
		#
		# Config Register 1
		# ------------------
		# bit 7: Conversion Mode                         -> 0 (Normally Off Mode)
		# bit 6: 1-shot                                  -> 1 (ON)
		# bit 5: open-circuit fault detection            -> 0 (off)
		# bit 4: open-circuit fault detection            -> 0 (off)
		# bit 3: Cold-junction temerature sensor enabled -> 0 (default)
		# bit 2: Fault Mode                              -> 0 (default)
		# bit 1: fault status clear                      -> 1 (clear any fault)
		# bit 0: 50/60 Hz filter select                  -> 0 (60Hz)
		#
		# write config register 0
		self.writeRegister(0, 0x42)
		# conversion time is less than 150ms
		time.sleep(.2) #give it 200ms for conversion

	def writeRegister(self, regNum, dataByte):
		GPIO.output(self.csPin, GPIO.LOW)
		
		# 0x8x to specify 'write register value'
		addressByte = 0x80 | regNum;
		
		# first byte is address byte
		self.sendByte(addressByte)
		# the rest are data bytes
		self.sendByte(dataByte)

		GPIO.output(self.csPin, GPIO.HIGH)

		
	def readRegisters(self, regNumStart, numRegisters):
		out = []
		GPIO.output(self.csPin, GPIO.LOW)
		
		# 0x to specify 'read register value'
		self.sendByte(regNumStart)
		
		for byte in range(numRegisters):	
			data = self.recvByte()
			out.append(data)

		GPIO.output(self.csPin, GPIO.HIGH)
		return out

	def sendByte(self,byte):
		for bit in range(8):
			GPIO.output(self.clkPin, GPIO.HIGH)
			if (byte & 0x80):
				GPIO.output(self.mosiPin, GPIO.HIGH)
			else:
				GPIO.output(self.mosiPin, GPIO.LOW)
			byte <<= 1
			GPIO.output(self.clkPin, GPIO.LOW)

	def recvByte(self):
		byte = 0x00
		for bit in range(8):
			GPIO.output(self.clkPin, GPIO.HIGH)
			byte <<= 1
			if GPIO.input(self.misoPin):
				byte |= 0x1
			GPIO.output(self.clkPin, GPIO.LOW)
		return byte	

class FaultError(Exception):
	pass