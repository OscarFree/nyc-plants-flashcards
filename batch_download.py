#!/usr/bin/env python3
"""
Batch download plant images from Wikipedia with better rate limiting.
"""

import json
import os
import re
import time
import urllib.request
import urllib.parse
from pathlib import Path

USER_AGENT = 'NYCPlantsFlashcards/1.0 (Educational project for NY State scientists)'

def sanitize_filename(name: str) -> str:
    safe = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
    safe = re.sub(r'_+', '_', safe)
    return safe.strip('_')


def get_wikipedia_image(search_term: str):
    """Get image URL from Wikipedia."""
    try:
        # Search for article
        search_url = (
            "https://en.wikipedia.org/w/api.php?"
            f"action=query&list=search&srsearch={urllib.parse.quote(search_term)}"
            "&srnamespace=0&srlimit=1&format=json"
        )
        req = urllib.request.Request(search_url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())

        if not data.get('query', {}).get('search'):
            return None

        title = data['query']['search'][0]['title']

        # Get page image
        img_url = (
            "https://en.wikipedia.org/w/api.php?"
            f"action=query&titles={urllib.parse.quote(title)}"
            "&prop=pageimages&piprop=original&format=json"
        )
        req = urllib.request.Request(img_url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as resp:
            img_data = json.loads(resp.read())

        for page in img_data.get('query', {}).get('pages', {}).values():
            if 'original' in page:
                return page['original']['source']

    except Exception as e:
        print(f"    Error: {e}")
    return None


def download_image(url: str, filepath: str) -> bool:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            if len(data) > 1000:  # Valid image
                with open(filepath, 'wb') as f:
                    f.write(data)
                return True
    except Exception as e:
        print(f"    Download failed: {e}")
    return False


def main():
    plants_file = Path("/Users/oscar/Downloads/nyc_plants_flashcards/plants.json")
    images_dir = Path("/Users/oscar/Downloads/nyc_plants_flashcards/images")

    with open(plants_file) as f:
        plants = json.load(f)

    # Find plants without images
    need_images = []
    for p in plants:
        filename = sanitize_filename(p['scientific_name'])
        has_image = any((images_dir / f"{filename}{ext}").exists()
                       for ext in ['.jpg', '.jpeg', '.png', '.gif'])
        if not has_image:
            need_images.append(p)

    print(f"Plants needing images: {len(need_images)}")
    print(f"Starting download (3s delay between requests)...")

    downloaded = 0
    max_downloads = 50  # Limit per run to be nice to Wikipedia

    for i, plant in enumerate(need_images[:max_downloads]):
        sci_name = plant['scientific_name']
        common_name = plant['common_name']
        filename = sanitize_filename(sci_name)

        print(f"[{i+1}/{min(len(need_images), max_downloads)}] {sci_name}")

        # Try scientific name first
        url = get_wikipedia_image(sci_name)
        if not url:
            # Try common name
            url = get_wikipedia_image(common_name)

        if url:
            ext = os.path.splitext(url)[1].lower().split('?')[0]
            if ext not in ['.jpg', '.jpeg', '.png', '.gif']:
                ext = '.jpg'

            filepath = images_dir / f"{filename}{ext}"
            if download_image(url, str(filepath)):
                print(f"    Downloaded: {filepath.name}")
                downloaded += 1
            else:
                print(f"    Failed to save")
        else:
            print(f"    No image found")

        time.sleep(3)  # Be nice to Wikipedia

    print(f"\nDownloaded {downloaded} new images")

    # Update plants.json
    for plant in plants:
        filename = sanitize_filename(plant['scientific_name'])
        for ext in ['.jpg', '.jpeg', '.png', '.gif']:
            img_path = images_dir / f"{filename}{ext}"
            if img_path.exists():
                plant['image_file'] = img_path.name
                plant['image_license'] = 'Wikimedia Commons'
                plant['image_author'] = 'Wikipedia contributors'
                break

    with open(plants_file, 'w') as f:
        json.dump(plants, f, indent=2, ensure_ascii=False)

    print("Updated plants.json")


if __name__ == "__main__":
    main()
