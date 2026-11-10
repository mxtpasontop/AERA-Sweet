#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Package an AERA ramdisk using the pinned, device-tested sweet boot baseline.

This operates on local files only. It never flashes, reboots or contacts a phone.
"""
import argparse
import gzip
import hashlib
import json
import lzma
import os
import pathlib
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
import zlib

TEMPLATE_URL = 'https://dl.orangefox.download/6a107f7a192e80d0717207e1'
ZIP_SHA256 = '5ba70d54d69ad40b1c874d29ca90da69f26e384db174bdae31f149577923d42c'
IMAGE_SHA256 = '91b1b7bc78d5b7499aff608f6a98f9e9a7f44021595648216abdabcf3dd25666'
PARTITION_BYTES = 134217728


def sha(data):
    return hashlib.sha256(data).hexdigest()


def unpack(data):
    if data[:8] != b'ANDROID!':
        raise ValueError('Not an Android boot image')
    page, version = struct.unpack_from('<II', data, 36)
    if page != 4096 or version not in (1, 2):
        raise ValueError('Expected sweet header v1/v2 with 4096-byte pages')
    parts, offset = {}, page
    for name, field in [('kernel', 8), ('ramdisk', 16), ('second', 24), ('dtbo', 1632)]:
        size = struct.unpack_from('<I', data, field)[0]
        parts[name] = data[offset:offset + size]
        if len(parts[name]) != size:
            raise ValueError('Truncated component: ' + name)
        offset += (size + page - 1) // page * page
    if parts['second'] or not parts['kernel'] or not parts['ramdisk']:
        raise ValueError('Unexpected empty kernel/ramdisk or second-stage payload')
    return parts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ['aera', 'template-zip', 'mkbootimg', 'avbtool', 'key', 'output']:
        parser.add_argument('--' + flag, type=pathlib.Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output already exists; choose a new filename.')
    env = dict(os.environ)
    git_openssl = pathlib.Path('C:/Program Files/Git/usr/bin/openssl.exe')
    if os.name == 'nt' and git_openssl.is_file():
        env['PATH'] = str(git_openssl.parent) + os.pathsep + env.get('PATH', '')

    def run(arguments, capture=False):
        return subprocess.run([str(item) for item in arguments], env=env, check=True,
                              stdout=subprocess.PIPE if capture else None,
                              text=capture, encoding='utf-8' if capture else None)

    archive_bytes = args.template_zip.read_bytes()
    if sha(archive_bytes) != ZIP_SHA256:
        raise SystemExit('Template ZIP SHA-256 differs from the pinned official release.')
    with zipfile.ZipFile(args.template_zip) as archive:
        if archive.getinfo('recovery.img').file_size != PARTITION_BYTES:
            raise SystemExit('Unexpected template image size.')
        baseline = archive.read('recovery.img')
    if sha(baseline) != IMAGE_SHA256:
        raise SystemExit('Template image differs from the device-tested baseline.')
    source = args.aera.read_bytes()
    template_parts, source_parts = unpack(baseline), unpack(source)
    kernel_decoder = zlib.decompressobj(31)
    kernel = kernel_decoder.decompress(template_parts['kernel'])
    config_start = kernel.find(b'IKCFG_ST')
    if config_start < 0 or not kernel_decoder.unused_data.startswith(b'\xd0\x0d\xfe\xed'):
        raise SystemExit('Expected embedded kernel configuration and appended DTB.')
    config = zlib.decompress(kernel[config_start + 8:], 31).decode()
    if 'CONFIG_RD_LZMA=y' not in config.splitlines():
        raise SystemExit('Template kernel does not advertise LZMA initramfs support.')
    packed = source_parts['ramdisk']
    cpio = gzip.decompress(packed) if packed.startswith(b'\x1f\x8b') else lzma.decompress(packed)
    if not cpio.startswith(b'070701'):
        raise SystemExit('Expected a newc CPIO ramdisk.')
    compressed = lzma.compress(cpio, format=lzma.FORMAT_ALONE, preset=6)
    if lzma.decompress(compressed) != cpio:
        raise SystemExit('Ramdisk compression roundtrip failed.')
    info = run([sys.executable, args.avbtool, 'info_image', '--image', args.aera], capture=True).stdout
    match = re.search(r"^\s*Prop: com\.android\.build\.recovery\.fingerprint -> '(.*)'$", info, re.M)
    if not match:
        raise SystemExit('Input image is missing its recovery fingerprint descriptor.')
    fingerprint = match.group(1)
    cmdline = (baseline[64:576] + baseline[608:1632]).split(b'\0')[0].decode('ascii')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='aera-sweet-package-') as directory:
        scratch = pathlib.Path(directory)
        for name, data in [('kernel', template_parts['kernel']), ('ramdisk', compressed), ('dtbo', template_parts['dtbo'])]:
            (scratch / name).write_bytes(data)
        image = scratch / 'recovery.img'
        run([sys.executable, args.mkbootimg, '--header_version', '1', '--kernel', scratch / 'kernel',
             '--ramdisk', scratch / 'ramdisk', '--recovery_dtbo', scratch / 'dtbo', '--base', '0',
             '--kernel_offset', '0x8000', '--ramdisk_offset', '0x01000000', '--second_offset', '0',
             '--tags_offset', '0x100', '--pagesize', '4096', '--os_version', '99.87.36',
             '--os_patch_level', '2099-12-31', '--cmdline', cmdline, '--output', image])
        run([sys.executable, args.avbtool, 'add_hash_footer', '--image', image,
             '--partition_name', 'recovery', '--partition_size', str(PARTITION_BYTES),
             '--algorithm', 'SHA256_RSA4096', '--key', args.key, '--rollback_index', '1',
             '--salt', sha(template_parts['kernel'] + compressed + template_parts['dtbo']),
             '--prop', 'com.android.build.recovery.fingerprint:' + fingerprint,
             '--prop', 'com.android.build.boot.os_version:99.87.36',
             '--prop', 'com.android.build.boot.security_patch:2099-12-31'])
        run([sys.executable, args.avbtool, 'verify_image', '--image', image])
        result = image.read_bytes()
        parts = unpack(result)
        if len(result) != PARTITION_BYTES or struct.unpack_from('<I', result, 40)[0] != 1:
            raise SystemExit('Unexpected output size or header version.')
        if parts['kernel'] != template_parts['kernel'] or parts['dtbo'] != template_parts['dtbo']:
            raise SystemExit('Template boot components changed unexpectedly.')
        if lzma.decompress(parts['ramdisk']) != cpio:
            raise SystemExit('Output ramdisk contents changed unexpectedly.')
        shutil.copyfile(image, args.output)
    report = {'image': args.output.name, 'sha256': sha(result), 'bytes': len(result),
              'source_sha256': sha(source), 'official_template_url': TEMPLATE_URL,
              'template_zip_sha256': ZIP_SHA256, 'template_image_sha256': IMAGE_SHA256,
              'header_version': 1, 'ramdisk_compression': 'lzma', 'ramdisk_bytes': len(compressed),
              'uncompressed_cpio_sha256': sha(cpio), 'uncompressed_cpio_unchanged': True,
              'template_kernel_dtb_dtbo_unchanged': True, 'avb_signature_and_hash_verified': True,
              'boot_metadata': '99.87.36 / 2099-12-31 are inherited compatibility placeholders, not real OS/security versions.',
              'status': 'Uses the boot-tested packaging configuration; each newly compiled image still requires device testing.'}
    args.output.with_name(args.output.name + '.sha256').write_text(sha(result) + '  ' + args.output.name + '\n', encoding='ascii')
    args.output.with_name(args.output.name + '.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
