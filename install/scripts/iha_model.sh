#!/usr/bin/env bash
# Takımın İHA modelini (sim/px4) PX4-Autopilot'a kopyalar ve gz_iha hedefini kaydeder.
# Kurulum sayfasından ve PX4 modülü başlamadan önce çalışır; değişiklik yoksa hiçbir şey yapmaz.
set -euo pipefail
HANGAR_DIR="${HANGAR_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
PX4_DIR="${PX4_DIR:-$HOME/PX4-Autopilot}"
PX4_DIR="${PX4_DIR/#\~/$HOME}"

SRC="$HANGAR_DIR/sim/px4"
AIRFRAME=4900_gz_iha
MODEL_DST="$PX4_DIR/Tools/simulation/gz/models/iha"
AIRFRAME_DIR="$PX4_DIR/ROMFS/px4fmu_common/init.d-posix/airframes"
BUILD_DIR="$PX4_DIR/build/px4_sitl_default"

[ -d "$AIRFRAME_DIR" ] || { echo "HATA: PX4-Autopilot bulunamadı: $PX4_DIR"; exit 1; }

# 4900 başka bir airframe'e ait olmasın (4010 x500_mono_cam ile çakıştığı için 4900 seçildi).
other=$(ls "$AIRFRAME_DIR" | grep '^4900_' | grep -vx "$AIRFRAME" || true)
[ -z "$other" ] || { echo "HATA: 4900 airframe numarası çakışıyor: $other"; exit 1; }

mkdir -p "$MODEL_DST"
if ! diff -rq "$SRC/models/iha" "$MODEL_DST" >/dev/null 2>&1; then
  cp -r "$SRC/models/iha/." "$MODEL_DST/"
  echo "[iha] model://iha güncellendi"
fi
if ! cmp -s "$SRC/airframes/$AIRFRAME" "$AIRFRAME_DIR/$AIRFRAME"; then
  cp "$SRC/airframes/$AIRFRAME" "$AIRFRAME_DIR/$AIRFRAME"
  echo "[iha] $AIRFRAME güncellendi"
fi
if ! grep -qx "\s*$AIRFRAME" "$AIRFRAME_DIR/CMakeLists.txt"; then
  sed -i "s/^\(\s*\)4001_gz_x500$/&\n\1$AIRFRAME/" "$AIRFRAME_DIR/CMakeLists.txt"
  grep -q "$AIRFRAME" "$AIRFRAME_DIR/CMakeLists.txt" || { echo "HATA: $AIRFRAME CMakeLists.txt'ye eklenemedi"; exit 1; }
  echo "[iha] $AIRFRAME airframe listesine eklendi"
fi
# Önceden derlenmiş build yeni airframe'i bilmiyorsa gz_iha hedefi oluşsun diye yeniden yapılandır.
if [ -f "$BUILD_DIR/build.ninja" ] && ! grep -q "$AIRFRAME" "$BUILD_DIR/build.ninja"; then
  echo "[iha] PX4 build yeniden yapılandırılıyor"
  cmake "$BUILD_DIR" >/dev/null
fi
echo "[iha] Model hazır (gz_iha)"
