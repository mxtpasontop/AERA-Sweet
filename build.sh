#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Run from a fresh Linux shell: bash /path/to/kit/build.sh /path/to/AERA_16.0
set -eo pipefail
kit_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source_root="${1:?Pass the path to an already-synced AERA Android 16 source tree}"
cd -- "$source_root"
for required in build/envsetup.sh bootable/recovery/aera_config.mk vendor/twrp/config/common.mk device/xiaomi/sweet/vendorsetup.sh; do
    if [[ ! -f "$required" ]]; then
        printf 'Missing required source: %s\n' "$required" >&2
        exit 1
    fi
done
# Read installed-ROM crypto properties through the logical partition devices.
qcom_root=device/qcom/twrp-common
crypto_patch="$kit_dir/ci/prepdecrypt-dynamic-paths.patch"
if git -C "$qcom_root" apply --reverse --check "$crypto_patch" 2>/dev/null; then
    printf 'Dynamic-partition crypto helper patch is already applied.\n'
else
    git -C "$qcom_root" apply --check "$crypto_patch"
    git -C "$qcom_root" apply "$crypto_patch"
fi
export AERA_BUILD_DEVICE=sweet
source build/envsetup.sh
lunch twrp_sweet-bp2a-eng
resolved_device="$(get_build_var TARGET_DEVICE)"
if [[ "$resolved_device" != sweet ]]; then
    printf 'Unexpected TARGET_DEVICE: %s\n' "$resolved_device" >&2
    exit 1
fi
# Low default parallelism; select JOBS for the actual builder.
m -j"${JOBS:-2}" --skip-ninja adbd recoveryimage
build_out="$(get_build_var OUT_DIR)"
python3 "$kit_dir/check_config_json.py" "$build_out/soong"
m -j"${JOBS:-2}" adbd recoveryimage
python3 "$kit_dir/check_image.py" "$build_out/target/product/sweet/recovery.img"
