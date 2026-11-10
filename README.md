# AERA Recovery for Redmi Note 10 Pro (`sweet`)

Unofficial / Alpha, targeting LineageOS 23.2 / Android 16. **Boot, display, touch, ADB, metadata decryption and access to the owner's internal files were confirmed on 2026-11-10 with diagnostic 03.**

Tested image: `AERA-sweet-OFBASE-DIAG-03-CRYPTO.img`, 134,217,728 bytes including AVB padding.

SHA-256: `8cc2586fa216b5113e6b138cd654c4b50f20e525a39b9a4b40a0a5bc1445602e`

Recovery logs confirm the crypto helper completes, metadata maps to `/dev/block/mapper/userdata`, user 0 decrypts, and `/data` mounts as F2FS. The tester confirmed visible files. This establishes decryption on that installed setup; credential-protected PIN/password cases have not been separately characterized.

## What fixed bring-up

The final boot package uses header v1, 4096-byte pages, a kernel with appended DTB, embedded recovery DTBO, and an LZMA ramdisk. Boot components come together from the exact working OrangeFox R12.0_2 release. The kernel advertises `CONFIG_RD_LZMA=y`.

The original v2/gzip build and v1/gzip diagnostic returned to fastboot. Recompressing the identical AERA archive with LZMA reduced the compressed payload from 40,064,533 to 26,650,516 bytes and booted. No exact bootloader size limit has been established.

Decryption then failed because `prepdecrypt.sh` looked for physical `by-name/system` and `by-name/vendor` devices on a dynamic-partition ROM. `ci/prepdecrypt-dynamic-paths.patch` prefers existing mapper devices and retains physical-path fallback. Read-only checks verified the installed system/vendor properties through those mapper devices. Diagnostic 03 changes only that script inside diagnostic 02's ramdisk and successfully decrypts data. Earlier F2FS magic errors were from probing raw encrypted userdata before its metadata mapping existed; they did not establish filesystem corruption.

The boot container retains the working template's `99.87.36` / `2099-12-31` compatibility placeholders. **These are not the real Android version or security status.** The AERA userspace keeps its actual build properties; prepdecrypt reads the installed ROM's real properties before the `crypto.ready` service gate.

## Source and boot-template provenance

- Compile-tree base: [TeamWin sweet android-12.1](https://github.com/TeamWin/android_device_xiaomi_sweet/tree/android-12.1), pinned to `fa9c73d950de604bf5ac057ec0b93661f9d6bc60`, plus `aera-sweet.patch`.
- Recovery sources: [AERA Android 16 manifest](https://github.com/AERA-Recovery/android_manifest/tree/aera-16.0). Save the resolved manifest for each build. The tested userspace came from [run 42661897740](https://github.com/mxtpasontop/AERA-Sweet/actions/runs/42661897740), recovery revision `42ed6b66808200ce0d388bb0b4f05e4c2af4d207`.
- Boot baseline: [official OrangeFox R12.0_2 for sweet](https://orangefox.download/release/6a107f7a192e80d0717207e1), maintained by Mostafameesr. The publisher's ZIP and image MD5 values were checked, and SHA-256 pins are enforced by the packager.
- ZIP SHA-256: `5ba70d54d69ad40b1c874d29ca90da69f26e384db174bdae31f149577923d42c`.
- Embedded template image SHA-256: `91b1b7bc78d5b7499aff608f6a98f9e9a7f44021595648216abdabcf3dd25666`.
- Matching ROM trees: [sweet](https://github.com/LineageOS/android_device_xiaomi_sweet/tree/lineage-23.2) and [sm6150-common](https://github.com/LineageOS/android_device_xiaomi_sm6150-common/tree/lineage-23.2).

This repository stores patches and tools, not redistributed vendor/prebuilt binaries. Setup and packaging fetch upstream assets directly. Existing authorship and licensing notices remain; upstream assets retain their licensing requirements. An older inspected OrangeFox device tree had different binaries and is not a substitute for the pinned release.

## GitHub Actions

Open **Actions → Build AERA for sweet → Run workflow** and choose a job count. Four jobs were used for the successful full compilation. The workflow is manual, uses standard `ubuntu-24.04`, and does not flash a phone or publish a release.

The workflow:

1. Reclaims optional tools on the disposable hosted runner, adds 12 GiB swap, and syncs AERA.
2. Applies the pinned device patch and narrowly forwards Go resource settings into Soong's otherwise isolated environment.
3. Applies the dynamic-partition crypto helper patch idempotently, generates the build graph, checks product JSON, and compiles `adbd recoveryimage`.
4. Downloads the pinned official OrangeFox ZIP and runs `package_boot.py`, preserving the compiled AERA ramdisk contents while using the tested v1/LZMA boot packaging.
5. Verifies the final AVB signature/hash, component identity, CPIO roundtrip and 128 MiB budget. Uploads image, checksum, packaging report, source revisions, exact patches and logs. Retention is seven days.

The intermediate v2/gzip image in the Android output directory is a compile artifact; use the final packaged artifact. Newly compiled images remain named `AERA-sweet-UNTESTED.img` because the tested configuration does not automatically validate every future source revision.

The updated workflow passes actionlint and shell syntax checks. The packager was exercised on real CI output and reproduced diagnostic 02 exactly; it also reproduced the boot/touch/decryption-tested diagnostic 03 byte-for-byte. The complete updated workflow has not yet been rerun end-to-end.

## Build and package on Linux

Sync AERA as documented [upstream](https://aera-recovery.com/wiki/#bringup), then from its source root:

```bash
python3 /path/to/kit/prepare_tree.py device/xiaomi/sweet
bash /path/to/kit/build.sh "$PWD"
curl --fail --location --retry 3 \
  https://dl.orangefox.download/6a107f7a192e80d0717207e1 \
  -o /path/to/OrangeFox-R12.0_2-sweet.zip
python3 /path/to/kit/package_boot.py \
  --aera out/target/product/sweet/recovery.img \
  --template-zip /path/to/OrangeFox-R12.0_2-sweet.zip \
  --mkbootimg system/tools/mkbootimg/mkbootimg.py \
  --avbtool external/avb/avbtool.py \
  --key external/avb/test/data/testkey_rsa4096.pem \
  --output /path/to/AERA-sweet-UNTESTED.img
repo manifest -r -o /path/to/build-manifest.xml
```

Python 3, OpenSSL, Git and the normal Android build dependencies are required. Setup refuses an existing device-tree destination; packaging refuses to overwrite an existing output. The full source sync used roughly 76 GiB, with additional space needed for output and swap. The build helper selects `twrp_sweet-bp2a-eng` and keeps wrapped-key FBE v2/metadata encryption and the dedicated 128 MiB A-only recovery layout. Nothing here formats or flashes a phone.

## Remaining limitations

- WLAN, cellular, fingerprint and Root Manager are disabled.
- Haptics and legacy display/secure-UI blobs have unresolved dependency names: `android.hardware.vibrator-V1-ndk_platform.so`, `vendor.display.config@1.0.so` and `vendor.display.config@2.0.so`. Core UI and decryption work on the tested device; these other paths need follow-up.
- Hardware GPU acceleration and audio are unverified. A visible UI does not establish either.
- MTP, fastbootd, ZIP/image installation, backup/restore, removable storage and all reboot paths have not been validated in this bring-up. Do not treat boot success as proof those operations work.
- The current tester reports temporary `fastboot boot` is broken on this phone. Recovery-partition boot was used for validation; keep a known-working recovery and the ROM-matched DTBO.

Raw device logs remain local because they can contain identifiers and filenames. `validation.json` contains sanitized evidence and the tested artifact hashes.
