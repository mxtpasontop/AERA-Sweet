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
        for go_pid in $(pgrep -x soong_build || true); do
            if [[ -r "/proc/$go_pid/environ" ]]; then
                printf 'Soong runtime settings (PID %s):\n' "$go_pid"
                tr '\0' '\n' < "/proc/$go_pid/environ" | grep -E '^(GOGC|GOMEMLIMIT|GOMAXPROCS)=' || true
            fi
        done
        sleep 45
    done
) &
monitor_pid=$!
trap 'kill "$monitor_pid" 2>/dev/null || true' EXIT
bash "$kit_dir/build.sh" "$source_root"
