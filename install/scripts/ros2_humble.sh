#!/usr/bin/env bash
# ROS 2 Humble kurulumu (resmi apt deposu). Ubuntu 22.04 gerekir.
source "$(dirname "$0")/common.sh"

. /etc/os-release
if [ "$VERSION_CODENAME" != "jammy" ]; then
  echo "HATA: ROS 2 Humble Ubuntu 22.04 (jammy) ister, bu sistem: $PRETTY_NAME"
  exit 1
fi

step "Temel paketler ve locale"
sudo apt-get update
sudo apt-get install -y locales software-properties-common curl
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
sudo add-apt-repository -y universe

if ! dpkg -s ros2-apt-source >/dev/null 2>&1 && [ ! -f /etc/apt/sources.list.d/ros2.list ]; then
  step "ROS 2 apt deposu ekleniyor"
  ver=$(curl -fsSL https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F '"tag_name"' | awk -F'"' '{print $4}')
  tmp=$(mktemp -d)
  curl -fL -o "$tmp/ros2-apt-source.deb" \
    "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ver}/ros2-apt-source_${ver}.${VERSION_CODENAME}_all.deb"
  sudo dpkg -i "$tmp/ros2-apt-source.deb"
fi

step "ROS 2 Humble paketleri"
sudo apt-get update
sudo apt-get install -y ros-humble-desktop ros-dev-tools

if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
  step "rosdep"
  sudo rosdep init
fi
rosdep update

mark_installed ros2 humble
step "ROS 2 Humble hazır."
