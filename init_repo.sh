#!/bin/bash

# Initialize repository structure
echo "Creating repository structure..."

# Create directories
mkdir -p .github/workflows
mkdir -p scripts
mkdir -p images/2026

# Create placeholder files
touch images/.gitkeep
touch requirements.txt

# Create README
cat > README.md << 'EOF'
# Weather Satellite Image Dumper

Automatically downloads and stores weather satellite images from ELECTRO-L satellite.

## Features
- Automatic hourly downloads via GitHub Actions
- Organized by year/month/day
- Tracks only new images
- Manual run capability

## Directory Structure
