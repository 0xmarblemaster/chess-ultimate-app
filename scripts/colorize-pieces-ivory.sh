#!/bin/bash

# Script to colorize Lichess Alpha pieces with ivory and ebony
# Warm ivory tones for white pieces, rich ebony for black pieces

SOURCE_DIR="../frontend/public/pieces/alpha"
OUTPUT_DIR="../frontend/public/pieces/alpha-ivory"

# Ivory color definitions (warm cream tones)
IVORY_FILL="#FFF8E7"         # Warm ivory/cream
IVORY_ACCENT="#F5E6D3"       # Darker cream
IVORY_OUTLINE="#D4C4A8"      # Warm tan outline

# Ebony color definitions (rich dark brown-black)
EBONY_FILL="#2B1810"         # Rich ebony/dark brown
EBONY_ACCENT="#3D2817"       # Lighter ebony
EBONY_OUTLINE="#4A3728"      # Brown outline

echo "🎨 Creating ivory & ebony chess pieces..."
echo "Source: $SOURCE_DIR"
echo "Output: $OUTPUT_DIR"
echo ""

mkdir -p "$OUTPUT_DIR"

# Process white pieces with warm ivory
for piece in wK wQ wR wB wN wP; do
  echo "Processing ${piece}.svg (ivory)..."
  sed -e "s/#f9f9f9/${IVORY_FILL}/g" \
      -e "s/#101010/${IVORY_OUTLINE}/g" \
      -e "s/<path fill=\"${IVORY_OUTLINE}\"/<path fill=\"${IVORY_OUTLINE}\" stroke=\"${IVORY_OUTLINE}\" stroke-width=\"6\"/g" \
      "$SOURCE_DIR/${piece}.svg" > "$OUTPUT_DIR/${piece}.svg"
done

# Process black pieces with rich ebony
for piece in bK bQ bR bB bN bP; do
  echo "Processing ${piece}.svg (ebony)..."
  sed -e "s/#f9f9f9/${EBONY_FILL}/g" \
      -e "s/#101010/${EBONY_OUTLINE}/g" \
      -e "s/<path fill=\"${EBONY_OUTLINE}\"/<path fill=\"${EBONY_OUTLINE}\" stroke=\"${EBONY_OUTLINE}\" stroke-width=\"6\"/g" \
      "$SOURCE_DIR/${piece}.svg" > "$OUTPUT_DIR/${piece}.svg"
done

echo ""
echo "✅ Done! Ivory & ebony pieces created in $OUTPUT_DIR"
echo ""
echo "Piece count:"
ls -1 "$OUTPUT_DIR" | wc -l
echo ""
echo "File sizes:"
du -sh "$OUTPUT_DIR"
