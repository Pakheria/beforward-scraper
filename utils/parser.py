"""
BE FORWARD Web Scraper - HTML Parser Module
Handles parsing of vehicle detail pages to extract specifications and image URLs.
"""

# Filter XMLParsedAsHTMLWarning before importing BeautifulSoup
import warnings
from bs4 import XMLParsedAsHTMLWarning
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import config


def extract_specs_table(soup: BeautifulSoup) -> dict:
    """
    Extract the spec table data from a vehicle detail page.

    The spec table has a specific structure with pairs of fields.
    Returns a dictionary with the field names as keys.
    """
    specs = {}

    # Initialize all spec fields with empty string
    for field in config.SPEC_FIELDS:
        specs[field] = ""

    # Find the spec table - it has class "specification" or similar
    # The table has rows with pairs of data
    spec_table = soup.find("table", class_="specification")

    if spec_table:
        rows = spec_table.find_all("tr")

        for row in rows:
            cells = row.find_all(["td", "th"])
            # Process cells in pairs (label, value, label, value, ...)
            for i in range(0, len(cells) - 1, 2):
                if i + 1 < len(cells):
                    label = cells[i].get_text(strip=True)
                    value = cells[i + 1].get_text(strip=True)

                    # Map the label to our internal field name
                    if label in config.FIELD_MAPPING:
                        field_name = config.FIELD_MAPPING[label]
                        specs[field_name] = value

    return specs


def get_image_urls(soup: BeautifulSoup) -> list:
    """
    Extract all image URLs from the vehicle detail page.

    Returns a list of high-quality image URLs.
    """
    image_urls = []

    # Find the image gallery - images are in thumbnail lists
    # Look for the main gallery section
    gallery = soup.find("div", id=re.compile(r"gallery|images|vehicle-images", re.I))

    if gallery:
        # Get all image links from thumbnails
        img_links = gallery.find_all("a", href=re.compile(r"\.(jpg|jpeg|png|gif)", re.I))

        for link in img_links:
            href = link.get("href", "")
            if href:
                # Convert to full URL if relative
                full_url = urljoin(config.BASE_URL, href)
                # Prefer large images over thumbnails
                # The site has /small/ and /large/ paths - we want /large/
                full_url = full_url.replace("/small/", "/large/")
                if full_url not in image_urls:
                    image_urls.append(full_url)

    # Alternative: find all images in the page with specific classes
    if not image_urls:
        # Look for images in the ad-gallery or similar container
        gallery_div = soup.find("div", class_=re.compile(r"ad-gallery|vehicle-gallery", re.I))

        if gallery_div:
            images = gallery_div.find_all("img")
            for img in images:
                src = img.get("src", "")
                if src and re.search(r"\.(jpg|jpeg|png|gif)", src, re.I):
                    full_url = urljoin(config.BASE_URL, src)
                    full_url = full_url.replace("/small/", "/large/")
                    if full_url not in image_urls:
                        image_urls.append(full_url)

    return image_urls


def get_zip_download_url(soup: BeautifulSoup) -> str | None:
    """
    Find the 'Download all images' zip file URL.

    The page has a link/button that downloads all images as a zip archive.
    Returns the URL if found, None otherwise.
    """
    # Look for the "Download all images" link or button
    # It's typically near the image gallery
    download_link = soup.find("a", string=re.compile(r"download.*all.*images", re.I))

    if download_link:
        href = download_link.get("href", "")
        if href:
            return urljoin(config.BASE_URL, href)

    # Alternative: look for a link with specific class or ID
    download_link = soup.find("a", class_=re.compile(r"download.*zip|download.*all", re.I))

    if download_link:
        href = download_link.get("href", "")
        if href:
            return urljoin(config.BASE_URL, href)

    # Another approach: look for any link pointing to a .zip file
    all_links = soup.find_all("a", href=re.compile(r"\.zip$", re.I))

    for link in all_links:
        href = link.get("href", "")
        if href:
            full_url = urljoin(config.BASE_URL, href)
            # Verify it's related to images
            if re.search(r"image|photo|picture", full_url, re.I):
                return full_url

    return None


def parse_vehicle_detail(html: str, url: str) -> dict:
    """
    Parse a vehicle detail page and extract all relevant data.

    Args:
        html: The HTML content of the page
        url: The URL of the page (for reference)

    Returns:

    # Filter XML parsing warning (HTML is fine, we parse correctly)
    import warnings
    from bs4 import XMLParsedAsHTMLWarning
    warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

        A dictionary containing all extracted vehicle data
    """
    soup = BeautifulSoup(html, "lxml")

    # Extract specs from the table
    specs = extract_specs_table(soup)

    # Get image URLs
    image_urls = get_image_urls(soup)

    # Get zip download URL
    zip_url = get_zip_download_url(soup)

    # Build the result dictionary
    result = {
        "detail_url": url,
        "specs": specs,
        "image_urls": image_urls,
        "zip_url": zip_url,
        "image_count": len(image_urls),
    }

    return result


def parse_stock_list_item(item_html) -> dict:
    """
    Parse a single vehicle item from the stock list page.

    Args:
        item_html: A BeautifulSoup element representing a vehicle card

    Returns:
        A dictionary with ref_no, title, price, and detail_url
    """
    # Find the link to the detail page
    link = item_html.find("a", href=re.compile(r"/\w+/\w+/[\w\d]+/id/\d+"))

    if not link:
        return None

    detail_url = urljoin(config.BASE_URL, link.get("href", ""))

    # Extract Ref No from URL or page content
    ref_no = ""
    ref_match = re.search(r"/([A-Z]{2}\d+)/id/", detail_url)
    if ref_match:
        ref_no = ref_match.group(1)
    else:
        # Try to find Ref No in the content
        ref_span = item_html.find(string=re.compile(r"Ref\s*\.?\s*No\.?", re.I))
        if ref_span:
            ref_match = re.search(r"[A-Z]{2}\d+", ref_span)
            if ref_match:
                ref_no = ref_match.group(0)

    # Extract title
    title = ""
    title_elem = item_html.find(["h3", "h4", "h5"], class_=re.compile(r"title|vehicle-name", re.I))
    if title_elem:
        title = title_elem.get_text(strip=True)

    return {
        "ref_no": ref_no,
        "title": title,
        "detail_url": detail_url,
    }
