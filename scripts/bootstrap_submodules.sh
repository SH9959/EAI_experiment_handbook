#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
clone_if_missing() {
  local url="$1"; local dst="$2"
  if [ -d "$dst/.git" ] || [ -f "$dst/.git" ]; then
    echo "[skip] $dst already initialized"
  else
    rm -rf "$dst"
    mkdir -p "$(dirname "$dst")"
    echo "[clone] $url -> $dst"
    git clone "$url" "$dst"
  fi
}
clone_if_missing https://github.com/alfworld/alfworld.git "$ROOT/chapter_4/4_1_task_planning/for_benchmark/alfworld"
clone_if_missing https://github.com/askforalfred/alfred.git "$ROOT/chapter_4/4_1_task_planning/for_benchmark/alfred"
clone_if_missing https://github.com/xavierpuigf/virtualhome.git "$ROOT/chapter_4/4_1_task_planning/for_simulator/for_virtualhome/virtualhome"
echo "Done. Note: VirtualHome Unity executable still needs to be downloaded separately."
