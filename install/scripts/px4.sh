#!/usr/bin/env bash
# PX4-Autopilot'u takım sürümüne getirir, bağımlılıkları kurar ve SITL'i derler.
source "$(dirname "$0")/common.sh"
PX4_DIR="${PX4_DIR:-$HOME/PX4-Autopilot}"

# Kurulum yarıda kalırsa eski işaret "güncel" göstermesin.
rm -f "$HANGAR_MARKER_DIR/px4"

git_checkout https://github.com/PX4/PX4-Autopilot.git "$PX4_DIR" "$REQ_VERSION" --recursive

step "PX4 bağımlılıkları (Tools/setup/ubuntu.sh) — uzun sürebilir"
bash "$PX4_DIR/Tools/setup/ubuntu.sh"

step "SITL derleniyor (px4_sitl)"
cd "$PX4_DIR"
# Model hedefi (gz_x500_mono_cam) simülasyonu başlatır; v1.15 DONT_RUN desteklemez, sadece derle.
make px4_sitl

step "Pixhawk 6C firmware derleniyor (px4_fmu-v6c)"
# ubuntu.sh derleyiciyi ~/.profile ile PATH'e ekler; oturum yenilenmeden de bulunsun.
for d in /opt/gcc-arm-none-eabi-*/bin; do [ -d "$d" ] && export PATH="$d:$PATH"; done
make px4_fmu-v6c_default || echo "UYARI: 6C firmware derlenemedi; SITL yine de hazır."

mark_installed px4 "$REQ_VERSION"
step "PX4 $REQ_VERSION hazır. Seri port izni (dialout) için bir kez oturumu kapatıp açın."
