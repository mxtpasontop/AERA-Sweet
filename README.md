# Initial AERA bring-up for Redmi Note 10 Pro (`sweet`)

Target ROM: LineageOS 23.2. Status: **source adaptation only, unbuilt and untested**.
This package contains a patch and setup/build helpers. It does not contain a recovery image or an installer ZIP. A successful source setup is not evidence that the phone will boot or decrypt.

## Device trees found

- TeamWin base: https://github.com/TeamWin/android_device_xiaomi_sweet/tree/android-12.1
- OrangeFox alternative: https://github.com/basamaryan/android_device_xiaomi_sweet-TWRP/tree/fox_12.1
- Matching ROM tree: https://github.com/LineageOS/android_device_xiaomi_sweet/tree/lineage-23.2
- Matching ROM common configuration: https://github.com/LineageOS/android_device_xiaomi_sm6150-common/tree/lineage-23.2
- AERA bring-up guide: https://aera-recovery.com/wiki/#bringup
- AERA manifest/build instructions: https://github.com/AERA-Recovery/android_manifest/tree/aera-16.0

The TeamWin base is pinned to `fa9c73d950de604bf5ac057ec0b93661f9d6bc60` (2023-11-15). It is a starting point, not proof of compatibility with LineageOS 23.2. The OrangeFox alternative was inspected at `ff50d886eafdb54989d1ddcd6dee5266fc5b50df`; it has a different kernel layout/header and must not be mixed into this tree piecemeal.

## Adaptation

- Uses the AERA public flag namespace, native interface geometry, and Android 16 product inheritance.
- Keeps the TeamWin kernel, DTB, DTBO, device init and USB adaptation. Boot header v2, 4096-byte pages, dedicated 128 MiB recovery; no A/B conversion.
- Aligns the dynamic group budget to LineageOS's 4 MiB super metadata reserve.
- Keeps wrapped-key FBE v2 and metadata encryption, matching LineageOS 23.2's UFS `/data` configuration.
- Removes compression-specific F2FS mount flags: the base kernel's embedded config has `CONFIG_F2FS_FS_COMPRESSION` disabled. LineageOS's current data fstab does not require those flags.
- Removes the fake `99.87.36` OS and `2099-12-31` patch values and the build-date reset service. Enables the common Qualcomm prepdecrypt path to obtain installed-ROM properties before starting crypto services.
- Removes requests for old Qualcomm display source modules/namespaces absent from AERA's manifest. The inherited vendor overlay remains. Hardware EGL/GLES and complete graphics dependency packaging are outstanding work.
- Marks the result Unofficial / Alpha. WLAN, cellular, root manager and fingerprint support remain disabled during the initial bring-up.

Existing copyright and license notices stay in the source. The package does not redistribute vendor binaries; setup fetches the unmodified upstream assets directly. Upstream assets retain their original licensing requirements.

## Prepare and build on Linux

Use a Linux builder with enough storage for the complete Android source and build output. The current Windows host initially had about 5 GB free, later increased to about 33 GB; no full source sync or build was attempted locally. WSL's virtual disk capacity does not add physical free space.

Install the Android build prerequisites and the `repo` tool on the builder, then initialize and sync AERA as documented upstream:

```bash
mkdir -p /path/to/AERA_16.0
cd /path/to/AERA_16.0
repo init -u https://github.com/AERA-Recovery/android_manifest.git -b aera-16.0
repo sync -c --no-clone-bundle --no-tags -j4
python3 /path/to/aera-sweet-bringup-kit/prepare_tree.py device/xiaomi/sweet
bash /path/to/aera-sweet-bringup-kit/build.sh /path/to/AERA_16.0
```

Setup refuses to overwrite an existing device tree. AERA's manifest tracks branches; save `repo manifest -r -o build-manifest.xml` alongside any resulting artifact to record the exact source revisions. The reference AERA revisions inspected for this adaptation were recovery `42ed6b66808200ce0d388bb0b4f05e4c2af4d207` and vendor/recovery `1f4b6e19882c83f95d1420872d0c31be0b97a7a6`.

The build helper uses `export AERA_BUILD_DEVICE=sweet` before envsetup and `lunch twrp_sweet-bp2a-eng`. It builds `adbd recoveryimage`, then checks the generated image's partition budget and basic header. It does not flash anything. Integration errors may still appear on the first full Android 16 build.

## Build with GitHub Actions

The repository root includes `.github/workflows/build-sweet.yml`. In GitHub, open **Actions → Build AERA for sweet → Run workflow** and select a job count (default 2). The workflow runs only when manually dispatched.

It reclaims unused tools on the disposable `ubuntu-24.04` hosted runner, installs build dependencies, shallow-syncs AERA, applies the pinned sweet patch, and builds the image. The artifact includes `AERA-sweet-UNTESTED.img`, its SHA-256, the exact synced manifest, port/upstream commit IDs, and logs. Logs are also uploaded on failure. Artifact retention is seven days. It does not publish a release or flash a phone.

The hosted-runner setup adds 12 GiB of swap. The workflow limits Go's memory target to 8 GiB and Go parallelism to two processes, and records host resources every 45 seconds during the build. These settings address limited runner resources; they do not replace device compatibility testing.

GitHub documents 14 GB of storage available on a standard Linux runner: https://docs.github.com/en/actions/reference/runners/github-hosted-runners . Cleanup reclaims optional preinstalled toolchains, but the amount recovered depends on the runner image. A 50 GiB post-cleanup preflight is an engineering budget, not a guarantee that this AERA build fits. If the sync/build exhausts space, use a larger configured Linux runner or a sufficiently provisioned self-hosted machine. Do not remove Android source directories speculatively to hide missing storage. `ci/prepare-runner.sh` refuses to run outside a GitHub-hosted Linux VM.

## Required before calling this a working port

1. Complete the full AERA build and resolve actual compile/link errors. Inspect the final ramdisk and vendor library dependencies, especially graphics and crypto.
2. Verify the resulting header, kernel and partition size against the phone's known-good recovery. Retain that recovery and a working bootloader restore route.
3. Test display, touch, brightness and ADB first using a device-supported nonpersistent boot route if available. A usable UI and accelerated GPU rendering are separate milestones.
4. On the exact LineageOS build, test skipped unlock, no-passcode and PIN/password unlock. Confirm filenames and file contents are readable. Do not format data to mask a decryption failure.
5. Verify read-only storage access, removable storage, USB, MTP, fastbootd and reboot paths; then test install and backup/restore on an appropriate test setup.
6. Bring up optional Wi-Fi, GPU acceleration, audio, cellular and other hardware separately using compatible firmware/libraries. Their availability on other AERA devices does not provide them on sweet.

Useful local evidence after an attempted recovery boot:

```bash
adb pull /tmp/recovery.log
adb logcat -d -b all > logcat.txt
adb shell dmesg > dmesg.txt
adb shell getprop > properties.txt
```

Review logs for personal data before sharing. Without a full build and real-device results, this remains an initial source adaptation.
