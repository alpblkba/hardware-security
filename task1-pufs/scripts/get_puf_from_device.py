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

    def read(self, size: int, *, label: str = "read", verbose: bool = False) -> bytes:
        """Read up to `size` bytes from the non-blocking serial file descriptor.

        `size` is counted in bytes, not bits. For example, read(32) asks for
        32 bytes, which is 256 bits.

        `self.fd` is the low-level POSIX file descriptor returned by os.open().
        This is an integer handle used by os.read()/os.write(); it is lower-level
        than pyserial's Serial object, but it lets this fallback implement manual
        non-blocking reads on macOS/Linux.

        `b''` means an empty bytes object: no byte was received in that read
        attempt. It does not mean that a literal character `b` arrived.
        """
        deadline = time.time() + self.timeout
        chunks: list[bytes] = []
        remaining = size
        attempts = 0
        empty_reads = 0
        blocked_reads = 0

        if verbose:
            print(f"fd is: {self.fd}")
            print(
                f"[read:{label}] start requested={size} bytes "
                f"timeout={self.timeout}s fd={self.fd}"
            )

        while remaining > 0 and time.time() < deadline:
            attempts += 1
            try:
                if verbose:
                    print(f"remaining is: {remaining}")
                chunk = os.read(self.fd, remaining)
            except BlockingIOError:
                blocked_reads += 1
                if verbose and blocked_reads <= 10:
                    print(f"[read:{label}] would block; no bytes available yet")
                time.sleep(0.01)
                continue

            if not chunk:
                empty_reads += 1
                if verbose and empty_reads <= 10:
                    print(f"[read:{label}] empty bytes b''; no bytes available yet")
                time.sleep(0.01)
                continue

            chunks.append(chunk)
            remaining -= len(chunk)

            if verbose:
                preview = chunk[:16].hex()
                print(
                    f"[read:{label}] chunk_len={len(chunk)} "
                    f"remaining={remaining} chunks={len(chunks)} "
                    f"preview_hex={preview}"
                )

        data = b"".join(chunks)

        if verbose:
            print(
                f"[read:{label}] done received={len(data)}/{size} bytes "
                f"remaining={remaining} chunks={len(chunks)} "
                f"attempts={attempts} empty_reads={empty_reads} "
                f"blocked_reads={blocked_reads}"
            )

        return data

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

    ser = serial.Serial(
        port=port,
        baudrate=baud_rate,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=timeout,
    )
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    return ser


def reset_fpga_via_rts(ser) -> None:
    time.sleep(0.001)
    ser.setRTS(False)
    time.sleep(0.001)
    ser.setRTS(True)
    time.sleep(0.001)


def read_serial_debug(ser, size: int, *, label: str, verbose: bool) -> bytes:
    """Read from either pyserial.Serial or the local PosixSerial fallback.

    This wrapper exists because pyserial.Serial.read() only accepts `size`, while
    PosixSerial.read() accepts extra debug labels. Keeping this wrapper prevents
    TypeError-driven control flow inside the receive loop and prints useful state
    for both backends.
    """
    if verbose:
        print(f"[serial:{label}] backend={type(ser).__module__}.{type(ser).__name__}")
        fd = getattr(ser, "fd", None)
        if fd is not None:
            print(f"[serial:{label}] fd={fd}")
        in_waiting = getattr(ser, "in_waiting", None)
        if in_waiting is not None:
            try:
                print(f"[serial:{label}] in_waiting_before={in_waiting}")
            except Exception:
                pass

    if isinstance(ser, PosixSerial):
        data = ser.read(size, label=label, verbose=verbose)
    else:
        # pyserial path: Serial.read(size) blocks until `size` bytes arrive or
        # until the serial timeout expires. If this returns b'', the selected
        # port produced no bytes during that timeout window.
        data = ser.read(size)

    if verbose:
        in_waiting = getattr(ser, "in_waiting", None)
        if in_waiting is not None:
            try:
                print(f"[serial:{label}] in_waiting_after={in_waiting}")
            except Exception:
                pass
        print(
            f"[serial:{label}] returned_len={len(data)} "
            f"repr={data[:32]!r} preview_hex={data[:32].hex()}"
        )

    return data


def read_exact(ser, size: int, timeout: float, *, verbose: bool = False) -> bytes:
    deadline = time.time() + timeout
    chunks: list[bytes] = []
    remaining = size
    iterations = 0
    empty_chunks = 0

    if verbose:
        print(f"[read_exact] start requested={size} bytes timeout={timeout}s")

    while remaining > 0 and time.time() < deadline:
        iterations += 1
        if verbose:
            print(f"[read_exact] iteration={iterations} remaining_before={remaining}")

        chunk = read_serial_debug(
            ser,
            remaining,
            label=f"capture-{iterations}",
            verbose=verbose,
        )

        if not chunk:
            empty_chunks += 1
            if verbose and empty_chunks <= 10:
                print(f"[read_exact] empty chunk; received_total={size - remaining}/{size}")
            continue

        chunks.append(chunk)
        remaining -= len(chunk)

        if verbose:
            print(
                f"[read_exact] accepted chunk_len={len(chunk)} "
                f"received_total={size - remaining}/{size} "
                f"remaining_after={remaining}"
            )

    data = b"".join(chunks)

    if verbose:
        print(
            f"[read_exact] done received={len(data)}/{size} bytes "
            f"remaining={remaining} chunks={len(chunks)} "
            f"iterations={iterations} empty_chunks={empty_chunks}"
        )

    return data


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
    parser.add_argument(
        "--verbose-read",
        action="store_true",
        help="Print detailed read progress: leftover, chunks, remaining byte counts, and capture summary.",
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
    if args.verbose_read:
        print(f"Available serial ports: {list_serial_ports()}")
        print(f"Selected serial port: {port}")
    if port is None:
        print("No serial port found. Connect the board or pass --port manually.")
        return 1

    request = args.request_byte.encode("ascii")
    if len(request) != 1:
        print("--request-byte must encode to exactly one ASCII byte.")
        return 1

    debug_raw = args.request_byte in ("d", "D")
    expected_bytes = TOTAL_BYTES

    output_path = Path(args.output)    
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Opening serial port: {port}")
    print(f"Baud rate: {args.baud}")
    print(f"Output file: {output_path}")
    
    # print(f"full parser: {parser}")


    try:
        ser = open_serial(port, args.baud, timeout=1)
    except Exception as exc:
        print(f"Could not open serial port {port}: {exc}")
        return 1

    try:
        if not args.no_reset:
            reset_fpga_via_rts(ser)

        leftover = read_serial_debug(
            ser,
            32,
            label="leftover-after-reset",
            verbose=args.verbose_read,
        )
        if args.verbose_read:
            print(f"the leftover is: {leftover}")

        print(
            "Data left on usb-serial adapter from reset: "
            f"len={len(leftover)} repr={leftover!r} hex={leftover.hex()}"
        )

        print("Requesting PUF data.")
        ser.write(request)

        if debug_raw:
            print(f"Receiving {expected_bytes} debug bytes as {DIVIDER} blocks of {BYTES_PER_BLOCK} bytes.")
        else:
            print(f"Receiving {TOTAL_BYTES} bytes as {DIVIDER} blocks of {BYTES_PER_BLOCK} bytes.")
        data = read_exact(
            ser,
            expected_bytes,
            timeout=args.timeout,
            verbose=args.verbose_read,
        )
        if args.verbose_read:
            print(
                "Capture data summary: "
                f"len={len(data)} "
                f"first32={data[:32].hex()} "
                f"last32={data[-32:].hex() if data else ''}"
            )
        print(f"Received {len(data)} / {expected_bytes} bytes.")

        write_capture_file(output_path, data)
        validate_capture_file(output_path)

        if debug_raw:
            hex_stream = data.hex()
            marker_index = hex_stream.find("4442")
            print("Debug capture shape OK: 512 lines, 64 hex characters per line.")
            print(f"Debug marker 4442 hex-index: {marker_index}")
            if marker_index >= 0:
                print(f"Debug marker byte-offset: {marker_index // 2}")
                print(f"Debug marker line: {marker_index // (BYTES_PER_BLOCK * 2)}")
                print(f"Debug marker column: {marker_index % (BYTES_PER_BLOCK * 2)}")
                print("Debug marker window:", hex_stream[marker_index:marker_index + 256])
                print("Before marker tail:", hex_stream[max(0, marker_index - 128):marker_index])
        else:
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