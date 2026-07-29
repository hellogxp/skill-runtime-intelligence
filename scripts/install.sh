#!/usr/bin/env sh
set -eu

repository="${SKILL_RUNTIME_REPOSITORY:-hellogxp/skill-runtime-intelligence}"
version="${SKILL_RUNTIME_VERSION:-latest}"
install_dir="${SKILL_RUNTIME_INSTALL_DIR:-${HOME}/.local/bin}"
binary_only=0

if [ "${1:-}" = "--binary-only" ]; then
  binary_only=1
  shift
fi
if [ "$#" -ne 0 ]; then
  echo "usage: install.sh [--binary-only]" >&2
  exit 2
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.9 or newer is required." >&2
  exit 1
fi
if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI is required to download the authenticated release." >&2
  exit 1
fi

installer_tmp="$(mktemp -d "${TMPDIR:-/tmp}/skill-runtime-install.XXXXXX")"
trap 'rm -rf "$installer_tmp"' EXIT HUP INT TERM

release_args="--repo ${repository}"
if [ "$version" != "latest" ]; then
  release_args="${version} ${release_args}"
fi
# shellcheck disable=SC2086
gh release download $release_args --pattern "skill-runtime.pyz" --dir "$installer_tmp"

mkdir -p "$install_dir"
install -m 755 "$installer_tmp/skill-runtime.pyz" "$install_dir/skill-runtime"
"$install_dir/skill-runtime" --help >/dev/null

echo "Installed Skill Runtime to $install_dir/skill-runtime"
case ":${PATH}:" in
  *":${install_dir}:"*) ;;
  *) echo "Add $install_dir to PATH before using skill-runtime." ;;
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
    # shellcheck disable=SC2086
    gh release download $release_args \
      --pattern "$native_asset" \
      --pattern "$native_asset.sha256" \
      --dir "$installer_tmp"
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
  "$install_dir/skill-runtime" install
  echo "Next: skill-runtime start"
fi
