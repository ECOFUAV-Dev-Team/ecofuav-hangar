#!/usr/bin/env bash
# px4_msgs'i PX4 sürümüyle eşleşen dala getirip ROS 2 çalışma alanında derler.
source "$(dirname "$0")/common.sh"
ROS_WS="${ROS_WS:-$HOME/iha_ws}"

if [ ! -f /opt/ros/humble/setup.bash ]; then
  echo "HATA: Önce ROS 2 Humble kurulmalı."
  exit 1
fi

mkdir -p "$ROS_WS/src"
git_checkout https://github.com/PX4/px4_msgs.git "$ROS_WS/src/px4_msgs" "$REQ_VERSION"

step "colcon build (sadece px4_msgs)"
set +u  # ROS setup betikleri tanımsız değişken kullanıyor
source /opt/ros/humble/setup.bash
set -u
cd "$ROS_WS"
colcon build --packages-select px4_msgs

mark_installed px4_msgs "$REQ_VERSION"
step "px4_msgs ($REQ_VERSION) hazır: $ROS_WS"
