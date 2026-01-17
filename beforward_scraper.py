#!/usr/bin/env python3
"""
BE FORWARD Web Scraper - Main Script
Scrapes vehicle data from https://www.beforward.jp/

Usage:
    python beforward_scraper.py --limit 50 --mode zip
    python beforward_scraper.py --limit 100 --mode individual
    python beforward_scraper.py --url "https://www.beforward.jp/..." --mode individual
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
import pandas as pd

import requests
import config
from utils import scraper, downloader, parser

# Set up logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_checkpoint() -> set:
    """Load previously processed vehicle Ref Nos from checkpoint file."""
    if config.CHECKPOINT_FILE.exists():
        try:
            with open(config.CHECKPOINT_FILE, "r") as f:
                data = json.load(f)
                return set(data.get("processed", []))
        except Exception as e:
            logger.warning(f"Could not load checkpoint: {e}")
    return set()


def save_checkpoint(processed_refs: set):
    """Save processed vehicle Ref Nos to checkpoint file."""
    try:
        with open(config.CHECKPOINT_FILE, "w") as f:
            json.dump({"processed": list(processed_refs), "updated": str(datetime.now())}, f)
    except Exception as e:
        logger.warning(f"Could not save checkpoint: {e}")


def scrape_single_vehicle(url: str, mode: str) -> dict | None:
    """
    Scrape a single vehicle from its detail page URL.

    Args:
        url: Vehicle detail page URL
        mode: Image download mode

    Returns:
        Vehicle data dictionary or None if failed
    """
    session = requests.Session()

    # Fetch vehicle detail page
    vehicle_data = scraper.scrape_vehicle_detail(url, session)

    if not vehicle_data:
        return None

    # Extract Ref No for folder naming
    ref_no = vehicle_data["specs"].get("ref_no", "UNKNOWN")

    # Download images
    if mode:
        image_result = downloader.download_vehicle_images(
            image_urls=vehicle_data["image_urls"],
            zip_url=vehicle_data["zip_url"],
            ref_no=ref_no,
            mode=mode,
        )

        # Add image info to vehicle data
        vehicle_data["image_folder"] = image_result["folder"]
        vehicle_data["image_count"] = image_result["count"]
        vehicle_data["image_mode"] = image_result["mode"]

    # Flatten specs to top level for easier export
    flat_data = {
        "detail_url": vehicle_data["detail_url"],
        **vehicle_data["specs"],
        "image_folder": vehicle_data.get("image_folder", ""),
        "image_count": vehicle_data.get("image_count", 0),
        "image_mode": vehicle_data.get("image_mode", ""),
    }

    return flat_data


def scrape_from_stock_list(limit: int, mode: str, skip_images: bool = False) -> list:
    """
    Scrape vehicles from the stock list page.

    Args:
        limit: Maximum number of vehicles to scrape
        mode: Image download mode
        skip_images: If True, skip image downloading

    Returns:
        List of vehicle data dictionaries
    """
    # Load checkpoint for resume capability
    processed_refs = load_checkpoint()

    # Get vehicle links from stock list
    logger.info("Fetching vehicle list from stock list...")
    vehicle_links = scraper.scrape_stock_list(max_vehicles=limit)

    if not vehicle_links:
        logger.error("No vehicles found in stock list")
        return []

    logger.info(f"Found {len(vehicle_links)} vehicles to process")

    # Scrape each vehicle
    all_data = []
    session = requests.Session()

    for vehicle in tqdm(vehicle_links, desc="Scraping vehicles"):
        ref_no = vehicle["ref_no"]

        # Skip if already processed
        if ref_no in processed_refs:
            logger.debug(f"Skipping already processed vehicle: {ref_no}")
            continue

        url = vehicle["detail_url"]
        logger.info(f"Processing: {ref_no} - {url}")

        try:
            # Fetch and parse vehicle detail page
            html = scraper.fetch_page(url, session)

            if not html:
                logger.error(f"Failed to fetch {url}")
                continue

            vehicle_data = parser.parse_vehicle_detail(html, url)

            # Download images if not skipped
            if not skip_images:
                image_mode = mode if ref_no not in processed_refs else None
                if image_mode:
                    image_result = downloader.download_vehicle_images(
                        image_urls=vehicle_data["image_urls"],
                        zip_url=vehicle_data["zip_url"],
                        ref_no=ref_no,
                        mode=image_mode,
                    )

                    vehicle_data["image_folder"] = image_result["folder"]
                    vehicle_data["image_count"] = image_result["count"]
                    vehicle_data["image_mode"] = image_result["mode"]
            else:
                vehicle_data["image_folder"] = ""
                vehicle_data["image_count"] = 0
                vehicle_data["image_mode"] = ""

            # Flatten specs to top level
            flat_data = {
                "detail_url": vehicle_data["detail_url"],
                **vehicle_data["specs"],
                "image_folder": vehicle_data.get("image_folder", ""),
                "image_count": vehicle_data.get("image_count", 0),
                "image_mode": vehicle_data.get("image_mode", ""),
            }

            all_data.append(flat_data)
            processed_refs.add(ref_no)

            # Save checkpoint periodically
            if len(all_data) % 10 == 0:
                save_checkpoint(processed_refs)

        except Exception as e:
            logger.error(f"Error processing {ref_no}: {e}")
            continue

    # Save final checkpoint
    save_checkpoint(processed_refs)

    return all_data


def export_data(data: list):
    """
    Export scraped data to JSON and CSV formats.

    Args:
        data: List of vehicle data dictionaries
    """
    if not data:
        logger.warning("No data to export")
        return

    logger.info(f"Exporting {len(data)} vehicles...")

    # Export to JSON
    try:
        with open(config.JSON_OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"JSON exported to: {config.JSON_OUTPUT_FILE}")
    except Exception as e:
        logger.error(f"Failed to export JSON: {e}")

    # Export to CSV
    try:
        df = pd.DataFrame(data)
        df.to_csv(config.CSV_OUTPUT_FILE, index=False, encoding="utf-8")
        logger.info(f"CSV exported to: {config.CSV_OUTPUT_FILE}")
    except Exception as e:
        logger.error(f"Failed to export CSV: {e}")


def main():
    """Main entry point for the scraper."""
    parser = argparse.ArgumentParser(
        description="BE FORWARD Web Scraper - Extract vehicle data and images",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape first 50 vehicles with zip image download
  python beforward_scraper.py --limit 50 --mode zip

  # Scrape first 100 vehicles with individual image download
  python beforward_scraper.py --limit 100 --mode individual

  # Scrape all vehicles (no limit)
  python beforward_scraper.py --mode zip

  # Scrape a single vehicle by URL
  python beforward_scraper.py --url "https://www.beforward.jp/toyota/land-cruiser/cb761369/id/13824758/" --mode individual

  # Scrape without downloading images
  python beforward_scraper.py --limit 50 --skip-images
        """,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=config.DEFAULT_VEHICLE_LIMIT,
        help=f"Maximum number of vehicles to scrape (default: {config.DEFAULT_VEHICLE_LIMIT or 'all'})",
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=[config.IMAGE_MODE_INDIVIDUAL, config.IMAGE_MODE_ZIP],
        default=config.DEFAULT_IMAGE_MODE,
        help=f"Image download mode: '{config.IMAGE_MODE_INDIVIDUAL}' (download each image) or "
             f"'{config.IMAGE_MODE_ZIP}' (download and extract zip archive). "
             f"Default: {config.DEFAULT_IMAGE_MODE}",
    )

    parser.add_argument(
        "--url",
        type=str,
        help="Scrape a single vehicle by its detail page URL",
    )

    parser.add_argument(
        "--skip-images",
        action="store_true",
        help="Skip image downloading (only extract data)",
    )

    parser.add_argument(
        "--output",
        type=str,
        help="Custom output directory path",
    )

    args = parser.parse_args()

    # Override output directory if specified
    if args.output:
        output_dir = Path(args.output)
        config.OUTPUT_DIR = output_dir
        config.DATA_DIR = output_dir / "data"
        config.VEHICLES_DIR = output_dir / "vehicles"
        config.JSON_OUTPUT_FILE = config.DATA_DIR / "vehicles.json"
        config.CSV_OUTPUT_FILE = config.DATA_DIR / "vehicles.csv"
        config.CHECKPOINT_FILE = config.DATA_DIR / ".checkpoint.json"

        # Create directories
        for dir_path in [config.OUTPUT_DIR, config.DATA_DIR, config.VEHICLES_DIR]:
            dir_path.mkdir(parents=True, exist_ok=True)

    # Print configuration
    print("=" * 60)
    print("BE FORWARD Web Scraper")
    print("=" * 60)
    print(f"Output directory: {config.OUTPUT_DIR}")
    print(f"Data directory: {config.DATA_DIR}")
    print(f"Images directory: {config.VEHICLES_DIR}")

    # Determine image mode
    image_mode = None if args.skip_images else args.mode

    # Scrape based on arguments
    data = []

    if args.url:
        # Single vehicle mode
        print(f"\nMode: Single vehicle")
        print(f"URL: {args.url}")
        print(f"Image mode: {image_mode or 'skipped'}")

        result = scrape_single_vehicle(args.url, image_mode)
        if result:
            data = [result]
    else:
        # Stock list mode
        print(f"\nMode: Stock list")
        print(f"Limit: {args.limit or 'all vehicles'}")
        print(f"Image mode: {image_mode or 'skipped'}")

        data = scrape_from_stock_list(
            limit=args.limit,
            mode=image_mode,
            skip_images=args.skip_images,
        )

    # Export data
    if data:
        export_data(data)

        # Print summary
        print("\n" + "=" * 60)
        print("Scraping Complete!")
        print("=" * 60)
        print(f"Vehicles processed: {len(data)}")

        total_images = sum(v.get("image_count", 0) for v in data)
        print(f"Total images downloaded: {total_images}")

        print(f"\nOutput files:")
        print(f"  JSON: {config.JSON_OUTPUT_FILE}")
        print(f"  CSV: {config.CSV_OUTPUT_FILE}")
    else:
        print("\nNo data collected. Check logs for errors.")
        sys.exit(1)


if __name__ == "__main__":
    main()
