#!/usr/bin/env bash
#
# download-eicar.sh – fetch EICAR test files via HTTPS
# Created by https://github.com/PinePad79
# List of EICAR test-file URLs
URLS=(
  # 1) The standard .com executable (68-byte DOS program)
  https://secure.eicar.org/eicar.com
  # 2) The same file renamed as a .txt
  https://secure.eicar.org/eicar.com.txt
  # 3) Single-level ZIP archive containing eicar.com
  https://secure.eicar.org/eicar_com.zip
  # 4) Double-level ZIP (zip-in-zip) for recursive scanning tests
  https://secure.eicar.org/eicar_com2.zip
)

# Where to save them (current directory by default)
DEST="./"

# Loop and download
for url in "${URLS[@]}"; do
  echo "Downloading $url..."
  wget --https-only --content-disposition --directory-prefix="$DEST" "$url" \
    && echo "→ Saved to $DEST" \
    || echo "‼ Failed to download $url"
done