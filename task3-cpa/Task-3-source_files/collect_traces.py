#!/usr/bin/env python3

import argparse
import csv
import os
import time
from pathlib import Path

import serial
from tqdm import tqdm


DEFAULT_PORT = "/dev/cu.usbserial-1201"
BAUD_RATE = 1_000_000
SENSE_LEN = 56
KEY_HEX = "3c4fcf098815f7aba6d2ae2816157e2b"


def read_exact(ser: serial.Serial, length: int) -> bytes:
    data = bytearray()

    while len(data) < length:
        chunk = ser.read(length - len(data))
        if not chunk:
            break
        data.extend(chunk)

    return bytes(data)


def reset_target(ser: serial.Serial) -> None:
    time.sleep(0.001)
    ser.setRTS(False)
    time.sleep(0.001)
    ser.setRTS(True)
    time.sleep(0.001)

    ser.reset_input_buffer()
    ser.reset_output_buffer()


def collect_one(
    ser: serial.Serial,
    retries: int = 3,
) -> tuple[bytes, bytes, bytes]:
    for _ in range(retries):
        plaintext = os.urandom(16)

        ser.reset_input_buffer()
        ser.write(plaintext)
        ser.flush()

        ciphertext = read_exact(ser, 16)
        trace = read_exact(ser, SENSE_LEN)

        if len(ciphertext) == 16 and len(trace) == SENSE_LEN:
            return plaintext, ciphertext, trace

        time.sleep(0.01)

    raise RuntimeError(
        f"UART receive failed: ciphertext={len(ciphertext)}, "
        f"trace={len(trace)}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-n",
        "--count",
        type=int,
        default=100,
        help="number of traces to collect",
    )
    parser.add_argument(
        "-p",
        "--port",
        default=DEFAULT_PORT,
        help="serial device",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="measurements",
        help="output directory",
    )
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    messages_path = output_dir / "collected_msgs.csv"
    traces_path = output_dir / "collected_traces.csv"
    ciphertexts_path = output_dir / "collected_ciphertexts.csv"

    with serial.Serial(
        port=args.port,
        baudrate=BAUD_RATE,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=2,
    ) as ser:
        reset_target(ser)

        with (
            messages_path.open("w", newline="") as msg_file,
            traces_path.open("w", newline="") as trace_file,
            ciphertexts_path.open("w", newline="") as cipher_file,
        ):
            msg_writer = csv.writer(msg_file)
            trace_writer = csv.writer(trace_file)
            cipher_writer = csv.writer(cipher_file)

            for index in tqdm(range(args.count), desc="Collecting"):
                plaintext, ciphertext, trace = collect_one(ser)

                msg_writer.writerow([
                    KEY_HEX,
                    plaintext.hex(),
                ])
                cipher_writer.writerow([
                    ciphertext.hex(),
                ])
                trace_writer.writerow(list(trace))

                if (index + 1) % 100 == 0:
                    msg_file.flush()
                    cipher_file.flush()
                    trace_file.flush()

    print()
    print(f"Messages:    {messages_path}")
    print(f"Ciphertexts: {ciphertexts_path}")
    print(f"Traces:      {traces_path}")


if __name__ == "__main__":
    main()
