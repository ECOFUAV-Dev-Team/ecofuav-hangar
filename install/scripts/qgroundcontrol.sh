#!/usr/bin/env bash
# QGroundControl AppImage'ını indirir ve gerekli sistem ayarlarını yapar.
source "$(dirname "$0")/common.sh"
QGC_PATH="${QGC_PATH:-$HOME/QGroundControl.AppImage}"

step "Seri port izni ve bağımlılıklar"
sudo usermod -aG dialout "$USER"
sudo apt-get remove -y modemmanager || true
sudo apt-get install -y gstreamer1.0-plugins-bad gstreamer1.0-libav gstreamer1.0-gl \
  libfuse2 libxcb-xinerama0 libxkbcommon-x11-0 libxcb-cursor0

step "QGroundControl $REQ_VERSION indiriliyor"
curl -fL -o "$QGC_PATH.tmp" \
  "https://github.com/mavlink/qgroundcontrol/releases/download/${REQ_VERSION}/QGroundControl.AppImage"
mv "$QGC_PATH.tmp" "$QGC_PATH"
chmod +x "$QGC_PATH"

mark_installed qgc "$REQ_VERSION"
step "QGroundControl hazır: $QGC_PATH (dialout izni için oturumu bir kez kapatıp açın)"
