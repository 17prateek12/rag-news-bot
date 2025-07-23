#!/usr/bin/env bash

echo "🔧 Starting build process..."

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Patch `six.moves._thread` issue in all relevant tz.py files
echo "🩹 Looking for 'six.moves._thread' import in dateutil tz.py files..."

find server -type f -name "tz.py" | while read -r file; do
  if grep -q "from six.moves import _thread" "$file"; then
    echo "⚠️ Found and patching: $file"
    sed -i 's/from six.moves import _thread/import _thread/' "$file"
    echo "✅ Patched: $file"
  else
    echo "ℹ️ No patch needed: $file"
  fi
done

echo "✅ Build script finished successfully."
