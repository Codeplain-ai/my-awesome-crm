#!/bin/bash
# Clean up script for a specific integration

if [ -z "$1" ]; then
    echo "Usage: ./scripts/cleanup.sh <integration>"
    echo "Example: ./scripts/cleanup.sh hubspot"
    exit 1
fi

INTEGRATION=$1

# Move to the project root directory so this script can be run from anywhere
cd "$(dirname "$0")/.." || exit 1

MATCHES=$(find . -name "*${INTEGRATION}*" ! -path "*/.git/*")
if [ -z "$MATCHES" ]; then
    echo "Error: No files or folders found containing '${INTEGRATION}'."
    exit 1
fi

echo "Removing crm.db..."
rm -f crm.db

echo "Deleting files and folders containing '${INTEGRATION}'..."
find . -depth -name "*${INTEGRATION}*" ! -path "*/.git/*" -exec rm -rf {} \;

echo "Removing any directories left empty..."
find . -depth -type d -empty ! -path "*/.git/*" -delete

echo "Cleanup complete for '${INTEGRATION}'!"
