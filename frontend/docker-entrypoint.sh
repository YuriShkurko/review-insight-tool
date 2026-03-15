#!/bin/sh
set -e
# With compose mount ./frontend:/app, node_modules comes from a volume that may be empty.
# Install deps when missing so first start (and after volume wipe) works.
if [ ! -d node_modules ] || [ ! -f node_modules/.package-lock.json ]; then
  echo "Installing dependencies..."
  npm install
fi
exec npm run dev
