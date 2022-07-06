#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later

# firmware_tool.py - A tool to parse ASM236x firmware image files.
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
import sys

try:
    import asm236x_fw
except ModuleNotFoundError:
    sys.stderr.write("Error: Failed to import \"asm236x_fw.py\". Please run \"make\" in this directory to generate that file, then try running this script again.\n")
    sys.exit(1)


IDLE_TIMER_STRINGS = {
    0x1: "3 minutes",
    0x2: "5 minutes",
    0x3: "10 minutes",
    0x4: "15 minutes",
    0x5: "20 minutes",
    0x6: "30 minutes",
    0x7: "1 hour",
    0x8: "2 hours",
    0x9: "3 hours",
    0xa: "4 hours",
    0xb: "5 hours",
    0xf: "Never",
}


def fw_version_bytes_to_string(version):
    return "{:02X}{:02X}{:02X}_{:02X}_{:02X}_{:02X}".format(*version)

def trim_0xff(string: bytes):
    return string.rstrip(b'\xff')

def extract(filename=None, fw=None, **kwargs):
    split = filename.split('.')
    basename = '.'.join(split[:-1])
    dest_name = "{}.code.bin".format(basename)

    print("Extracting {} bytes of firmware code from \"{}\" and writing it to \"{}\"...".format(fw.body.size, filename, dest_name))

    f = open(dest_name, "wb")
    f.write(fw.body.firmware.code)
    f.close()

    print("Done!")

    return 0

def info(filename=None, fw=None, fw_bin=None, **kwargs):
    version_string = fw_version_bytes_to_string(fw.body.firmware.version)
    print("Firmware version: {}".format(version_string))

    usb_info = fw.header.usb_info
    print("USB IDs: {:04x}:{:04x}".format(usb_info.id_vendor, usb_info.id_product))
    print("USB Device Revision: {:04x}".format(usb_info.bcd_device))
    print("EP0 Manufacturer String: {}".format(trim_0xff(fw.header.ep0_manufacturer_string)))
    print("EP0 Product String: {}".format(trim_0xff(fw.header.ep0_product_string)))
    print("T10 Manufacturer String: {}".format(trim_0xff(fw.header.t10_manufacturer_string)))
    print("T10 Product String: {}".format(trim_0xff(fw.header.t10_product_string)))
    print("Serial number: {}".format(trim_0xff(fw.header.serial_number)))
    print("Idle timer: {}".format(IDLE_TIMER_STRINGS.get(fw.header.idle_timer, "Unknown value: 0x{:x}".format(fw.header.idle_timer))))

    calculated_csum = sum(fw_bin[0x04:0x7f]) & 0xff
    expected_csum = fw.header.checksum
    print("Header checksum: Expected: 0x{:02x}, Calculated: 0x{:02x}".format(expected_csum, calculated_csum))
    print("Image size: {} bytes".format(fw.body.size))

    return 0

def raw_info(fw_bin=None, **kwargs):
    version_string = fw_version_bytes_to_string(fw_bin[0x200:0x200+6])
    print("Firmware version: {}".format(version_string))

    return 0

def unsupported(command=None, fw_type=None, **kwargs):
    print("Error: Command \"{}\" is not supported for image type \"{}\".".format(command, fw_type), file=sys.stderr)

    return 1

def main():
    commands = {
        "extract": {
            "image": extract,
        },
        "info": {
            "image": info,
            "raw": raw_info,
        },
    }

    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--type", choices=("auto", "image", "raw"), default="auto", help="The image type. Default: auto")
    parser.add_argument("command", choices=commands.keys(), help="Subcommands.")
    parser.add_argument("firmware", type=str, help="The firmware image file.")
    args = parser.parse_args()

    fw_bin = open(args.firmware, 'rb').read()

    fw_type = args.type
    if fw_type != "auto":
        print("Firmware type set to \"{}\".".format(fw_type))
    else:
        print("Trying to guess firmware type...")
        threshold = 3
        points = 0

        # Is the serial number string present?
        try:
            bytes.fromhex(fw_bin[4:4+12].decode('ascii'))
            points += 1
        except Exception:
            pass

        # Is "ASMT" present?
        try:
            if fw_bin[0x3c:0x3c+4].decode('ascii') == "ASMT":
                points += 1
        except Exception:
            pass

        # Is the magic value present?
        try:
            if fw_bin[0x7e] == 0x5a:
                points += 1
        except Exception:
            pass

        # Are the exception vector long jump instructions all present?
        try:
            vector_offsets = (0x82, 0x85, 0x8d, 0x95)
            vectors_present = 0
            for offset in vector_offsets:
                vectors_present += 1
            if vectors_present == len(vector_offsets):
                points += 1
        except Exception:
            pass

        if points >= threshold:
            fw_type = "image"
        else:
            fw_type = "raw"
        print("Guessed firmware type is \"{}\".".format(fw_type))

    if fw_type == "image":
        fw = asm236x_fw.Asm236xFw.from_bytes(fw_bin)
        return commands[args.command].get(fw_type, unsupported)(command=args.command, filename=args.firmware, fw=fw, fw_bin=fw_bin, fw_type=fw_type)
    elif fw_type == "raw":
        return commands[args.command].get(fw_type, unsupported)(command=args.command, filename=args.firmware, fw_bin=fw_bin, fw_type=fw_type)
    else:
        print("Error: Unknown image type: {}".format(fw_type), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
