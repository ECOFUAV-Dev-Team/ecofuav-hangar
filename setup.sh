#!/usr/bin/env bash
# ECOFUAV Hangar'ı kurar: sanal ortam, bağımlılıklar ve uygulama menüsü kısayolu.
set -euo pipefail
APP_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Sistem paketleri"
sudo apt-get install -y python3-venv python3-pip libxcb-cursor0 git

echo "==> Python sanal ortamı"
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

echo "==> Kısayollar"
mkdir -p "$HOME/.local/bin" "$HOME/.local/share/applications"
cat > "$HOME/.local/bin/ecofuav-hangar" <<SH
#!/bin/sh
exec "$APP_DIR/.venv/bin/python" "$APP_DIR/main.py" "\$@"
SH
chmod +x "$HOME/.local/bin/ecofuav-hangar"

cat > "$HOME/.local/share/applications/ecofuav-hangar.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=ECOFUAV Hangar
Comment=Gazebo / PX4 / ROS 2 kontrol paneli
Exec=$HOME/.local/bin/ecofuav-hangar
Icon=$APP_DIR/assets/icon.svg
Terminal=false
Categories=Development;
DESKTOP

echo
echo "Kurulum tamam. Uygulama menüsünden 'ECOFUAV Hangar'ı açabilir"
echo "ya da terminalden 'ecofuav-hangar' yazabilirsiniz."
