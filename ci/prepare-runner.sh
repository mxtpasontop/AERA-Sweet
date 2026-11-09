#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Only for fresh, disposable GitHub-hosted Linux runner VMs.
set -euo pipefail
if [[ "${GITHUB_ACTIONS:-}" != true || "${RUNNER_ENVIRONMENT:-}" != github-hosted ]]; then
    echo 'Refusing hosted-runner cleanup outside a GitHub-hosted Actions VM.' >&2
    exit 1
fi
if [[ "${RUNNER_OS:-}" != Linux ]]; then
    echo 'This build requires a Linux runner.' >&2
    exit 1
fi
df -h /
# Fixed paths for optional toolchains unused by this recovery build.
# These removals never run on the developer PC or a self-hosted runner.
sudo rm -rf -- /usr/local/lib/android /usr/share/dotnet /opt/ghc /usr/local/.ghcup /opt/microsoft/powershell
sudo docker image prune --all --force
sudo apt-get clean
# Give the Android build graph more headroom on a standard 16 GB runner.
swap_file="${RUNNER_TEMP:?RUNNER_TEMP is required}/aera-build.swap"
if [[ -e "$swap_file" ]]; then
    echo 'Refusing to overwrite an existing swap file.' >&2
    exit 1
fi
sudo fallocate -l 12G "$swap_file"
sudo chmod 600 "$swap_file"
sudo mkswap "$swap_file"
sudo swapon "$swap_file"
free -h
df -h /
available_bytes="$(df --output=avail -B1 . | tail -n1 | tr -d ' ')"
# Engineering preflight budget, not an upstream guaranteed space requirement.
if (( available_bytes < 50 * 1024 * 1024 * 1024 )); then
    echo 'Less than 50 GiB free after cleanup. Use a runner with more storage.' >&2
    exit 1
fi
