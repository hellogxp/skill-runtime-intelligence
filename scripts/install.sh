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
  "$install_dir/skill-runtime" install
  echo "Next: skill-runtime start"
fi
