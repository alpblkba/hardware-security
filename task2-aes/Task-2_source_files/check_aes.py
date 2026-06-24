#!/usr/bin/python3

import os
import sys
import serial
import time
import serial.tools.list_ports

# Edit UART device if necessary
# Edit UART device if necessary.
# Override manually with:
#   DEV_UART=/dev/cu.usbserial-21400 python3 check_aes.py
DEV_UART = os.environ.get("DEV_UART")

if DEV_UART is None:
    ports = [p.device for p in serial.tools.list_ports.comports()]

    preferred = [
        p for p in ports
        if (
            p.startswith("/dev/cu.usbserial")
            or p.startswith("/dev/cu.usbmodem")
            or p.startswith("/dev/ttyUSB")
            or p.startswith("/dev/ttyACM")
        )
    ]

    if len(preferred) == 1:
        DEV_UART = preferred[0]
    elif len(preferred) > 1:
        print("Multiple candidate UART devices found:")
        for p in preferred:
            print("  " + p)
        print("Please choose one, for example:")
        print(f"  DEV_UART={preferred[0]} python3 check_aes.py")
        sys.exit(1)
    else:
        print("No UART device found.")
        print("Available serial ports:")
        for p in ports:
            print("  " + p)
        sys.exit(1)

print("Using UART device:", DEV_UART)

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

# Send the example test string from NIST.FIPS.197
print("Sending plaintext...")
#ser.write(bytes.fromhex("0123456789abcdef0123456789abcdef"))
ser.write(bytes.fromhex("3243f6a8885a308d313198a2e0370734"))

# Receive the 16 byte ciphertext
cipher = ser.read(16)
if (len(cipher) == 16):
    print("Received ciphertext: " + cipher.hex())
    print("Correct ciphertext:  3925841d02dc09fbdc118597196a0b32")
    if (cipher.hex() == "3925841d02dc09fbdc118597196a0b32"):
        print("AES seems to be working correctly, congratulations!")
    else:
        print("Incorrect ciphertext received!")
else:
    print("Error receiving ciphertext!")
    print("Received: " + cipher.hex())

print("Finished");
