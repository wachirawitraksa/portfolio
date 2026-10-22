#!/bin/sh
# Builds the admin stylesheet (app/static/admin.css) from css/input.css with the Tailwind standalone CLI
# and daisyUI. No Node is needed here or in the api container: run this on your machine after changing a template
# or css/input.css, and commit the generated file.
#
#   scripts/build_css.sh            build once
#   scripts/build_css.sh --watch    rebuild on every change
#
# The two tools are downloaded once into tools/ (ignored by git and by Docker) at the pinned versions below.
set -eu
cd "$(dirname "$0")/.."

TAILWIND=4.3.3
DAISYUI=5.7.50

case "$(uname -s)-$(uname -m)" in
  Linux-x86_64) BIN=tailwindcss-linux-x64 ;;
  Linux-aarch64 | Linux-arm64) BIN=tailwindcss-linux-arm64 ;;
  Darwin-arm64) BIN=tailwindcss-macos-arm64 ;;
  Darwin-x86_64) BIN=tailwindcss-macos-x64 ;;
  MINGW* | MSYS* | CYGWIN*) BIN=tailwindcss-windows-x64.exe ;;
  *) echo "No Tailwind standalone build for $(uname -s) $(uname -m)" >&2; exit 1 ;;
esac

TOOLS=tools
mkdir -p "$TOOLS"
case "$BIN" in *.exe) CLI="$TOOLS/tailwindcss-$TAILWIND.exe" ;; *) CLI="$TOOLS/tailwindcss-$TAILWIND" ;; esac

fetch() { # url file
  curl -fsSL --retry 2 -o "$2.part" "$1" && mv "$2.part" "$2"
}

if [ ! -x "$CLI" ]; then
  echo "Downloading Tailwind CSS $TAILWIND ($BIN) ..."
  base="https://github.com/tailwindlabs/tailwindcss/releases/download/v$TAILWIND"
  fetch "$base/$BIN" "$CLI"
  # Check the download against the checksum the release publishes.
  expected=$(curl -fsSL "$base/sha256sums.txt" | awk -v f="./$BIN" '$2 == f { print $1 }')
  if command -v sha256sum >/dev/null 2>&1; then actual=$(sha256sum "$CLI" | cut -d' ' -f1); else actual=$(shasum -a 256 "$CLI" | cut -d' ' -f1); fi
  if [ -z "$expected" ] || [ "$expected" != "$actual" ]; then rm -f "$CLI"; echo "Checksum mismatch for $BIN" >&2; exit 1; fi
  chmod +x "$CLI"
fi

for file in daisyui.mjs daisyui-theme.mjs; do
  target="$TOOLS/$DAISYUI-$file"
  if [ ! -f "$target" ]; then
    echo "Downloading daisyUI $DAISYUI ($file) ..."
    fetch "https://github.com/saadeghi/daisyui/releases/download/v$DAISYUI/$file" "$target"
  fi
  cp "$target" "$TOOLS/$file"  # css/input.css names the plain file; the versioned copy is what is checked
done

exec "$CLI" -i css/input.css -o app/static/admin.css --minify "$@"
