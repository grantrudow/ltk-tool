#!/bin/bash
# This script runs before your application starts on Render

# Create download directories
mkdir -p /app/download_storage
chmod 777 /app/download_storage

# Test Chrome installation
echo "Testing Chrome installation..."
google-chrome --version

# Test ChromeDriver installation
echo "Testing ChromeDriver installation..."
chromedriver --version

# Test FFmpeg installation
echo "Testing FFmpeg installation..."
ffmpeg -version

# Print environment info
echo "Python version:"
python --version

echo "Setup complete!"