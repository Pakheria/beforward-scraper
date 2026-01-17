"""
BE FORWARD Web Scraper - Utility Modules
"""

from .parser import parse_vehicle_detail, extract_specs_table, get_image_urls, get_zip_download_url
from .scraper import get_vehicle_links, get_total_pages, fetch_page
from .downloader import download_individual_images, download_and_extract_zip

__all__ = [
    "parse_vehicle_detail",
    "extract_specs_table",
    "get_image_urls",
    "get_zip_download_url",
    "get_vehicle_links",
    "get_total_pages",
    "fetch_page",
    "download_individual_images",
    "download_and_extract_zip",
]
