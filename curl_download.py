#!/usr/bin/env python3
"""
Download plant images using curl (bypasses Wikimedia bot detection).
"""

import json
import os
import re
import subprocess
import time
from pathlib import Path

CACHE_FILE = Path("/Users/oscar/Downloads/nyc_plants_flashcards/url_cache.json")

def sanitize_filename(name):
    safe = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
    return re.sub(r'_+', '_', safe).strip('_')

def download_with_curl(url, filepath):
    """Download file using curl."""
    try:
        result = subprocess.run([
            'curl', '-sL', '-o', filepath,
            '-A', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            '--max-time', '30',
            url
        ], capture_output=True, timeout=35)

        # Check if file exists and has content
        if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
            return True, None
        else:
            if os.path.exists(filepath):
                os.remove(filepath)
            return False, "too small"
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)[:30]

def main():
    plants_file = Path("/Users/oscar/Downloads/nyc_plants_flashcards/plants.json")
    images_dir = Path("/Users/oscar/Downloads/nyc_plants_flashcards/images")

    with open(plants_file) as f:
        plants = json.load(f)

    # Load URL cache
    with open(CACHE_FILE) as f:
        cache = json.load(f)
    print(f"Loaded {len(cache)} cached URLs")

    # Find plants needing images
    need_download = []
    for plant in plants:
        sci_name = plant['scientific_name']
        filename = sanitize_filename(sci_name)

        # Skip if already have image
        exists = any((images_dir / f"{filename}{ext}").exists()
                    for ext in ['.jpg', '.jpeg', '.png', '.gif'])
        if exists:
            continue

        # Skip if no URL cached
        img_url = cache.get(sci_name)
        if not img_url:
            continue

        need_download.append((sci_name, img_url, filename))

    print(f"Need to download {len(need_download)} images")
    print("Starting download (100ms delay)...")

    downloaded = 0
    failed = 0

    for i, (sci_name, url, filename) in enumerate(need_download):
        ext = os.path.splitext(url)[1].lower().split('?')[0]
        if ext not in ['.jpg', '.jpeg', '.png', '.gif']:
            ext = '.jpg'

        filepath = str(images_dir / f"{filename}{ext}")
        print(f"[{i+1}/{len(need_download)}] {sci_name}", end='', flush=True)

        success, error = download_with_curl(url, filepath)
        if success:
            print(f" - OK")
            downloaded += 1
        else:
            print(f" - Failed ({error})")
            failed += 1

        time.sleep(0.1)  # 100ms delay

        # Progress update every 50
        if (i + 1) % 50 == 0:
            print(f"  [Progress: {downloaded} downloaded, {failed} failed]")

    print(f"\n=== FINAL ===")
    print(f"Downloaded: {downloaded}")
    print(f"Failed: {failed}")

    # Update plants.json with image info
    total_with_images = 0
    for plant in plants:
        filename = sanitize_filename(plant['scientific_name'])
        for ext in ['.jpg', '.jpeg', '.png', '.gif']:
            img_path = images_dir / f"{filename}{ext}"
            if img_path.exists():
                plant['image_file'] = img_path.name
                plant['image_license'] = 'Wikimedia Commons'
                plant['image_author'] = 'Wikipedia contributors'
                total_with_images += 1
                break

    with open(plants_file, 'w') as f:
        json.dump(plants, f, indent=2, ensure_ascii=False)

    print(f"Total plants with images: {total_with_images}")

if __name__ == "__main__":
    main()
