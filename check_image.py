#!/usr/bin/env python3
"""Check image size and basic boot header structure; this is not a boot test."""
import argparse
import hashlib
import pathlib
import struct

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=pathlib.Path)
    image = parser.parse_args().image
    size = image.stat().st_size
    if size > 134217728:
        raise SystemExit('FAIL: image exceeds the 128 MiB recovery partition.')
    with image.open('rb') as handle:
        header = handle.read(1660)
    if len(header) < 1660 or header[:8] != b'ANDROID!':
        raise SystemExit('FAIL: missing Android boot-image header.')
    kernel_size, = struct.unpack_from('<I', header, 8)
    ramdisk_size, = struct.unpack_from('<I', header, 16)
    second_size, = struct.unpack_from('<I', header, 24)
    page_size, header_version = struct.unpack_from('<II', header, 36)
    if page_size != 4096 or header_version != 2:
        raise SystemExit('FAIL: expected 4096-byte pages and header v2 for this tree.')
    dtbo_size, = struct.unpack_from('<I', header, 1632)
    dtb_size, = struct.unpack_from('<I', header, 1648)
    if not kernel_size or not ramdisk_size or not dtb_size:
        raise SystemExit('FAIL: kernel, ramdisk or DTB is empty.')
    align = lambda value: (value + page_size - 1) // page_size * page_size
    minimum = page_size + sum(align(n) for n in [kernel_size, ramdisk_size, second_size, dtbo_size, dtb_size])
    if minimum > size:
        raise SystemExit('FAIL: declared boot-image components exceed the file length.')
    digest = hashlib.sha256()
    with image.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    print('PASS: basic header and size checks only; boot/decryption remain unverified.')
    print('Bytes:', size)
    print('SHA-256:', digest.hexdigest())

if __name__ == '__main__':
    main()
