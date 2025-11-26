#!/bin/bash

# Script to create 3D-style chess pieces with depth and gradients
# Rich colors with highlights and shadows for dimensional effect

SOURCE_DIR="../frontend/public/pieces/alpha"
OUTPUT_DIR="../frontend/public/pieces/alpha-3d"

echo "🎨 Creating 3D chess pieces with depth and gradients..."
echo "Source: $SOURCE_DIR"
echo "Output: $OUTPUT_DIR"
echo ""

mkdir -p "$OUTPUT_DIR"

# For 3D effect, we'll need to manually edit pieces with gradients
# This script creates the base - we'll enhance with SVG gradients

# Process white pieces - will add gradient in SVG
for piece in wK wQ wR wB wN wP; do
  echo "Processing ${piece}.svg (white 3D)..."
  # Keep original for now, will add gradients via SVG defs
  cp "$SOURCE_DIR/${piece}.svg" "$OUTPUT_DIR/${piece}.svg"
done

# Process black pieces
for piece in bK bQ bR bB bN bP; do
  echo "Processing ${piece}.svg (black 3D)..."
  cp "$SOURCE_DIR/${piece}.svg" "$OUTPUT_DIR/${piece}.svg"
done

echo ""
echo "✅ Base pieces copied. Now adding 3D gradients..."
echo ""

# Now we'll use sed to add SVG gradient definitions
echo "Adding gradient definitions to pieces..."
