#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Define paths
ZIP_FILE="deployed_assets.zip"
DEPLOY_DIR="deployed_assets"
FILES_TO_COPY=("agent.py" "index.py" "tools.py")

echo "=== Starting Lambda deployment packaging ==="

# Step 1: Delete the existing zip file
if [ -f "$ZIP_FILE" ]; then
    echo "Deleting existing $ZIP_FILE..."
    rm "$ZIP_FILE"
fi

# Step 2: Delete old source files from deployed_assets directory
echo "Cleaning old source files from $DEPLOY_DIR..."
for file in "${FILES_TO_COPY[@]}"; do
    if [ -f "$DEPLOY_DIR/$file" ]; then
        rm "$DEPLOY_DIR/$file"
    fi
done

# Step 3: Copy current versions into deployed_assets
echo "Copying latest source files into $DEPLOY_DIR..."
for file in "${FILES_TO_COPY[@]}"; do
    cp "$file" "$DEPLOY_DIR/"
done

# Step 4: Create a new zip of the deployed_assets directory
echo "Creating new zip archive $ZIP_FILE..."
cd "$DEPLOY_DIR"
zip -r "../$ZIP_FILE" ./*
cd ..

echo "=== Deployment package $ZIP_FILE created successfully ==="
