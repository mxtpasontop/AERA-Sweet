# Initial AERA bring-up for Redmi Note 10 Pro (`sweet`)

Target ROM: LineageOS 23.2. Status: **first Android 16 blind build completed; hardware untested**.
This source package contains a patch and setup/build helpers. The recovery image is a separate build artifact, not an installer ZIP. Compilation and structural checks do not establish that the phone will boot or decrypt.

The [successful build](https://github.com/mxtpasontop/AERA-Sweet/actions/runs/42661897740) used port commit `57c7c0f785cdd5069801cbabe5deca029f1ad88e`. Its `AERA-sweet-5-success` artifact contains `AERA-sweet-UNTESTED.img`, logs and the exact source manifest. GitHub artifact retention is seven days; retain a local copy. The image is 134,217,728 bytes including AVB padding, within the 128 MiB partition budget.

SHA-256: `8f338e944ef7176f2a87f6c06c1860664e452599c85ab271e78ed683d58a5a8e`

Local inspection verified the v2 header, 4096-byte pages, gzip ramdisk, and exact kernel/DTB/DTBO matches to the pinned TeamWin tree. Essential init, recovery, ADB and crypto paths are present. A library-name inventory found no missing dependency names in their static dependency chains; this does not verify linker namespaces, symbols or runtime behavior.

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

Known ramdisk dependency gaps: the inherited vibrator service and implementation request `android.hardware.vibrator-V1-ndk_platform.so`, which is absent. The legacy `libdisplayconfig.qti.so` and `libsecureui.so` request absent `vendor.display.config@2.0.so` and `vendor.display.config@1.0.so`, respectively. Haptics and these display/secure-UI paths need follow-up. These libraries were not on the inspected init/recovery/ADB/keymaster/gatekeeper static dependency chains; dynamically loaded paths and hardware behavior remain unverified. See `validation.json` for the inventory.

Existing copyright and license notices stay in the source. The package does not redistribute vendor binaries; setup fetches the unmodified upstream assets directly. Upstream assets retain their original licensing requirements.

## Prepare and build on Linux

Use a Linux builder with enough storage for the complete Android source and build output. The hosted build synced roughly 76 GiB of sources and required additional space for outputs and swap. WSL's virtual disk capacity does not add physical free space.

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

The build helper uses `export AERA_BUILD_DEVICE=sweet` before envsetup and `lunch twrp_sweet-bp2a-eng`. It first generates the build graph with `--skip-ninja` and validates the generated product-configuration JSON, then builds `adbd recoveryimage` and checks the image's partition budget and basic header. It does not flash anything. The full Android 16 build passed; future upstream changes may introduce new integration errors.

## Build with GitHub Actions

The repository root includes `.github/workflows/build-sweet.yml`. In GitHub, open **Actions → Build AERA for sweet → Run workflow** and select a job count (default 2). The workflow runs only when manually dispatched.

It reclaims unused tools on the disposable `ubuntu-24.04` hosted runner, installs build dependencies, shallow-syncs AERA, applies the pinned sweet patch, and builds the image. The artifact includes `AERA-sweet-UNTESTED.img`, its SHA-256, the exact synced manifest, port/upstream commit IDs, and logs. Logs are also uploaded on failure. Artifact retention is seven days. It does not publish a release or flash a phone.

The hosted-runner setup adds 12 GiB of swap. A narrow patch forwards `GOGC`, `GOMEMLIMIT` and `GOMAXPROCS` into Soong's otherwise empty builder environment. The workflow requests a 10 GiB Go memory target and concurrency of two, and records resources and the effective runtime settings every 45 seconds. The exact build-system patch is included in the artifacts. These settings address limited runner resources; they do not replace device compatibility testing.

GitHub documents 14 GB of storage available on a standard Linux runner: https://docs.github.com/en/actions/reference/runners/github-hosted-runners . Cleanup reclaims optional preinstalled toolchains, but the amount recovered depends on the runner image. A 50 GiB post-cleanup preflight is an engineering budget, not a guarantee that this AERA build fits. If the sync/build exhausts space, use a larger configured Linux runner or a sufficiently provisioned self-hosted machine. Do not remove Android source directories speculatively to hide missing storage. `ci/prepare-runner.sh` refuses to run outside a GitHub-hosted Linux VM.

## Required before calling this a working port

1. Resolve the known vendor dependency gaps and inspect runtime graphics and crypto behavior. The full build and initial ramdisk inventory have passed; this is not a hardware validation result.
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

Review logs for personal data before sharing. Until real-device validation is complete, this remains an untested initial bring-up.
