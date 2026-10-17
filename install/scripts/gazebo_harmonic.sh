#!/usr/bin/env bash
# Gazebo Harmonic + ROS 2 Humble köprüsü (ros_gz), OSRF apt deposundan.
source "$(dirname "$0")/common.sh"

step "OSRF Gazebo deposu"
sudo apt-get install -y curl lsb-release gnupg
sudo curl -fsSL https://packages.osrfoundation.org/gazebo.gpg -o /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" \
  | sudo tee /etc/apt/sources.list.d/gazebo-stable.list >/dev/null

step "gz-harmonic"
sudo apt-get update
sudo apt-get install -y gz-harmonic

if [ -f /opt/ros/humble/setup.bash ]; then
  step "ros_gz köprüsü (ros-humble-ros-gzharmonic)"
  sudo apt-get install -y ros-humble-ros-gzharmonic
else
  echo "Not: ROS 2 yüklü değil, ros_gz köprüsü atlandı. ROS 2'den sonra bu adımı tekrar çalıştırın."
fi

mark_installed gazebo harmonic
step "Gazebo Harmonic hazır."
