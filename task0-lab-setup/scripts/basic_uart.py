#!/usr/bin/env python3

import argparse
import sys
import time
from typing import Optional

import serial
import serial.tools.list_ports


BAUD_RATE = 115200


def list_serial_ports() -> list[str]:
    ports = []
    for port in serial.tools.list_ports.comports():
        ports.append(port.device)
    return ports


def auto_select_port() -> Optional[str]:
    ports = list_serial_ports()

    if not ports:
        return None

    # prefer likely usb-serial ports on macos, linux, and windows
    preferred_keywords = [
        "usbserial",
        "usbmodem",
        "ttyUSB",
        "ttyACM",
        "COM",
    ]

    preferred = [
        port for port in ports
        if any(keyword.lower() in port.lower() for keyword in preferred_keywords)
    ]

    if len(preferred) == 1:
        return preferred[0]

    # the Lattice HX8K board usually exposes two FTDI serial ports.
    # on linux the lab guide often uses the second ttyUSB port.
    # on macos this often corresponds to the second cu.usbserial port.
    if len(preferred) >= 2:
        return preferred[1]

    return ports[0]


def open_serial(port: str, baud_rate: int) -> serial.Serial:
    return serial.Serial(
        port=port,
        baudrate=baud_rate,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=1,
    )


def reset_fpga_via_rts(ser: serial.Serial) -> None:
    # if RTS is connected through the PCF/top-level design, this can reset the FPGA.
    time.sleep(0.001)
    ser.setRTS(False)
    time.sleep(0.001)
    ser.setRTS(True)
    time.sleep(0.001)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Basic UART test for the Lattice iCE40 HX8K Task-0 design."
    )
    parser.add_argument(
        "-p",
        "--port",
        help="Serial port, for example /dev/cu.usbserial-11301 on macOS or /dev/ttyUSB1 on Linux.",
    )
    parser.add_argument(
        "-b",
        "--baud",
        type=int,
        default=BAUD_RATE,
        help=f"Baud rate, default {BAUD_RATE}.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available serial ports and exit.",
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Do not toggle RTS before starting communication.",
    )
    args = parser.parse_args()

    if args.list:
        ports = list_serial_ports()
        if not ports:
            print("No serial ports found.")
            return 1

        print("Available serial ports:")
        for port in ports:
            print(f"  {port}")
        return 0

    port = args.port or auto_select_port()

    if port is None:
        print("No serial port found. Is the board connected?")
        return 1

    print(f"Opening serial port: {port}")
    print(f"Baud rate: {args.baud}")

    try:
        ser = open_serial(port, args.baud)
    except serial.SerialException as exc:
        print(f"Could not open serial port {port}: {exc}")
        return 1

    try:
        if not args.no_reset:
            reset_fpga_via_rts(ser)

        # consume old buffered data after reset
        leftover = ser.read(32).decode("utf8", "ignore")
        print(f"Data left on usb-serial adapter from reset: < {leftover} >")

        # interact with board
        print("Sending LED test sequence. Watch the LEDs on the board.")

        ser.write(b"s")
        ser.write(b"\0")

        time.sleep(1)
        ser.write(b"s")
        ser.write(b"a")

        time.sleep(1)
        ser.write(b"S")
        ser.write(b"b")

        time.sleep(1)
        ser.write(b"S")
        ser.write(b"c")

        time.sleep(1)
        ser.write(b"S")
        ser.write(b"d")

        time.sleep(1)
        ser.write(b"S")
        ser.write(b"e")

        time.sleep(1)
        ser.write(b"S")
        ser.write(b"f")

        time.sleep(1)
        ser.write(b"S")
        ser.write(b"g")

        print("Finished.")
        return 0

    finally:
        ser.close()


if __name__ == "__main__":
    sys.exit(main())
