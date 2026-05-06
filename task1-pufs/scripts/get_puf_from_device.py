#!/usr/bin/python3

import os
import sys
import serial
import time
import serial.tools.list_ports

DEV_UART = '/dev/ttyUSB1'

# write/overwrite puf_data.txt
puftxt = open('puf_data.txt', 'w');

# separate memory into how many blocks
# (in powers of 2)
DIVIDER = 512

# in windows:
if ('-win') in sys.argv:
    # BASEPATH='C:/Users/Xiang/Documents/git/iot-security/'
    plist = list(serial.tools.list_ports.comports())

    if len(plist) <= 0:
        print("The Serial port can't be found!")
    else:
        plist_0 = list(plist[1])
        DEV_UART = plist_0[0]

BAUD_RATE=115200

ser = serial.Serial(
    port=DEV_UART,
    baudrate=BAUD_RATE,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1
)

# if you connect the reset signal in LatticeiCE40HX8K.pcf
# (with set_io RST B13), then you can reset the FPGA like this:
time.sleep(0.001);
ser.setRTS(False);
time.sleep(0.001);
ser.setRTS(True);
time.sleep(0.001);

# consume data already buffered in the usb-to-serial adapter
print("Data left on usb-serial adapter from reset: < "+str(ser.read(32).decode('utf8','ignore'))+" >");

print("Requesting PUF data:")

# ask for puf data
ser.write(b's')

print("Receiving PUF data in "+str(int(16384/DIVIDER))+"-byte blocks");

# 
for i in range(0,DIVIDER):
    pufdata = ser.read(int(16384/DIVIDER))
    print(".",end='')
    sys.stdout.flush()
    puftxt.write(pufdata.hex())
    puftxt.write('\n')

ser.close()
puftxt.close()

print("Finished");
