#!/usr/bin/env python3
"""
Download plant images from Wikipedia.
Uses the Wikipedia pageimages API which is more efficient and respectful.
"""

import json
import os
import re
import time
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional, Dict

# Configuration
DELAY_BETWEEN_REQUESTS = 2.0  # Seconds between API calls
MAX_RETRIES = 3
USER_AGENT = 'NYCPlantsFlashcards/1.0 (Educational project; contact: educational@example.com)'


def sanitize_filename(name: str) -> str:
    """Create a safe filename from plant name."""
    safe = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
    safe = re.sub(r'_+', '_', safe)
    return safe.strip('_')


def get_wikipedia_image(scientific_name: str) -> Optional[Dict]:
    """
    Get the main image from a Wikipedia article about the plant.
    Uses the pageimages API which is designed for this purpose.
    """
    # Search for the article
    search_url = (
        "https://en.wikipedia.org/w/api.php?"
        f"action=query&list=search&srsearch={urllib.parse.quote(scientific_name)}"
        "&srnamespace=0&srlimit=1&format=json"
    )

    try:
        req = urllib.request.Request(search_url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))

        if not data.get('query', {}).get('search'):
            return None

        # Get the page title
        page_title = data['query']['search'][0]['title']

        # Get the page image
        image_url = (
            "https://en.wikipedia.org/w/api.php?"
            f"action=query&titles={urllib.parse.quote(page_title)}"
            "&prop=pageimages|pageterms&piprop=original&format=json"
        )

        req = urllib.request.Request(image_url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as response:
            image_data = json.loads(response.read().decode('utf-8'))

        pages = image_data.get('query', {}).get('pages', {})
        for page_id, page_info in pages.items():
            if 'original' in page_info:
                return {
                    'url': page_info['original']['source'],
                    'title': page_title,
                    'license': 'Wikimedia',
                    'author': 'Wikipedia contributors'
                }

    except urllib.error.HTTPError as e:
        if e.code == 429:
            print(f"  Rate limited - waiting 60 seconds...")
            time.sleep(60)
            return get_wikipedia_image(scientific_name)  # Retry once
        print(f"  HTTP Error {e.code}")
    except Exception as e:
        print(f"  Error: {e}")

    return None


def download_image(url: str, filepath: str) -> bool:
    """Download an image from URL to filepath."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read()
            # Check if it's actually an image
            if len(content) < 1000:
                return False
            with open(filepath, 'wb') as f:
                f.write(content)
        return True
    except Exception as e:
        print(f"  Download error: {e}")
        return False


def main():
    plants_file = "/Users/oscar/Downloads/nyc_plants_flashcards/plants.json"
    images_dir = Path("/Users/oscar/Downloads/nyc_plants_flashcards/images")
    images_dir.mkdir(exist_ok=True)

    with open(plants_file, 'r') as f:
        plants = json.load(f)

    print(f"Processing {len(plants)} plants...")
    print(f"Delay between requests: {DELAY_BETWEEN_REQUESTS}s")

    # Track existing images
    existing_images = set()
    for f in images_dir.iterdir():
        if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
            existing_images.add(f.stem)

    success_count = len(existing_images)
    failed_plants = []
    skipped = 0

    for i, plant in enumerate(plants):
        scientific_name = plant['scientific_name']
        common_name = plant['common_name']
        filename = sanitize_filename(scientific_name)

        # Skip if already have this image
        if filename in existing_images:
            print(f"[{i+1}/{len(plants)}] Already have: {scientific_name}")
            # Find the existing file
            for ext in ['.jpg', '.jpeg', '.png', '.gif']:
                existing_path = images_dir / f"{filename}{ext}"
                if existing_path.exists():
                    plant['image_file'] = existing_path.name
                    break
            skipped += 1
            continue

        # Skip plants that already failed (marked as no image)
        if plant.get('image_file') is None and 'image_file' in plant:
            skipped += 1
            continue

        print(f"[{i+1}/{len(plants)}] Searching: {scientific_name} ({common_name})")

        # Search for image
        image_info = get_wikipedia_image(scientific_name)

        if not image_info:
            # Try common name
            image_info = get_wikipedia_image(common_name)

        if image_info:
            url = image_info['url']
            ext = os.path.splitext(url)[1].lower().split('?')[0]
            if ext not in ['.jpg', '.jpeg', '.png', '.gif']:
                ext = '.jpg'

            filepath = images_dir / f"{filename}{ext}"

            if download_image(url, str(filepath)):
                print(f"  Downloaded: {filepath.name}")
                plant['image_file'] = filepath.name
                plant['image_license'] = image_info['license']
                plant['image_author'] = image_info['author']
                success_count += 1
                existing_images.add(filename)
            else:
                print(f"  Failed to download")
                failed_plants.append(scientific_name)
                plant['image_file'] = None
        else:
            print(f"  No image found")
            failed_plants.append(scientific_name)
            plant['image_file'] = None

        # Rate limiting
        time.sleep(DELAY_BETWEEN_REQUESTS)

        # Save progress every 20 plants
        if (i + 1) % 20 == 0:
            with open(plants_file, 'w') as f:
                json.dump(plants, f, indent=2, ensure_ascii=False)
            print(f"  [Progress saved - {success_count} images]")

    # Final save
    with open(plants_file, 'w') as f:
        json.dump(plants, f, indent=2, ensure_ascii=False)

    print(f"\n=== SUMMARY ===")
    print(f"Total plants: {len(plants)}")
    print(f"Images downloaded: {success_count}")
    print(f"Skipped (existing): {skipped}")
    print(f"Failed: {len(failed_plants)}")

    if failed_plants[:10]:
        print(f"\nSample of plants without images:")
        for name in failed_plants[:10]:
            print(f"  - {name}")


if __name__ == "__main__":
    main()
