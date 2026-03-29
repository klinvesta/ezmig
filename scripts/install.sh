#!/bin/sh
set -eu

if [ "$(uname -s)" != "Linux" ]; then
  echo "Error: this installer currently supports Linux only." >&2
  exit 1
fi

ARCH="$(uname -m)"
case "$ARCH" in
  x86_64|amd64)
    ASSET="ezmig-linux-amd64"
    ;;
  *)
    echo "Error: unsupported Linux architecture: $ARCH" >&2
    echo "Supported architectures: x86_64/amd64" >&2
    exit 1
    ;;
esac

BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
REPO="${REPO:-klinvesta/ezmig}"
VERSION="${VERSION:-latest}"
BINARY_NAME="${BINARY_NAME:-ezmig}"

mkdir -p "$BIN_DIR"

if [ "$VERSION" = "latest" ]; then
  DOWNLOAD_URL="https://github.com/$REPO/releases/latest/download/$ASSET"
else
  DOWNLOAD_URL="https://github.com/$REPO/releases/download/$VERSION/$ASSET"
fi

TMP_FILE="$(mktemp)"
trap 'rm -f "$TMP_FILE"' EXIT INT TERM

if ! command -v curl >/dev/null 2>&1; then
  echo "Error: curl is required but was not found on PATH." >&2
  exit 1
fi

echo "Downloading $DOWNLOAD_URL"
curl -fsSL "$DOWNLOAD_URL" -o "$TMP_FILE"
chmod +x "$TMP_FILE"
mv "$TMP_FILE" "$BIN_DIR/$BINARY_NAME"

echo "Installed $BINARY_NAME to $BIN_DIR/$BINARY_NAME"

case ":$PATH:" in
  *":$BIN_DIR:"*)
    ;;
  *)
    echo "Warning: $BIN_DIR is not on your PATH." >&2
    echo "Add this to your shell profile:" >&2
    echo "  export PATH=\"$BIN_DIR:\$PATH\"" >&2
    ;;
esac
