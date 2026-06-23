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

if [ ! -f "plain/${INTEGRATION}.plain" ] && [ ! -d "src/integrations/${INTEGRATION}" ]; then
    echo "Error: Integration '${INTEGRATION}' does not exist (no .plain file or src directory found)."
    exit 1
fi

echo "Removing crm.db..."
rm -f crm.db

echo "Removing specs and resources for '${INTEGRATION}'..."
rm -f "plain/${INTEGRATION}.plain"
rm -rf "plain/resources/${INTEGRATION}"

echo "Cleaning up generated integration directories for '${INTEGRATION}'..."
rm -rf "src/integrations/${INTEGRATION}"
rm -rf "tests/integrations/${INTEGRATION}"

echo "Cleanup complete for '${INTEGRATION}'!"
