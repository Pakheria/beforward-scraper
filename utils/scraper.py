"""
BE FORWARD Web Scraper - Core Scraping Module
Handles fetching pages and extracting vehicle links from stock listings.
"""

import time
import random
import re
import logging
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
import config
from . import parser

# Set up logging
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL))
logger = logging.getLogger(__name__)


def fetch_page(url: str, session: requests.Session = None) -> str | None:
    """
    Fetch a page from BE FORWARD with retry logic and rate limiting.

    Args:
        url: The URL to fetch
        session: Optional requests Session for connection pooling

    Returns:
        The HTML content as a string, or None if failed
    """
    if session is None:
        session = requests.Session()

    for attempt in range(config.MAX_RETRIES):
        try:
            response = session.get(
                url,
                headers=config.HEADERS,
                timeout=config.TIMEOUT,
            )

            response.raise_for_status()

            # Rate limiting - add random delay between requests
            delay = random.uniform(config.REQUEST_DELAY_MIN, config.REQUEST_DELAY_MAX)
            time.sleep(delay)

            return response.text

        except requests.RequestException as e:
            logger.warning(f"Attempt {attempt + 1}/{config.MAX_RETRIES} failed for {url}: {e}")
            if attempt < config.MAX_RETRIES - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                logger.error(f"Failed to fetch {url} after {config.MAX_RETRIES} attempts")
                return None


def get_total_pages(html: str) -> int:
    """
    Extract the total number of pages from the stock list page.

    Args:
        html: The HTML content of the stock list page

    Returns:
        The total number of pages
    """
    soup = BeautifulSoup(html, "lxml")

    # Look for pagination links
    pagination = soup.find("div", class_=re.compile(r"pagination|pager", re.I))

    if pagination:
        # Find all page links
        page_links = pagination.find_all("a", href=re.compile(r"page=\d+"))

        if page_links:
            # Get the highest page number
            max_page = 1
            for link in page_links:
                match = re.search(r"page=(\d+)", link.get("href", ""))
                if match:
                    page_num = int(match.group(1))
                    max_page = max(max_page, page_num)

            return max_page

    # Alternative: look for "Next Page" link or similar
    next_link = soup.find("a", string=re.compile(r"next|»", re.I))
    if next_link:
        match = re.search(r"page=(\d+)", next_link.get("href", ""))
        if match:
            return int(match.group(1))

    # If no pagination found, assume single page
    return 1


def get_vehicle_links(html: str, base_url: str = config.STOCK_LIST_URL) -> List[Dict[str, str]]:
    """
    Extract vehicle links from a stock list page.

    Args:
        html: The HTML content of the stock list page
        base_url: The base URL for resolving relative links

    Returns:
        A list of dictionaries containing ref_no, title, and detail_url
    """
    soup = BeautifulSoup(html, "lxml")
    vehicles = []
    seen_urls = set()

    # Find all links that contain '/id/' - this is the vehicle detail page pattern
    all_links = soup.find_all("a", href=True)

    for link in all_links:
        href = link.get("href", "")

        # Look for vehicle detail URLs: /make/model/refno/id/number/
        # Pattern: /word/word/CB12345/id/67890/
        if "/id/" in href and href.count("/") >= 4:
            # Extract the URL
            full_url = href if href.startswith("http") else f"{config.BASE_URL}{href}"

            # Skip if we've already seen this URL
            if full_url in seen_urls:
                continue

            # Extract Ref No from URL pattern
            # URL format: /make/model/REFNO/id/number/
            # Ref numbers can be uppercase or lowercase (e.g., CB12345 or cb12345)
            ref_match = re.search(r"/([a-zA-Z]{2}\d+)/id/\d+", full_url)
            if not ref_match:
                # Try alternative pattern: /CB12345/id/67890/
                ref_match = re.search(r"^/([a-zA-Z]{2}\d+)/id/\d+", href)

            ref_no = ref_match.group(1).upper() if ref_match else ""

            # Try to get title from link text or nearby elements
            title = ""
            link_text = link.get_text(strip=True)
            if link_text and len(link_text) > 5 and not link_text.isdigit():
                title = link_text

            seen_urls.add(full_url)
            vehicles.append({
                "ref_no": ref_no,
                "title": title,
                "detail_url": full_url,
            })

    logger.info(f"Found {len(vehicles)} unique vehicle links on page")
    return vehicles


def scrape_stock_list(max_vehicles: int = None) -> List[Dict[str, str]]:
    """
    Scrape the stock list and collect vehicle detail page URLs.

    Args:
        max_vehicles: Maximum number of vehicles to scrape (None = all)

    Returns:
        A list of dictionaries with ref_no, title, and detail_url
    """
    session = requests.Session()
    all_vehicles = []
    page = 1

    logger.info(f"Starting stock list scrape (max vehicles: {max_vehicles or 'all'})")

    while True:
        # Check if we've reached the limit
        if max_vehicles and len(all_vehicles) >= max_vehicles:
            logger.info(f"Reached vehicle limit of {max_vehicles}")
            break

        # Construct URL for current page
        if page == 1:
            url = config.STOCK_LIST_URL
        else:
            url = f"{config.BASE_URL}/stocklist/page={page}/stock_country=44/sortkey=n"

        logger.info(f"Fetching page {page}: {url}")

        html = fetch_page(url, session)

        if not html:
            logger.error(f"Failed to fetch page {page}, stopping")
            break

        # Get total pages on first request
        if page == 1:
            total_pages = get_total_pages(html)
            logger.info(f"Total pages available: {total_pages}")

        # Extract vehicle links
        vehicles = get_vehicle_links(html, url)

        if not vehicles:
            logger.warning(f"No vehicles found on page {page}, stopping")
            break

        # Add to our collection (respecting the limit)
        remaining = max_vehicles - len(all_vehicles) if max_vehicles else len(vehicles)
        all_vehicles.extend(vehicles[:remaining])

        logger.info(f"Collected {len(all_vehicles)} vehicles so far")

        # Check if we should continue
        if page >= total_pages:
            logger.info(f"Reached last page ({page}/{total_pages})")
            break

        if max_vehicles and len(all_vehicles) >= max_vehicles:
            logger.info(f"Reached vehicle limit of {max_vehicles}")
            break

        page += 1

    logger.info(f"Stock list scrape complete. Total vehicles: {len(all_vehicles)}")
    return all_vehicles


def scrape_vehicle_detail(url: str, session: requests.Session = None) -> Dict | None:
    """
    Scrape a single vehicle detail page.

    Args:
        url: The vehicle detail page URL
        session: Optional requests Session

    Returns:
        A dictionary with all vehicle data, or None if failed
    """
    if session is None:
        session = requests.Session()

    logger.info(f"Fetching vehicle detail: {url}")

    html = fetch_page(url, session)

    if not html:
        logger.error(f"Failed to fetch vehicle detail: {url}")
        return None

    return parser.parse_vehicle_detail(html, url)
