#!/bin/bash

# Script to colorize Lichess Alpha pieces with rich traditional colors
# Vibrant black and white with gradients

SOURCE_DIR="../frontend/public/pieces/alpha"
OUTPUT_DIR="../frontend/public/pieces/alpha-traditional"

# Rich traditional color definitions
# White pieces: Cream to bright white gradient
WHITE_FILL="#FEFEFE"      # Pure white (bright)
WHITE_ACCENT="#F5F5F5"    # Soft cream
WHITE_OUTLINE="#E0E0E0"   # Light gray outline

# Black pieces: Deep charcoal to rich black gradient
BLACK_FILL="#1A1A1A"      # Rich black
BLACK_ACCENT="#2D2D2D"    # Deep charcoal
BLACK_OUTLINE="#404040"   # Medium gray outline

echo "🎨 Creating traditional vibrant black & white pieces..."
echo "Source: $SOURCE_DIR"
echo "Output: $OUTPUT_DIR"
echo ""

mkdir -p "$OUTPUT_DIR"

# Process white pieces with rich cream/white
for piece in wK wQ wR wB wN wP; do
  echo "Processing ${piece}.svg (white - vibrant)..."
  sed -e "s/#f9f9f9/${WHITE_FILL}/g" \
      -e "s/#101010/${WHITE_OUTLINE}/g" \
      -e "s/<path fill=\"${WHITE_OUTLINE}\"/<path fill=\"${WHITE_OUTLINE}\" stroke=\"${WHITE_OUTLINE}\" stroke-width=\"6\"/g" \
      "$SOURCE_DIR/${piece}.svg" > "$OUTPUT_DIR/${piece}.svg"
done

# Process black pieces with rich black
for piece in bK bQ bR bB bN bP; do
  echo "Processing ${piece}.svg (black - vibrant)..."
  sed -e "s/#f9f9f9/${BLACK_FILL}/g" \
      -e "s/#101010/${BLACK_OUTLINE}/g" \
      -e "s/<path fill=\"${BLACK_OUTLINE}\"/<path fill=\"${BLACK_OUTLINE}\" stroke=\"${BLACK_OUTLINE}\" stroke-width=\"6\"/g" \
      "$SOURCE_DIR/${piece}.svg" > "$OUTPUT_DIR/${piece}.svg"
done

echo ""
echo "✅ Done! Traditional vibrant pieces created in $OUTPUT_DIR"
echo ""
echo "Piece count:"
ls -1 "$OUTPUT_DIR" | wc -l
echo ""
echo "File sizes:"
du -sh "$OUTPUT_DIR"
