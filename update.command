#!/bin/bash
# Storage Screener - one-click updater for macOS.
# Downloads the latest version and swaps in the new files. Your saved listings
# and installed setup are kept. After it finishes, run start.command as usual.

cd "$(dirname "$0")" || exit 1

echo "============================================"
echo "   Updating Storage Screener"
echo "============================================"
echo
echo "Downloading the latest version..."

if ! curl -fL -o update.zip "https://github.com/davidgscott/properties/archive/refs/heads/main.zip"; then
  echo
  echo "Update failed to download. Check your internet connection and try again."
  read -r -p "Press Return to close."
  exit 1
fi

rm -rf update_tmp
if ! unzip -q update.zip -d update_tmp; then
  echo "Could not unpack the update."
  rm -f update.zip
  read -r -p "Press Return to close."
  exit 1
fi

echo "Installing new files..."
# Copy the new files over the current folder. Files that aren't in the download
# (your .venv setup and saved listings in app/data) are left untouched.
cp -R update_tmp/properties-main/. .
rm -rf update_tmp update.zip
chmod +x start.command update.command 2>/dev/null

echo
echo "Update complete!"
echo "Now double-click start.command to run it, and refresh your browser."
read -r -p "Press Return to close."
