#!/usr/bin/env bash
# Micro XRCE-DDS Agent'ı kaynaktan derleyip /usr/local'a kurar.
source "$(dirname "$0")/common.sh"
SRC="$HOME/.local/src/Micro-XRCE-DDS-Agent"

step "Derleme araçları"
sudo apt-get install -y git cmake build-essential

step "Kaynak kod ($REQ_VERSION)"
rm -rf "$SRC"
mkdir -p "$(dirname "$SRC")"
git clone --depth 1 --branch "$REQ_VERSION" https://github.com/eProsima/Micro-XRCE-DDS-Agent.git "$SRC"

step "Derleniyor"
cmake -S "$SRC" -B "$SRC/build"
cmake --build "$SRC/build" -j"$(nproc)"

step "Kuruluyor"
sudo cmake --install "$SRC/build"
sudo ldconfig /usr/local/lib/

mark_installed microxrce "$REQ_VERSION"
step "MicroXRCEAgent $REQ_VERSION hazır."
