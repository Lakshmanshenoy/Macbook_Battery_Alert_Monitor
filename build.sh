#!/bin/bash

# Build script for macOS app

# Specify the project directory
PROJECT_DIR="./MacApp"

# Change to the project directory
cd "$PROJECT_DIR" || exit

# Install dependencies
pod install

# Build the app
xcodebuild -scheme "YourAppScheme" -configuration Release
