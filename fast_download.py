#!/usr/bin/env python3
"""
Fast plant image downloader with URL caching.
"""

import json
import os
import re
import time
import urllib.request
import urllib.parse
from pathlib import Path

USER_AGENT = 'NYCPlantsFlashcards/1.0 (Educational; plant-flashcards@example.com)'
CACHE_FILE = Path("/Users/oscar/Downloads/nyc_plants_flashcards/url_cache.json")

def sanitize_filename(name):
    safe = re.sub(r'[^a-zA-Z0-9]', '_', name.lower())
    return re.sub(r'_+', '_', safe).strip('_')

def load_cache():
    if CACHE_FILE.exists():
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)

def get_image(search_term):
    """Try to get image URL from Wikipedia."""
    try:
        # Search Wikipedia
        url = (f"https://en.wikipedia.org/w/api.php?action=query"
               f"&list=search&srsearch={urllib.parse.quote(search_term)}"
               f"&srnamespace=0&srlimit=1&format=json")
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())

        if not data.get('query', {}).get('search'):
            return None

        title = data['query']['search'][0]['title']

        # Get image
        img_url = (f"https://en.wikipedia.org/w/api.php?action=query"
                  f"&titles={urllib.parse.quote(title)}"
                  f"&prop=pageimages&piprop=original&format=json")
        req = urllib.request.Request(img_url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as resp:
            img_data = json.loads(resp.read())

        for page in img_data.get('query', {}).get('pages', {}).values():
            if 'original' in page:
                return page['original']['source']

    except Exception:
        pass
    return None

def download_file(url, filepath):
    try:
        headers = {
            'User-Agent': USER_AGENT,
            'Referer': 'https://en.wikipedia.org/',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8'
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            if len(data) > 1000:
                with open(filepath, 'wb') as f:
                    f.write(data)
                return True, None
            return False, "too small"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, str(e)[:30]

def main():
    plants_file = Path("/Users/oscar/Downloads/nyc_plants_flashcards/plants.json")
    images_dir = Path("/Users/oscar/Downloads/nyc_plants_flashcards/images")

    with open(plants_file) as f:
        plants = json.load(f)

    # Load URL cache
    cache = load_cache()
    print(f"Loaded {len(cache)} cached URLs")

    print(f"Processing {len(plants)} plants...")

    # Phase 1: Get all URLs (using cache)
    need_urls = []
    for plant in plants:
        sci_name = plant['scientific_name']
        filename = sanitize_filename(sci_name)

        # Skip if already have image
        exists = any((images_dir / f"{filename}{ext}").exists()
                    for ext in ['.jpg', '.jpeg', '.png', '.gif'])
        if exists:
            continue

        # Check cache
        if sci_name in cache:
            continue

        need_urls.append(plant)

    print(f"Need to fetch URLs for {len(need_urls)} plants...")

    for i, plant in enumerate(need_urls):
        sci_name = plant['scientific_name']
        common_name = plant['common_name']

        print(f"[{i+1}/{len(need_urls)}] Getting URL for: {sci_name}", end='', flush=True)

        img_url = get_image(sci_name)
        if not img_url:
            time.sleep(0.1)
            img_url = get_image(common_name)

        if img_url:
            cache[sci_name] = img_url
            print(f" - Found")
        else:
            cache[sci_name] = None  # Mark as no image
            print(f" - No image")

        time.sleep(0.1)

        # Save cache every 20 plants
        if (i + 1) % 20 == 0:
            save_cache(cache)
            print(f"  [Cache saved - {len([v for v in cache.values() if v])} URLs]")

    save_cache(cache)
    print(f"\nTotal cached URLs: {len([v for v in cache.values() if v])}")

    # Phase 2: Download images
    print("\n--- Downloading images ---")
    downloaded = 0
    failed = 0
    skipped = 0

    for plant in plants:
        sci_name = plant['scientific_name']
        filename = sanitize_filename(sci_name)

        # Skip if already have image
        exists = any((images_dir / f"{filename}{ext}").exists()
                    for ext in ['.jpg', '.jpeg', '.png', '.gif'])
        if exists:
            skipped += 1
            continue

        img_url = cache.get(sci_name)
        if not img_url:
            continue

        ext = os.path.splitext(img_url)[1].lower().split('?')[0]
        if ext not in ['.jpg', '.jpeg', '.png', '.gif']:
            ext = '.jpg'

        filepath = images_dir / f"{filename}{ext}"
        print(f"Downloading: {sci_name}", end='', flush=True)

        success, error = download_file(img_url, str(filepath))
        if success:
            print(f" - OK")
            downloaded += 1
        else:
            print(f" - Failed ({error})")
            failed += 1

        time.sleep(0.1)

    print(f"\n=== FINAL ===")
    print(f"Downloaded: {downloaded}")
    print(f"Failed: {failed}")
    print(f"Skipped (existing): {skipped}")

    # Update plants.json
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
