#!/usr/bin/env python3
import argparse
import glob
import os
import sys
import termios
import time
from pathlib import Path
from typing import Optional

try:
    import serial
    import serial.tools.list_ports
except ModuleNotFoundError:
    serial = None

BAUD_RATE = 115200
TOTAL_BYTES = 16384
DIVIDER = 512
BYTES_PER_BLOCK = TOTAL_BYTES // DIVIDER
DEFAULT_OUTPUT = "puf_data.txt"


class PosixSerial:
    """Small pyserial fallback for macOS/Linux UART captures."""

    def __init__(self, port: str, baud_rate: int, timeout: float = 1.0):
        self.port = port
        self.timeout = timeout
        self.fd = os.open(port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        self._configure(baud_rate)

    def _configure(self, baud_rate: int) -> None:
        if baud_rate != 115200:
            raise ValueError("POSIX serial fallback currently supports only 115200 baud.")

        attrs = termios.tcgetattr(self.fd)

        # raw 8N1 UART mode
        attrs[0] = 0
        attrs[1] = 0
        attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        attrs[3] = 0
        attrs[4] = termios.B115200
        attrs[5] = termios.B115200
        attrs[6][termios.VMIN] = 0
        attrs[6][termios.VTIME] = int(self.timeout * 10)

        termios.tcsetattr(self.fd, termios.TCSANOW, attrs)
        termios.tcflush(self.fd, termios.TCIOFLUSH)

    def read(self, size: int) -> bytes:
        deadline = time.time() + self.timeout
        chunks: list[bytes] = []
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
        # RTS reset is optional for this task. The fallback skips modem-line control.
        return None

    def close(self) -> None:
        os.close(self.fd)


def list_serial_ports() -> list[str]:
    if serial is not None:
        return sorted(port.device for port in serial.tools.list_ports.comports())

    patterns = [
        "/dev/cu.usbserial*",
        "/dev/tty.usbserial*",
        "/dev/cu.usbmodem*",
        "/dev/tty.usbmodem*",
        "/dev/ttyUSB*",
        "/dev/ttyACM*",
    ]

    ports: list[str] = []
    for pattern in patterns:
        ports.extend(glob.glob(pattern))

    return sorted(set(ports))


def auto_select_port() -> Optional[str]:
    ports = list_serial_ports()
    if not ports:
        return None

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

    if len(preferred) >= 2:
        # The Lattice HX8K board usually exposes two FTDI serial ports.
        # The lab guide uses the second ttyUSB port on Linux; on macOS this
        # usually corresponds to the second /dev/cu.usbserial-* port.
        return preferred[1]

    return ports[0]


def open_serial(port: str, baud_rate: int, timeout: float):
    if serial is None:
        print("pyserial is not available for this Python interpreter; using POSIX serial fallback.")
        return PosixSerial(port, baud_rate, timeout=timeout)

    return serial.Serial(
        port=port,
        baudrate=baud_rate,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=timeout,
    )


def reset_fpga_via_rts(ser) -> None:
    time.sleep(0.001)
    ser.setRTS(False)
    time.sleep(0.001)
    ser.setRTS(True)
    time.sleep(0.001)


def read_exact(ser, size: int, timeout: float) -> bytes:
    deadline = time.time() + timeout
    chunks: list[bytes] = []
    remaining = size

    while remaining > 0 and time.time() < deadline:
        chunk = ser.read(remaining)
        if not chunk:
            continue
        chunks.append(chunk)
        remaining -= len(chunk)

    return b"".join(chunks)


def write_capture_file(output_path: Path, data: bytes) -> None:
    if len(data) != TOTAL_BYTES:
        raise ValueError(f"expected {TOTAL_BYTES} bytes, received {len(data)} bytes")

    with output_path.open("w", encoding="ascii") as puf_txt:
        for offset in range(0, TOTAL_BYTES, BYTES_PER_BLOCK):
            block = data[offset:offset + BYTES_PER_BLOCK]
            puf_txt.write(block.hex())
            puf_txt.write("\n")


def validate_capture_file(output_path: Path) -> None:
    lines = output_path.read_text(encoding="ascii").splitlines()

    if len(lines) != DIVIDER:
        raise ValueError(f"expected {DIVIDER} lines, got {len(lines)}")

    expected_width = BYTES_PER_BLOCK * 2
    bad_lines = [index + 1 for index, line in enumerate(lines) if len(line) != expected_width]
    if bad_lines:
        preview = ", ".join(str(line) for line in bad_lines[:10])
        raise ValueError(f"expected {expected_width} hex chars per line; bad lines: {preview}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture SRAM PUF data from the Lattice iCE40 HX8K board over UART."
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available serial ports and exit.",
    )
    parser.add_argument(
        "-p",
        "--port",
        help="Serial port to use. If omitted, the script auto-selects a likely board UART port.",
    )
    parser.add_argument(
        "-b",
        "--baud",
        type=int,
        default=BAUD_RATE,
        help=f"UART baud rate. Default: {BAUD_RATE}.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Output capture file. Default: {DEFAULT_OUTPUT}.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Total receive timeout in seconds. Default: 10.",
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Do not toggle RTS before requesting PUF data.",
    )
    parser.add_argument(
        "--request-byte",
        default="s",
        help="Single character request byte sent to the FPGA. Default: s.",
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

        selected = auto_select_port()
        if selected is not None:
            print(f"Auto-selected port would be: {selected}")
        return 0

    port = args.port or auto_select_port()
    if port is None:
        print("No serial port found. Connect the board or pass --port manually.")
        return 1

    request = args.request_byte.encode("ascii")
    if len(request) != 1:
        print("--request-byte must encode to exactly one ASCII byte.")
        return 1

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Opening serial port: {port}")
    print(f"Baud rate: {args.baud}")
    print(f"Output file: {output_path}")

    try:
        ser = open_serial(port, args.baud, timeout=1)
    except Exception as exc:
        print(f"Could not open serial port {port}: {exc}")
        return 1

    try:
        if not args.no_reset:
            reset_fpga_via_rts(ser)

        leftover = ser.read(32).decode("utf8", "ignore")
        print(f"Data left on usb-serial adapter from reset: < {leftover} >")

        print("Requesting PUF data.")
        ser.write(request)

        print(f"Receiving {TOTAL_BYTES} bytes as {DIVIDER} blocks of {BYTES_PER_BLOCK} bytes.")
        data = read_exact(ser, TOTAL_BYTES, timeout=args.timeout)
        print(f"Received {len(data)} / {TOTAL_BYTES} bytes.")

        write_capture_file(output_path, data)
        validate_capture_file(output_path)

        print("Capture shape OK: 512 lines, 64 hex characters per line.")
        print("Finished.")
        return 0
    except Exception as exc:
        print(f"Capture failed: {exc}")
        return 1
    finally:
        ser.close()


if __name__ == "__main__":
    sys.exit(main())