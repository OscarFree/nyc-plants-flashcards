#!/usr/bin/env python3
"""
Parse the NYC Parks Planting Guide to extract native plant species information.
"""

import re
import json
from pathlib import Path

def parse_plants(filepath: str) -> list[dict]:
    """Parse plants from the text file, focusing on the Native Plant Descriptions section."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the Native Plant Descriptions section (starts at page 98 with Ferns)
    start_idx = content.find('Page | 98')
    if start_idx == -1:
        # Fallback to finding "Ferns" section header
        start_idx = content.find('Ferns\nFerns add texture')
        if start_idx == -1:
            start_idx = 0

    # Find Glossary (end of plant descriptions)
    end_idx = content.find('Glossary', start_idx)
    if end_idx == -1:
        end_idx = len(content)

    description_section = content[start_idx:end_idx]
    lines = description_section.split('\n')

    plants = []
    seen = set()

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Skip page markers and empty lines
        if not line or line.startswith('---') or line.startswith('Page |'):
            i += 1
            continue

        # Pattern: Genus species [var./ssp.] Common Name
        # Handle "Adiantum  pedatum  Northern maidenhair  fern" format
        match = re.match(
            r'^([A-Z][a-z]+)\s+([a-z]+(?:\s+(?:var\.|ssp\.)\s+[a-z]+)?)\s*†?\s+([A-Z].*)$',
            line
        )

        if match:
            genus = match.group(1).strip()
            species = match.group(2).strip().replace('†', '').strip()
            common = match.group(3).strip().replace('†', '').strip()

            scientific = f"{genus} {species}"

            # Clean up common name
            common = re.sub(r'\s+(Prohibited|Regulated|Invasive).*$', '', common, flags=re.IGNORECASE)
            common = ' '.join(common.split())  # Normalize whitespace

            # Skip if common name looks wrong
            if len(common) < 3:
                i += 1
                continue

            # Skip section headers
            skip_terms = ['ferns', 'forbs', 'graminoids', 'shrubs', 'trees', 'vines']
            if genus.lower() in skip_terms:
                i += 1
                continue

            # Validate binomial nomenclature
            if not (genus[0].isupper() and species[0].islower()):
                i += 1
                continue

            # Skip if looks like table/list header
            if common.lower() in ['common name', 'common names', 'valued characteristics']:
                i += 1
                continue

            key = scientific.lower()
            if key not in seen:
                seen.add(key)

                plant_info = {
                    'scientific_name': scientific,
                    'common_name': common,
                    'habitat': '',
                    'form_color': '',
                    'ecosystem_services': '',
                    'horticultural_value': '',
                    'other_info': '',
                    'exposure': '',
                    'soil_moisture': ''
                }

                # Look ahead for additional info
                j = i + 1
                while j < min(i + 60, len(lines)):
                    next_line = lines[j].strip()

                    if next_line.startswith('Habitat:'):
                        habitat_text = next_line.replace('Habitat:', '').strip()
                        habitat_text = re.sub(r'\s*Coefficient\s+of\s+\d+.*$', '', habitat_text)
                        plant_info['habitat'] = habitat_text

                    elif 'Exposure:' in next_line:
                        parts = next_line.split('Exposure:')
                        if len(parts) > 1:
                            exp = parts[1].split('Ecosystem')[0].strip()
                            plant_info['exposure'] = exp

                    elif 'Form/Color:' in next_line:
                        form_text = next_line.split('Form/Color:')[-1].strip()
                        k = j + 1
                        while k < min(j + 4, len(lines)):
                            cont = lines[k].strip()
                            if cont and not any(cont.startswith(x) for x in
                                ['Other:', '---', 'Habitat:', 'Page |']):
                                if re.match(r'^[A-Z][a-z]+\s+[a-z]+\s+[A-Z]', cont):
                                    break
                                form_text += ' ' + cont
                            else:
                                break
                            k += 1
                        plant_info['form_color'] = form_text

                    elif 'Ecosystem Services:' in next_line:
                        plant_info['ecosystem_services'] = next_line.split('Services:')[-1].strip()

                    elif 'Horticultural' in next_line and 'Value:' in next_line:
                        plant_info['horticultural_value'] = next_line.split('Value:')[-1].strip()

                    elif next_line.startswith('Other:'):
                        plant_info['other_info'] = next_line.replace('Other:', '').strip()

                    # Stop at next plant entry
                    if j > i + 3 and re.match(r'^[A-Z][a-z]+\s+[a-z]+\s+[A-Z]', next_line):
                        break

                    j += 1

                plants.append(plant_info)

        i += 1

    return plants


def categorize_plant(scientific_name: str) -> str:
    """Determine the category of a plant based on genus."""
    fern_genera = ['Adiantum', 'Asplenium', 'Athyrium', 'Dennstaedtia', 'Deparia',
                   'Dryopteris', 'Matteuccia', 'Onoclea', 'Osmunda', 'Osmundastrum',
                   'Polypodium', 'Polystichum', 'Pteridium', 'Thelypteris', 'Woodwardia']

    graminoid_genera = ['Ammophila', 'Andropogon', 'Aristida', 'Agrostis', 'Avenella',
                        'Bolboschoenus', 'Calamagrostis', 'Carex', 'Cenchrus', 'Chasmanthium',
                        'Cinna', 'Cyperus', 'Danthonia', 'Dichanthelium', 'Distichlis',
                        'Eleocharis', 'Elymus', 'Eragrostis', 'Eriophorum', 'Festuca',
                        'Glyceria', 'Juncus', 'Koeleria', 'Leersia', 'Muhlenbergia',
                        'Panicum', 'Phalaris', 'Piptochaetium', 'Poa', 'Rhynchospora',
                        'Schizachyrium', 'Schoenoplectus', 'Scirpus', 'Sorghastrum',
                        'Spartina', 'Sporobolus', 'Tridens', 'Tripsacum', 'Typha', 'Zizania']

    shrub_genera = ['Aronia', 'Arctostaphylos', 'Baccharis', 'Calycanthus', 'Ceanothus',
                    'Cephalanthus', 'Clethra', 'Comptonia', 'Cornus', 'Crataegus',
                    'Diervilla', 'Epigaea', 'Eubotrys', 'Euonymus', 'Gaultheria',
                    'Gaylussacia', 'Hamamelis', 'Hudsonia', 'Hydrangea', 'Ilex',
                    'Itea', 'Kalmia', 'Leucothoe', 'Lindera', 'Lyonia', 'Morella',
                    'Myrica', 'Photinia', 'Physocarpus', 'Prunus', 'Rhododendron',
                    'Rhus', 'Ribes', 'Rosa', 'Rubus', 'Sambucus', 'Spiraea',
                    'Staphylea', 'Symphoricarpos', 'Vaccinium', 'Viburnum', 'Xanthorhiza']

    tree_genera = ['Abies', 'Acer', 'Aesculus', 'Amelanchier', 'Asimina', 'Betula', 'Carpinus',
                   'Carya', 'Castanea', 'Catalpa', 'Celtis', 'Cercis', 'Chionanthus',
                   'Cladrastis', 'Diospyros', 'Fagus', 'Fraxinus', 'Gleditsia',
                   'Gymnocladus', 'Halesia', 'Juglans', 'Juniperus', 'Larix',
                   'Liquidambar', 'Liriodendron', 'Magnolia', 'Morus', 'Nyssa',
                   'Ostrya', 'Oxydendrum', 'Picea', 'Pinus', 'Platanus', 'Populus', 'Quercus',
                   'Salix', 'Sassafras', 'Taxodium', 'Thuja', 'Tilia', 'Tsuga', 'Ulmus']

    vine_genera = ['Apios', 'Bignonia', 'Campsis', 'Celastrus', 'Clematis', 'Lonicera',
                   'Menispermum', 'Parthenocissus', 'Smilax', 'Strophostyles', 'Vitis',
                   'Wisteria']

    genus = scientific_name.split()[0]

    if genus in fern_genera:
        return 'Fern'
    elif genus in graminoid_genera:
        return 'Graminoid'
    elif genus in shrub_genera:
        return 'Shrub'
    elif genus in tree_genera:
        return 'Tree'
    elif genus in vine_genera:
        return 'Vine'
    else:
        return 'Forb'


def clean_name(name: str) -> str:
    """Clean up plant name by removing extra spaces and artifacts."""
    name = ' '.join(name.split())
    name = name.strip(' .,;:')
    return name


def main():
    pdf_path = "/Users/oscar/Downloads/2024_NYCPARKS_Planting_Guide.txt"
    output_path = "/Users/oscar/Downloads/nyc_plants_flashcards/plants.json"

    print("Parsing native plants from PDF...")
    plants = parse_plants(pdf_path)

    # Clean up and add categories
    for plant in plants:
        plant['scientific_name'] = clean_name(plant['scientific_name'])
        plant['common_name'] = clean_name(plant['common_name'])
        plant['category'] = categorize_plant(plant['scientific_name'])

    # Remove duplicates
    unique_plants = {}
    for plant in plants:
        key = plant['scientific_name'].lower()
        if key not in unique_plants:
            unique_plants[key] = plant
        else:
            existing = unique_plants[key]
            if len(plant.get('habitat', '') or '') > len(existing.get('habitat', '') or ''):
                unique_plants[key] = plant

    plants = list(unique_plants.values())
    plants.sort(key=lambda x: x['scientific_name'])

    print(f"Found {len(plants)} unique native plants")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(plants, f, indent=2, ensure_ascii=False)

    print(f"Saved to {output_path}")

    categories = {}
    for plant in plants:
        cat = plant.get('category', 'Unknown')
        categories[cat] = categories.get(cat, 0) + 1

    print("\nPlants by category:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")

    print("\nSample plants:")
    for plant in plants[:15]:
        print(f"  - {plant['scientific_name']}: {plant['common_name']}")


if __name__ == "__main__":
    main()
