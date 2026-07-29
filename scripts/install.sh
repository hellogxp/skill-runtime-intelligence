#!/usr/bin/env sh
set -eu

repository="${SKILL_RUNTIME_REPOSITORY:-hellogxp/skill-runtime-intelligence}"
version="${SKILL_RUNTIME_VERSION:-latest}"
install_dir="${SKILL_RUNTIME_INSTALL_DIR:-${HOME}/.local/bin}"
binary_only=0
start_after_install=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --binary-only) binary_only=1 ;;
    --start) start_after_install=1 ;;
    *)
      echo "usage: install.sh [--binary-only] [--start]" >&2
      exit 2
      ;;
  esac
  shift
done
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.9 or newer is required." >&2
  exit 1
fi
if ! python3 -c 'import sys; raise SystemExit(sys.version_info < (3, 9))'; then
  echo "Python 3.9 or newer is required." >&2
  exit 1
fi

installer_tmp="$(mktemp -d "${TMPDIR:-/tmp}/skill-runtime-install.XXXXXX")"
trap 'rm -rf "$installer_tmp"' EXIT HUP INT TERM

if command -v curl >/dev/null 2>&1; then
  download() {
    curl --fail --silent --show-error --location --retry 3 \
      --output "$2" "$1"
  }
elif command -v wget >/dev/null 2>&1; then
  download() {
    wget --quiet --output-document="$2" "$1"
  }
else
  echo "curl or wget is required." >&2
  exit 1
fi

if [ -n "${SKILL_RUNTIME_RELEASE_BASE:-}" ]; then
  release_base="${SKILL_RUNTIME_RELEASE_BASE}"
elif [ "$version" = "latest" ]; then
  release_base="https://github.com/${repository}/releases/latest/download"
else
  release_base="https://github.com/${repository}/releases/download/${version}"
fi

download "${release_base}/skill-runtime.pyz" \
  "$installer_tmp/skill-runtime.pyz"
download "${release_base}/python-assets.sha256" \
  "$installer_tmp/python-assets.sha256"

(
  cd "$installer_tmp"
  grep ' skill-runtime.pyz$' python-assets.sha256 > skill-runtime.pyz.sha256
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum -c skill-runtime.pyz.sha256
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 -c skill-runtime.pyz.sha256
  else
    echo "sha256sum or shasum is required for release verification." >&2
    exit 1
  fi
) >/dev/null

mkdir -p "$install_dir"
install -m 755 "$installer_tmp/skill-runtime.pyz" "$install_dir/skill-runtime"
"$install_dir/skill-runtime" --help >/dev/null

echo "Installed Skill Runtime to $install_dir/skill-runtime"
case ":${PATH}:" in
  *":${install_dir}:"*) ;;
  *)
    profile=""
    case "${SHELL:-}" in
      */zsh) profile="${HOME}/.zshrc" ;;
      */bash) profile="${HOME}/.bashrc" ;;
    esac
    if [ -n "$profile" ] && [ "${SKILL_RUNTIME_NO_MODIFY_PATH:-0}" != "1" ]; then
      path_line="export PATH=\"${install_dir}:\$PATH\""
      if ! grep -F "$path_line" "$profile" >/dev/null 2>&1; then
        {
          echo ""
          echo "# Added by Skill Runtime installer"
          echo "$path_line"
        } >> "$profile"
      fi
      echo "Added $install_dir to PATH in $profile (applies to new shells)."
    else
      echo "Add $install_dir to PATH before using skill-runtime."
    fi
    ;;
esac

if [ "$binary_only" -eq 0 ]; then
  native_os=""
  native_arch=""
  case "$(uname -s 2>/dev/null || true)" in
    Darwin) native_os="darwin" ;;
    Linux) native_os="linux" ;;
  esac
  case "$(uname -m 2>/dev/null || true)" in
    x86_64|amd64) native_arch="x86_64" ;;
    arm64|aarch64) native_arch="arm64" ;;
  esac
  if [ -n "$native_os" ] && [ -n "$native_arch" ]; then
    native_asset="skill-runtime-hook-native-${native_os}-${native_arch}"
    download "${release_base}/${native_asset}" \
      "$installer_tmp/$native_asset"
    download "${release_base}/${native_asset}.sha256" \
      "$installer_tmp/$native_asset.sha256"
    checksum_ok=0
    if command -v sha256sum >/dev/null 2>&1; then
      (
        cd "$installer_tmp"
        sha256sum -c "$native_asset.sha256"
      ) >/dev/null && checksum_ok=1
    elif command -v shasum >/dev/null 2>&1; then
      (
        cd "$installer_tmp"
        shasum -a 256 -c "$native_asset.sha256"
      ) >/dev/null && checksum_ok=1
    fi
    if [ "$checksum_ok" -ne 1 ]; then
      echo "Native sender checksum verification failed." >&2
      exit 1
    fi
    state_root="${SKILL_RUNTIME_HOME:-${HOME}/.skill-runtime}"
    mkdir -p "$state_root/bin"
    install -m 700 "$installer_tmp/$native_asset" \
      "$state_root/bin/skill-runtime-hook-native"
  fi
  if ( : </dev/tty ) 2>/dev/null; then
    "$install_dir/skill-runtime" install </dev/tty
  else
    "$install_dir/skill-runtime" install
  fi
  if [ "$start_after_install" -eq 1 ]; then
    "$install_dir/skill-runtime" start
  else
    echo "Next: skill-runtime start"
  fi
fi
