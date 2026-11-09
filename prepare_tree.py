#!/usr/bin/env python3
"""Fetch the pinned TeamWin sweet tree and apply the initial AERA adaptation."""
import argparse
import pathlib
import subprocess

BASE_URL = 'https://github.com/TeamWin/android_device_xiaomi_sweet.git'
BASE_SHA = 'fa9c73d950de604bf5ac057ec0b93661f9d6bc60'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=pathlib.Path,
                        help='new device tree path, normally AERA_16.0/device/xiaomi/sweet')
    args = parser.parse_args()
    dest = args.destination.resolve()
    patch = pathlib.Path(__file__).resolve().with_name('aera-sweet.patch')
    if dest.exists():
        parser.error('Destination already exists; choose a new path. Existing work is never replaced.')
    if not patch.is_file():
        parser.error('aera-sweet.patch must be next to this script.')
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['git', 'clone', '--no-checkout', '--depth', '1', '--branch',
                    'android-12.1', BASE_URL, str(dest)], check=True)
    subprocess.run(['git', '-C', str(dest), 'config', 'core.autocrlf', 'false'], check=True)
    subprocess.run(['git', '-C', str(dest), 'fetch', '--depth', '1', 'origin', BASE_SHA], check=True)
    subprocess.run(['git', '-C', str(dest), 'checkout', '--detach', BASE_SHA], check=True)
    subprocess.run(['git', '-C', str(dest), 'apply', '--check', str(patch)], check=True)
    subprocess.run(['git', '-C', str(dest), 'apply', str(patch)], check=True)
    print('Initial AERA source adaptation created at', dest)
    print('UNBUILT / UNTESTED. No flashable recovery image has been produced.')

if __name__ == '__main__':
    main()
