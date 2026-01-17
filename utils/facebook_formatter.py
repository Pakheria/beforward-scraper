"""
BE FORWARD Web Scraper - Facebook Post Formatter
Generates Facebook-ready post content from vehicle data.
"""

import re
from typing import Dict, List
import config


def sanitize_filename(name: str) -> str:
    """
    Sanitize a string to be used as a folder/filename.

    Args:
        name: The string to sanitize

    Returns:
        A safe filename string
    """
    # Replace spaces and special characters with underscores
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'[-\s]+', '_', name)
    # Remove leading/trailing underscores
    name = name.strip('_')
    return name


def create_vehicle_folder_name(title: str, ref_no: str) -> str:
    """
    Create a standardized folder name for a vehicle.

    Args:
        title: Vehicle title (e.g., "2019 TOYOTA LAND CRUISER 4.5L Diesel V8 Manual")
        ref_no: Vehicle reference number (e.g., "CB761369")

    Returns:
        A safe folder name (e.g., "2019_TOYOTA_LAND_CRUISER_CB761369")
    """
    # Extract key info from title (year, make, model)
    parts = title.split()

    # Year (first 4 characters if numeric)
    year = ""
    if parts and parts[0].isdigit() and len(parts[0]) == 4:
        year = parts[0]

    # Make and model (usually next 2-3 words)
    make = ""
    model = ""
    if len(parts) >= 2:
        make = parts[1].upper() if parts[1] else ""
    if len(parts) >= 3:
        model = parts[2].upper() if parts[2] else ""

    # Create folder name: YEAR_MAKE_MODEL_REFNO
    folder_parts = [year, make, model, ref_no]
    folder_name = "_".join([p for p in folder_parts if p])

    return sanitize_filename(folder_name)


def generate_hashtags(specs: Dict) -> List[str]:
    """
    Generate relevant hashtags from vehicle specifications.

    Args:
        specs: Vehicle specification dictionary

    Returns:
        List of hashtag strings (without # symbol)
    """
    hashtags = set(config.FACEBOOK_POST_TEMPLATE["default_hashtags"])

    # Add make hashtag
    make = specs.get("make", "")
    if make:
        hashtags.add(f"#{make}")

    # Add model hashtag
    model = specs.get("model", "")
    if model:
        hashtags.add(f"#{model}")

    # Add type-specific hashtags
    drive = specs.get("drive", "").lower()
    if "4" in drive or "awd" in drive or "4wd" in drive:
        hashtags.add("#4x4")
        hashtags.add("#4WD")

    # Fuel type
    fuel = specs.get("fuel", "").lower()
    if "diesel" in fuel:
        hashtags.add("#Diesel")
    if "hybrid" in fuel:
        hashtags.add("#Hybrid")
    if "petrol" in fuel or "gasoline" in fuel:
        hashtags.add("#Petrol")

    # Transmission
    trans = specs.get("transmission", "").lower()
    if "auto" in trans or "at" in trans:
        hashtags.add("#Automatic")
    if "manual" in trans or "mt" in trans:
        hashtags.add("#Manual")

    return sorted(list(hashtags))


def format_facebook_post(vehicle_data: Dict) -> Dict:
    """
    Generate a Facebook-ready post from vehicle data.

    Args:
        vehicle_data: Complete vehicle data dictionary

    Returns:
        Facebook post template dictionary
    """
    specs = vehicle_data.get("specs", {})

    # Extract key info
    ref_no = specs.get("ref_no", "")
    title = vehicle_data.get("title", f"{specs.get('location', '')} Stock")

    # Build headline
    headline = config.FACEBOOK_POST_TEMPLATE["headline"].format(title=title)

    # Build specs section
    emojis = config.FACEBOOK_POST_TEMPLATE["emojis"]
    specs_lines = []

    # Location
    location = specs.get("location", "")
    if location:
        specs_lines.append(f"{emojis['location']} Location: {location}, UAE")

    # Price (if available - you may need to add this to the scraper)
    price = vehicle_data.get("price", "")
    if price:
        specs_lines.append(f"{emojis['price']} Price: {price}")

    # Mileage
    mileage = specs.get("mileage", "")
    if mileage:
        specs_lines.append(f"{emojis['mileage']} Mileage: {mileage}")

    # Engine
    engine_size = specs.get("engine_size", "")
    fuel = specs.get("fuel", "")
    if engine_size and fuel:
        specs_lines.append(f"{emojis['engine']} Engine: {engine_size} {fuel}")
    elif engine_size:
        specs_lines.append(f"{emojis['engine']} Engine: {engine_size}")

    # Transmission
    transmission = specs.get("transmission", "")
    if transmission:
        specs_lines.append(f"{emojis['transmission']} Transmission: {transmission}")

    # Drive
    drive = specs.get("drive", "")
    if drive:
        specs_lines.append(f"{emojis['drive']} Drive: {drive}")

    # Additional specs
    additional_specs = []
    seats = specs.get("seats", "")
    if seats:
        additional_specs.append(f"• Seats: {seats}")

    doors = specs.get("doors", "")
    if doors:
        additional_specs.append(f"• Doors: {doors}")

    steering = specs.get("steering", "")
    if steering:
        additional_specs.append(f"• Steering: {steering}")

    color = specs.get("ext_color", "")
    if color:
        additional_specs.append(f"• Color: {color}")

    # Build post body
    intro = config.FACEBOOK_POST_TEMPLATE["intro"]
    specs_section = "\n".join(specs_lines)

    post_body = f"{headline}\n\n{intro}\n\n{specs_section}"

    if additional_specs:
        post_body += f"\n\nSpecs:\n" + "\n".join(additional_specs)

    # Add call-to-action with link
    detail_url = vehicle_data.get("detail_url", "")
    cta = config.FACEBOOK_POST_TEMPLATE["cta"]
    if detail_url:
        post_body += f"\n\n{cta.format(link=detail_url)}"

    # Generate hashtags
    hashtags = generate_hashtags(specs)
    hashtag_section = " ".join(hashtags)
    post_body += f"\n\n{hashtag_section}"

    # Get image paths
    image_folder = vehicle_data.get("image_folder", "")
    image_files = vehicle_data.get("image_files", [])

    # If image_files not provided, use image_folder
    if not image_files and image_folder:
        import os
        if os.path.exists(image_folder):
            images_dir = f"{image_folder}/images"
            if os.path.exists(images_dir):
                image_files = [
                    f"{images_dir}/{f}"
                    for f in sorted(os.listdir(images_dir))
                    if f.lower().endswith(('.jpg', '.jpeg', '.png'))
                ]

    # Build result
    result = {
        "title": title,
        "ref_no": ref_no,
        "price": price,
        "location": location,
        "post_content": {
            "headline": headline,
            "body": post_body.strip(),
            "hashtags": hashtags,
        },
        "images": image_files[:10],  # Facebook allows up to 10 photos
        "vehicle_url": detail_url,
        "folder_name": vehicle_data.get("folder_name", ""),
    }

    return result


def save_facebook_json(facebook_data: Dict, output_path):
    """
    Save Facebook post data to a JSON file.

    Args:
        facebook_data: Facebook post dictionary
        output_path: Path to save the JSON file
    """
    import json

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(facebook_data, f, indent=2, ensure_ascii=False)
