#!/usr/bin/env python3
"""
Update plants.json with available images from the images folder.
"""

import json
import re
from pathlib import Path

def sanitize_filename(name: str) -> str:
    """Create a safe filename from plant name."""
    safe = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
    safe = re.sub(r'_+', '_', safe)
    return safe.strip('_')

def main():
    plants_file = Path("/Users/oscar/Downloads/nyc_plants_flashcards/plants.json")
    images_dir = Path("/Users/oscar/Downloads/nyc_plants_flashcards/images")

    with open(plants_file, 'r') as f:
        plants = json.load(f)

    # Get all available images
    available_images = {}
    for img_file in images_dir.iterdir():
        if img_file.is_file() and img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
            available_images[img_file.stem] = img_file.name

    print(f"Found {len(available_images)} images in folder")

    # Update plants with image info
    matched = 0
    for plant in plants:
        filename = sanitize_filename(plant['scientific_name'])
        if filename in available_images:
            plant['image_file'] = available_images[filename]
            plant['image_license'] = 'Wikimedia Commons'
            plant['image_author'] = 'Wikipedia contributors'
            matched += 1
        elif 'image_file' not in plant:
            plant['image_file'] = None

    print(f"Matched {matched} plants with images")

    # Save updated plants
    with open(plants_file, 'w') as f:
        json.dump(plants, f, indent=2, ensure_ascii=False)

    print(f"Updated {plants_file}")

    # Show sample
    print("\nPlants with images:")
    for plant in plants:
        if plant.get('image_file'):
            print(f"  - {plant['scientific_name']}: {plant['image_file']}")

if __name__ == "__main__":
    main()
