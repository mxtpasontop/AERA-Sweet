#!/usr/bin/env python3
"""Validate generated product configuration before native compilation."""
import argparse
import json
import pathlib

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('soong_directory',type=pathlib.Path)
    args=parser.parse_args()
    for name in ['soong.twrp_sweet.variables','soong.twrp_sweet.extra.variables']:
        path=args.soong_directory/name
        try:
            with path.open(encoding='utf-8') as handle:
                config=json.load(handle)
        except (OSError,json.JSONDecodeError) as error:
            raise SystemExit('Invalid generated configuration {}: {}'.format(path,error))
        if not isinstance(config,dict):
            raise SystemExit('Expected a JSON object in '+str(path))
        if name.endswith('.extra.variables') and config.get('RecoveryPixelFormat')!='RGBX_8888':
            raise SystemExit('Unexpected RecoveryPixelFormat in '+str(path))
        print('PASS: generated configuration JSON:',name)

if __name__=='__main__':
    main()
