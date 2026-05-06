Task-0 UART LED sanity test working.

Board: Lattice iCE40HX8K
macOS port used: /dev/cu.usbserial-21201
Python serial package: pyserial 3.5

Validated commands:
  make clean
  make
  make prog
  python3 basic_uart.py --list
  python3 basic_uart.py
  python3 basic_uart.py --blink
  python3 basic_uart.py --pattern 0xff
  python3 basic_uart.py --pattern 0x00
  python3 basic_uart.py --pattern 0x55
  python3 basic_uart.py --pattern 0xaa

Observed:
  FPGA acknowledges 's' with 0x80.
  Payload byte directly controls LED_STATE.
  LED walk, blink, all-on/all-off, 0x55, and 0xaa patterns work.

