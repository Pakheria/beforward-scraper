#!/usr/bin/env python3
"""
BE FORWARD Daily Scraper - Automated Daily Vehicle Scraper
Scrapes one vehicle per day and organizes output for Facebook posting.

Usage:
    python3 daily_scraper.py              # Run daily scraper
    python3 daily_scraper.py --force      # Force run even if already ran today
    python3 daily_scraper.py --url <URL>  # Scrape specific vehicle
"""

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime, date
from pathlib import Path

import requests
from tqdm import tqdm

import config
from utils import scraper, downloader, facebook_formatter

# Set up logging
def setup_logging(log_file=None):
    """Configure logging to both file and console."""
    handlers = [logging.StreamHandler(sys.stdout)]

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )

    return logging.getLogger(__name__)


logger = setup_logging()


class StateManager:
    """Manages scraper state for daily automation."""

    def __init__(self, state_file: Path = None):
        self.state_file = state_file or config.STATE_FILE
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state = self._load_state()

    def _load_state(self) -> dict:
        """Load state from file or create new state."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load state file: {e}")

        # Default state
        return {
            "last_scraped_ref": None,
            "last_scraped_date": None,
            "scraped_vehicles": [],
            "current_index": 0,
            "total_available": 0,
            "created_at": str(datetime.now()),
        }

    def save_state(self):
        """Save current state to file."""
        try:
            with open(self.state_file, "w") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save state: {e}")

    @property
    def last_scraped_date(self) -> date | None:
        """Get the last scraped date as a date object."""
        if self.state.get("last_scraped_date"):
            try:
                return datetime.fromisoformat(self.state["last_scraped_date"]).date()
            except:
                pass
        return None

    @property
    def already_ran_today(self) -> bool:
        """Check if scraper already ran today."""
        return self.last_scraped_date == date.today()

    def update(self, ref_no: str, total_available: int = None):
        """Update state after scraping a vehicle."""
        # Normalize ref_no to uppercase for consistent comparison
        ref_no = ref_no.upper()

        self.state["last_scraped_ref"] = ref_no
        self.state["last_scraped_date"] = str(date.today())

        if ref_no not in self.state["scraped_vehicles"]:
            self.state["scraped_vehicles"].append(ref_no)

        self.state["current_index"] = len(self.state["scraped_vehicles"])

        if total_available is not None:
            self.state["total_available"] = total_available

        self.save_state()

    def reset_today(self):
        """Reset today's run (for --force flag)."""
        self.state["last_scraped_date"] = None
        self.save_state()


def get_next_vehicle(state: StateManager):
    """
    Get the next vehicle to scrape from the stock list.

    Smart logic:
    - Start from page 1
    - Check vehicles in order on each page
    - Skip already scraped vehicles
    - Return first unscraped vehicle (or None if all scraped)
    - Move to next page if all on current page are scraped

    Returns:
        Dictionary with ref_no, title, detail_url or None if no more vehicles
    """
    scraped_refs = set(v.upper() for v in state.state["scraped_vehicles"])
    session = requests.Session()
    page = 1

    logger.info("Looking for next unscraped vehicle...")
    logger.info(f"Already scraped: {len(scraped_refs)} vehicles")

    while True:
        # Get the stock list URL for the configured country
        stock_list_url = config.get_stock_list_url()

        # Construct URL for current page
        if page == 1:
            url = stock_list_url
        else:
            # Extract the country code from the stock list URL
            import re
            country_match = re.search(r'stock_country=(\d+)', stock_list_url)
            country_code = country_match.group(1) if country_match else "44"
            url = f"{config.BASE_URL}/stocklist/page={page}/stock_country={country_code}/sortkey=n"

        logger.info(f"Checking page {page}...")

        html = scraper.fetch_page(url, session)
        if not html:
            logger.error(f"Failed to fetch page {page}")
            # Try next page
            page += 1
            continue

        # Get vehicles from this page
        vehicles = scraper.get_vehicle_links(html, url)

        if not vehicles:
            logger.warning(f"No vehicles found on page {page}, moving to next page")
            page += 1
            continue

        logger.info(f"Found {len(vehicles)} vehicles on page {page}")

        # Check each vehicle on this page
        page_has_unscraped = False

        for vehicle in vehicles:
            ref_no = vehicle["ref_no"]

            if ref_no not in scraped_refs:
                # Found an unscraped vehicle!
                logger.info(f"Found unscraped vehicle: {ref_no}")

                # Update total count estimate
                state.state["total_available"] = state.state.get("total_available", 0) + page * 25
                state.save_state()

                return vehicle
            else:
                logger.debug(f"Skipping already scraped: {ref_no}")

        # All vehicles on this page are scraped, move to next page
        logger.info(f"All {len(vehicles)} vehicles on page {page} already scraped")
        page += 1

        # Safety limit to prevent infinite loop
        if page > 150:
            logger.error("Reached page limit (150), stopping")
            break

    logger.info("No more unscraped vehicles found!")
    return None


def scrape_vehicle(url: str, state: StateManager, mode: str = config.IMAGE_MODE_INDIVIDUAL) -> dict | None:
    """
    Scrape a single vehicle and organize its data.

    Args:
        url: Vehicle detail page URL
        state: StateManager instance
        mode: Image download mode

    Returns:
        Vehicle data dictionary or None if failed
    """
    session = requests.Session()

    logger.info(f"Fetching vehicle: {url}")
    html = scraper.fetch_page(url, session)

    if not html:
        logger.error(f"Failed to fetch: {url}")
        return None

    # Parse vehicle data
    logger.info("Parsing vehicle data...")
    vehicle_data = scraper.parser.parse_vehicle_detail(html, url)

    # Extract Ref No
    ref_no = vehicle_data["specs"].get("ref_no", "UNKNOWN")

    # Create folder name from title
    # Try to get title from the page
    from bs4 import BeautifulSoup

    # Filter XML parsing warning
    import warnings
    from bs4 import XMLParsedAsHTMLWarning
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


    soup = BeautifulSoup(html, "lxml")
    title_elem = soup.find("title")
    title = title_elem.get_text(strip=True) if title_elem else f"Vehicle {ref_no}"

    # Clean title (remove "BE FORWARD" suffix etc)
    title = title.split("-")[0].strip()
    folder_name = facebook_formatter.create_vehicle_folder_name(title, ref_no)

    # Create vehicle directory
    vehicle_dir = config.DAILY_VEHICLE_BASE_DIR / folder_name
    vehicle_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Created vehicle directory: {vehicle_dir}")

    # Download images
    logger.info("Downloading images...")
    image_result = downloader.download_vehicle_images(
        image_urls=vehicle_data["image_urls"],
        zip_url=vehicle_data["zip_url"],
        ref_no=folder_name,  # Use folder name as ref for organization
        mode=mode,
        output_dir=config.DAILY_VEHICLE_BASE_DIR,
    )

    # Organize images into subfolder
    images_dir = vehicle_dir / "images"
    if image_result["files"]:
        import shutil
        images_dir.mkdir(exist_ok=True)
        for img_file in image_result["files"]:
            if os.path.exists(img_file):
                shutil.move(img_file, images_dir / os.path.basename(img_file))

    # Prepare vehicle data for output
    # Add title and folder name
    vehicle_data["title"] = title
    vehicle_data["folder_name"] = folder_name

    # Try to extract price from the page
    price_elem = soup.find("span", class_=re.compile(r"price|Price", re.I))
    if price_elem:
        price_text = price_elem.get_text(strip=True)
        if price_text:
            vehicle_data["price"] = price_text
    else:
        vehicle_data["price"] = ""

    # Add image info
    vehicle_data["image_folder"] = str(images_dir)
    vehicle_data["image_files"] = image_result["files"]
    vehicle_data["image_count"] = len(image_result["files"])

    # Save data.json
    data_file = vehicle_dir / "data.json"
    with open(data_file, "w", encoding="utf-8") as f:
        # Flatten specs for JSON output
        flat_data = {
            "title": title,
            "ref_no": ref_no,
            "detail_url": url,
            "folder_name": folder_name,
            "scraped_at": str(datetime.now()),
            "specs": vehicle_data["specs"],
            "price": vehicle_data.get("price", ""),
            "image_count": vehicle_data["image_count"],
            "image_folder": str(images_dir),
        }
        json.dump(flat_data, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved data.json: {data_file}")

    # Generate Facebook post
    logger.info("Generating Facebook post...")
    fb_data = facebook_formatter.format_facebook_post(vehicle_data)

    # Update fb_data with correct image paths
    fb_data["images"] = []
    if os.path.exists(images_dir):
        for img_file in sorted(os.listdir(images_dir)):
            if img_file.lower().endswith(('.jpg', '.jpeg', '.png')):
                fb_data["images"].append(str(images_dir / img_file))

    # Save facebook.json
    fb_file = vehicle_dir / "facebook.json"
    facebook_formatter.save_facebook_json(fb_data, fb_file)
    logger.info(f"Saved facebook.json: {fb_file}")

    # Save metadata.txt
    metadata_file = vehicle_dir / "metadata.txt"
    with open(metadata_file, "w", encoding="utf-8") as f:
        f.write(f"Scraped at: {datetime.now()}\n")
        f.write(f"Ref No: {ref_no}\n")
        f.write(f"Title: {title}\n")
        f.write(f"URL: {url}\n")
        f.write(f"Image count: {vehicle_data['image_count']}\n")
        f.write(f"Folder: {folder_name}\n")
    logger.info(f"Saved metadata.txt: {metadata_file}")

    # Update state
    total_available = state.state.get("total_available", 0)
    state.update(ref_no, total_available)

    return vehicle_data


def main():
    """Main entry point for the daily scraper."""
    parser = argparse.ArgumentParser(
        description="BE FORWARD Daily Scraper - Automated daily vehicle scraping",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run daily scraper (skips if already ran today)
  python3 daily_scraper.py

  # Force run even if already ran today
  python3 daily_scraper.py --force

  # Scrape from a different country
  python3 daily_scraper.py --country japan
  python3 daily_scraper.py --country uk
  python3 daily_scraper.py --country korea

  # Scrape a specific vehicle by URL
  python3 daily_scraper.py --url "https://www.beforward.jp/toyota/land-cruiser/cb761369/id/13824758/"

  # Skip image downloading
  python3 daily_scraper.py --skip-images

  # Use zip download mode
  python3 daily_scraper.py --mode zip

Available countries:
  uae, japan, korea, thailand, uk, singapore, australia, philippines,
  belgium, south_africa, new_zealand, tanzania, zambia, kenya, uganda,
  mozambique, zimbabwe, botswana, namibia, lesotho, malawi, rwanda,
  burundi, ghana, senegal, gabon, nigeria, angola, egypt, saudi_arabia,
  georgia, germany, usa, canada, ukraine, armenia, azerbaijan, russia,
  kyrgyzstan, bangladesh, pakistan, mongolia, sri_lanka, mexico, taiwan
        """,
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Force run even if already ran today",
    )

    parser.add_argument(
        "--url",
        type=str,
        help="Scrape a specific vehicle by URL",
    )

    parser.add_argument(
        "--mode",
        type=str,
        choices=[config.IMAGE_MODE_INDIVIDUAL, config.IMAGE_MODE_ZIP],
        default=config.IMAGE_MODE_INDIVIDUAL,
        help=f"Image download mode (default: {config.IMAGE_MODE_INDIVIDUAL})",
    )

    parser.add_argument(
        "--skip-images",
        action="store_true",
        help="Skip image downloading",
    )


    parser.add_argument(
        "--no-crop",
        action="store_true",
        help="Disable automatic image cropping (removes BE FORWARD watermark)",
    )

    parser.add_argument(
        "--log-file",
        type=str,
        default=str(config.SERVICE_LOG_FILE),
        help=f"Log file path (default: {config.SERVICE_LOG_FILE})",
    )

    parser.add_argument(
        "--country",
        type=str,
        default=None,
        help=f"Country to scrape (e.g., uae, japan, korea, uk, usa). Default: {config.DEFAULT_COUNTRY}",
    )

    args = parser.parse_args()

    # Set country if specified
    if args.country:
        config.CURRENT_COUNTRY = args.country.lower()
        config.CURRENT_COUNTRY_CODE = config.COUNTRY_CODES.get(
            config.CURRENT_COUNTRY,
            config.DEFAULT_COUNTRY_CODE
        )
        print(f"Country set to: {args.country.upper()} (code: {config.CURRENT_COUNTRY_CODE})")



    # Set cropping config
    if args.no_crop:
        config.ENABLE_CROPPING = False
        print("Image cropping: DISABLED")
    else:
        print(f"Image cropping: ENABLED (crop {config.CROP_PERCENTAGE}% from bottom)")

    # Re-setup logging with log file if specified
    global logger
    logger = setup_logging(Path(args.log_file) if args.log_file else None)

    print("=" * 60)
    print("BE FORWARD Daily Scraper")
    print("=" * 60)
    print(f"Date: {date.today()}")
    print(f"Country: {config.CURRENT_COUNTRY.upper()} (code: {config.CURRENT_COUNTRY_CODE})")
    print(f"Stock URL: {config.get_stock_list_url()}")
    print(f"Output directory: {config.DAILY_VEHICLE_BASE_DIR}")
    print(f"State file: {config.STATE_FILE}")
    print(f"Image mode: {args.mode if not args.skip_images else 'skipped'}")
    print()

    # Initialize state manager
    state = StateManager()

    # Check if already ran today
    if state.already_ran_today and not args.force and not args.url:
        print(f"Already ran today! Last scraped: {state.last_scraped_date}")
        print(f"Last vehicle: {state.state['last_scraped_ref']}")
        print(f"Use --force to run again.")
        print()
        print(f"Total scraped: {len(state.state['scraped_vehicles'])} / {state.state.get('total_available', '?')}")
        return 0

    # Determine what to scrape
    vehicle_to_scrape = None

    if args.url:
        # Scrape specific URL
        print(f"Mode: Single vehicle from URL")
        vehicle_to_scrape = {
            "ref_no": "CUSTOM",
            "title": "Custom Vehicle",
            "detail_url": args.url,
        }
    else:
        # Get next vehicle from stock list
        print(f"Mode: Daily automation")
        print(f"Previously scraped: {len(state.state['scraped_vehicles'])} vehicles")
        print()

        vehicle_to_scrape = get_next_vehicle(state)

        if not vehicle_to_scrape:
            print("No more vehicles to scrape!")
            return 0

    # Display vehicle info
    print(f"Scraping vehicle:")
    print(f"  Ref No: {vehicle_to_scrape['ref_no']}")
    print(f"  Title: {vehicle_to_scrape.get('title', 'N/A')}")
    print(f"  URL: {vehicle_to_scrape['detail_url']}")
    print()

    # Scrape the vehicle
    try:
        image_mode = None if args.skip_images else args.mode
        result = scrape_vehicle(vehicle_to_scrape["detail_url"], state, mode=image_mode)

        if result:
            print()
            print("=" * 60)
            print("Scraping Complete!")
            print("=" * 60)
            print(f"Ref No: {result['specs'].get('ref_no', 'N/A')}")
            print(f"Title: {result.get('title', 'N/A')}")
            print(f"Images: {result.get('image_count', 0)}")
            print(f"Folder: {config.DAILY_VEHICLE_BASE_DIR / result.get('folder_name', '')}")
            print()
            print(f"Output files:")
            print(f"  - data.json")
            print(f"  - facebook.json")
            print(f"  - metadata.txt")
            print(f"  - images/ ({result.get('image_count', 0)} files)")
            print()
            print(f"Progress: {state.state['current_index']} / {state.state.get('total_available', '?')}")
            return 0
        else:
            print("Failed to scrape vehicle!")
            return 1

    except Exception as e:
        logger.error(f"Error during scraping: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
