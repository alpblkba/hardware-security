#!/usr/bin/env python3

import argparse
import glob
import os
import sys
import termios
import time
from typing import Optional

try:
    import serial
    import serial.tools.list_ports
except ModuleNotFoundError:
    serial = None


BAUD_RATE = 115200


class PosixSerial:
    """Small pyserial fallback for macOS/Linux sanity checks."""

    def __init__(self, port: str, baud_rate: int, timeout: float = 1.0):
        self.port = port
        self.timeout = timeout
        self.fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        self._configure(baud_rate)

    def _configure(self, baud_rate: int) -> None:
        if baud_rate != 115200:
            raise ValueError("PosixSerial fallback currently supports only 115200 baud.")

        attrs = termios.tcgetattr(self.fd)

        # input flags, output flags, local flags
        attrs[0] = 0
        attrs[1] = 0
        attrs[3] = 0

        # 8 data bits, receiver enabled, ignore modem control lines
        attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL

        attrs[4] = termios.B115200
        attrs[5] = termios.B115200

        # read returns after timeout even if no byte arrives
        attrs[6][termios.VMIN] = 0
        attrs[6][termios.VTIME] = int(self.timeout * 10)

        termios.tcsetattr(self.fd, termios.TCSANOW, attrs)
        termios.tcflush(self.fd, termios.TCIOFLUSH)

    def read(self, size: int) -> bytes:
        deadline = time.time() + self.timeout
        chunks = []
        remaining = size

        while remaining > 0 and time.time() < deadline:
            try:
                chunk = os.read(self.fd, remaining)
            except BlockingIOError:
                time.sleep(0.01)
                continue

            if not chunk:
                time.sleep(0.01)
                continue

            chunks.append(chunk)
            remaining -= len(chunk)

        return b"".join(chunks)

    def write(self, data: bytes) -> int:
        return os.write(self.fd, data)

    def setRTS(self, value: bool) -> None:
        # This fallback does not control modem lines. For this sanity check,
        # skipping RTS reset is acceptable.
        return None

    def close(self) -> None:
        os.close(self.fd)


def list_serial_ports() -> list[str]:
    if serial is not None:
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append(port.device)
        return ports

    # pyserial is not installed for this Python interpreter.
    # Use filesystem globbing as a macOS/Linux fallback.
    patterns = [
        "/dev/cu.usbserial*",
        "/dev/tty.usbserial*",
        "/dev/cu.usbmodem*",
        "/dev/tty.usbmodem*",
        "/dev/ttyUSB*",
        "/dev/ttyACM*",
    ]

    ports = []
    for pattern in patterns:
        ports.extend(glob.glob(pattern))

    return sorted(set(ports))


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


def open_serial(port: str, baud_rate: int):
    if serial is None:
        print("pyserial is not available for this Python interpreter; using POSIX serial fallback.")
        return PosixSerial(port, baud_rate, timeout=1)

    return serial.Serial(
        port=port,
        baudrate=baud_rate,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=1,
    )


def reset_fpga_via_rts(ser) -> None:
    # if RTS is connected through the PCF/top-level design, this can reset the FPGA.
    time.sleep(0.001)
    ser.setRTS(False)
    time.sleep(0.001)
    ser.setRTS(True)
    time.sleep(0.001)


def send_led_pattern(ser, pattern: int) -> None:
    ser.write(b"s")
    ser.write(bytes([pattern & 0xff]))


def run_default_sequence(ser) -> None:
    print("Sending LED test sequence. Watch the LEDs on the board.")

    for value in [0x00, ord("a"), ord("b"), ord("c"), ord("d"), ord("e"), ord("f"), ord("g")]:
        send_led_pattern(ser, value)
        time.sleep(1)


def run_blink_sequence(ser, repeats: int = 8, delay: float = 0.25) -> None:
    print("Blinking all LEDs. Watch the LEDs on the board.")

    for _ in range(repeats):
        send_led_pattern(ser, 0xff)
        time.sleep(delay)
        send_led_pattern(ser, 0x00)
        time.sleep(delay)


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
    parser.add_argument(
        "--pattern",
        type=lambda value: int(value, 0),
        help="Send one LED byte pattern, for example 0xaa, 0x55, 255, or 0.",
    )
    parser.add_argument(
        "--blink",
        action="store_true",
        help="Blink all LEDs as a quick board sanity check.",
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
    except Exception as exc:
        print(f"Could not open serial port {port}: {exc}")
        return 1

    try:
        if not args.no_reset:
            reset_fpga_via_rts(ser)

        # consume old buffered data after reset
        leftover = ser.read(32).decode("utf8", "ignore")
        print(f"Data left on usb-serial adapter from reset: < {leftover} >")

        # interact with board
        if args.pattern is not None:
            pattern = args.pattern & 0xff
            print(f"Sending LED pattern: 0x{pattern:02x}")
            send_led_pattern(ser, pattern)
        elif args.blink:
            run_blink_sequence(ser)
        else:
            run_default_sequence(ser)

        print("Finished.")
        return 0

    finally:
        ser.close()


if __name__ == "__main__":
    sys.exit(main())
