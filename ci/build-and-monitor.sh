#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -eo pipefail
kit_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
source_root="${1:?Pass the synced AERA source directory}"
(
    while true; do
        printf '\n--- Build host resources at %s ---\n' "$(date -u +%FT%TZ)"
        free -h
        df -h "$source_root"
        ps -eo pid,comm,rss --sort=-rss | sed -n '1,8p'
        sleep 45
    done
) &
monitor_pid=$!
trap 'kill "$monitor_pid" 2>/dev/null || true' EXIT
bash "$kit_dir/build.sh" "$source_root"
