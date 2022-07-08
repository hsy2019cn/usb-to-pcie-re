#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

# asm236x_tool.py - A tool to interact with ASM236x devices over USB.
# Copyright (C) 2022  Forest Crossman <cyrozap@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


import argparse
import os
import struct
import sys
import time

try:
    import sgio
except ModuleNotFoundError:
    sys.stderr.write("Error: Failed to import \"sgio\". Please install \"cython-sgio\", then try running this script again.\n")
    sys.exit(1)


class Asm236x:
    def __init__(self, dev_path):
        self._file = os.fdopen(os.open(dev_path, os.O_RDWR | os.O_NONBLOCK))


def dump(args, dev):
    start_addr = 0x0000
    read_len = 1 << 16
    stride = 128

    data = bytearray(read_len)

    start_ns = time.perf_counter_ns()
    for i in range(0, read_len, stride):
        remaining = read_len - i
        buf_len = min(stride, remaining)

        cdb = struct.pack('>BBBHB', 0xe4, buf_len, 0x00, start_addr + i, 0x00)

        buf = bytearray(buf_len)
        ret = sgio.execute(dev._file, cdb, None, buf)
        assert ret == 0

        data[i:i+buf_len] = buf

    end_ns = time.perf_counter_ns()
    elapsed = end_ns - start_ns
    print("Read {} bytes in {:.6f} seconds ({} bytes per second).".format(
        len(data), elapsed/1e9, int(len(data)*1e9) // elapsed))

    open(args.dump_file, 'wb').write(data)

    return 0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--device", default="/dev/sg0", help="The SCSI/SG_IO device. Default: /dev/sg0")

    subparsers = parser.add_subparsers(dest="command", required=True, help="Subcommands.")

    parser_dump = subparsers.add_parser("dump")
    parser_dump.add_argument("dump_file", help="The file to write the memory dump output to.")
    parser_dump.set_defaults(func=dump)

    args = parser.parse_args()

    # Initialize the device object.
    dev = Asm236x(args.device)

    return args.func(args, dev)


if __name__ == "__main__":
    sys.exit(main())