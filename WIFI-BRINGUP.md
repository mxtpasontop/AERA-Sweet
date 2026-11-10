# Wi-Fi bring-up in progress

This branch enables AERA's native WLAN code and supplicant packages for compilation. Cellular remains disabled. The tested boot/touch/decryption baseline remains on `main`.

The known-working kernel includes qcacld/ICNSS and `/dev/wlan`; an external Wi-Fi module is not needed. Firmware is available read-only from the installed modem firmware partition, and Wi-Fi configuration/services are available from the installed vendor partition.

Runtime investigation is still in progress. Recovery needs the firmware mount and the correct Qualcomm namespace, firmware/calibration and driver startup sequence. A partial DSP startup hit a sensor user-PD watchdog and reset the phone; the complete companion-service setup must be established before repeating it. Test configuration and CNSS writes were isolated in RAM; original Android Wi-Fi data and persist were not modified.

The initial build on this branch provides the WLAN-enabled userspace for integration. **It does not yet establish working Wi-Fi and should not be treated as a validated networking build.** Driver initialization, scanning, association, DHCP, DNS and USB coexistence still require tests. Raw device/network logs remain local.
