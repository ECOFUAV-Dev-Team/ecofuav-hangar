# Tüm kurulum betiklerinin ortak başlangıcı. "source" ile kullanılır.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

# Uygulamadan çalışırken terminal yok; sudo şifreyi grafik pencereden istesin.
# export -f sayesinde alt betikler (ör. PX4 ubuntu.sh) de aynı davranışı alır.
if [ -n "${SUDO_ASKPASS:-}" ] && [ ! -t 0 ]; then
  sudo() { command sudo -A "$@"; }
  export -f sudo
fi

REQ_VERSION="${REQ_VERSION:?REQ_VERSION tanımlı değil}"
HANGAR_MARKER_DIR="${HANGAR_MARKER_DIR:-$HOME/.local/share/ecofuav-hangar/installed}"

step() { printf '\n==> %s\n' "$*"; }

mark_installed() {  # mark_installed <bileşen> <sürüm>
  mkdir -p "$HANGAR_MARKER_DIR"
  echo "$2" > "$HANGAR_MARKER_DIR/$1"
}

# Git deposunu klonlar ya da istenen tag/dala getirir. Yerel değişiklik varsa durur.
git_checkout() {  # git_checkout <url> <klasör> <tag/dal> [--recursive]
  local url="$1" dir="$2" ref="$3" recursive="${4:-}"
  if [ ! -d "$dir/.git" ]; then
    step "$url klonlanıyor ($ref)"
    git clone ${recursive:+--recursive} --branch "$ref" "$url" "$dir"
    return
  fi
  if [ -n "$(git -C "$dir" status --porcelain --untracked-files=no)" ]; then
    echo "HATA: $dir içinde commit edilmemiş değişiklikler var. Kaybolmasınlar diye durduruldu."
    echo "      Değişiklikleri commit/stash edip tekrar deneyin."
    exit 1
  fi
  step "$dir → $ref"
  git -C "$dir" fetch --tags origin
  if git -C "$dir" show-ref --verify --quiet "refs/remotes/origin/$ref"; then
    git -C "$dir" checkout "$ref"
    git -C "$dir" merge --ff-only "origin/$ref"
  else
    git -C "$dir" checkout "$ref"
  fi
  if [ -n "$recursive" ]; then
    git -C "$dir" submodule sync --recursive
    git -C "$dir" submodule update --init --recursive
  fi
}
