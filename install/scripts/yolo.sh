#!/usr/bin/env bash
# Ultralytics (YOLOv11 + BoT-SORT takipçisi) kurulumu.
source "$(dirname "$0")/common.sh"

if [ "$(uname -m)" = "aarch64" ]; then
  echo "HATA: Jetson'da PyTorch'u pip'ten değil, JetPack'e uygun NVIDIA wheel'lerinden kurun."
  echo "      Ardından: pip3 install --user ultralytics==$REQ_VERSION 'numpy<2' lap"
  exit 1
fi

step "pip"
sudo apt-get install -y python3-pip

step "ultralytics $REQ_VERSION (PyTorch dahil, birkaç GB indirebilir)"
# numpy<2: ROS 2 Humble'ın cv_bridge'i numpy 2 ile çalışmaz.
python3 -m pip install --user "ultralytics==$REQ_VERSION" "numpy<2" "lap>=0.5.12"

mark_installed yolo "$REQ_VERSION"
step "Ultralytics hazır."
