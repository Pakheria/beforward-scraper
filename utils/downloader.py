"""
BE FORWARD Web Scraper - Downloader Module
Handles downloading individual images or zip archives.
"""

import os
from . import image_processor
import zipfile
import logging
from pathlib import Path
from typing import List
import requests
import config

# Set up logging
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL))
logger = logging.getLogger(__name__)


def download_file(url: str, output_path: Path, session: requests.Session = None) -> bool:
    """
    Download a single file with retry logic.

    Args:
        url: The URL to download from
        output_path: The path to save the file to
        session: Optional requests Session

    Returns:
        True if successful, False otherwise
    """
    if session is None:
        session = requests.Session()

    try:
        response = session.get(
            url,
            headers=config.HEADERS,
            timeout=config.TIMEOUT,
            stream=True,
        )
        response.raise_for_status()

        # Create parent directories if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file in chunks
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        logger.debug(f"Downloaded: {output_path.name}")
        return True

    except Exception as e:
        logger.error(f"Failed to download {url}: {e}")
        return False


def download_individual_images(image_urls: List[str], ref_no: str, output_dir: Path = None) -> List[str]:
    """
    Download individual images for a vehicle.

    Args:
        image_urls: List of image URLs
        ref_no: Vehicle reference number (used for folder naming)
        output_dir: Base output directory (default: config.VEHICLES_DIR)

    Returns:
        List of downloaded file paths
    """
    if output_dir is None:
        output_dir = config.VEHICLES_DIR

    vehicle_dir = output_dir / ref_no
    vehicle_dir.mkdir(parents=True, exist_ok=True)

    downloaded_files = []
    session = requests.Session()

    for i, url in enumerate(image_urls, 1):
        # Determine file extension
        ext = ".jpg"
        if ".png" in url.lower():
            ext = ".png"
        elif ".jpeg" in url.lower():
            ext = ".jpeg"

        # Create filename with leading zeros for proper sorting
        filename = f"{ref_no}_{i:03d}{ext}"
        output_path = vehicle_dir / filename

        if download_file(url, output_path, session):
            downloaded_files.append(str(output_path))

            # Crop image to remove bottom watermark (if enabled)
            if config.ENABLE_CROPPING:
                try:
                    cropped_path = image_processor.crop_bottom(
                        str(output_path),
                        crop_percentage=config.CROP_PERCENTAGE,
                        overwrite=True,
                        quality=config.CROP_QUALITY
                    )
                    logger.debug(f"Auto-cropped: {os.path.basename(str(output_path))}")
                except Exception as e:
                    logger.warning(f"Could not crop image: {e}")


    logger.info(f"Downloaded {len(downloaded_files)}/{len(image_urls)} images for {ref_no}")
    return downloaded_files


def download_and_extract_zip(zip_url: str, ref_no: str, output_dir: Path = None) -> List[str]:
    """
    Download and extract a zip archive of images.

    Args:
        zip_url: URL of the zip file
        ref_no: Vehicle reference number (used for folder naming)
        output_dir: Base output directory (default: config.VEHICLES_DIR)

    Returns:
        List of extracted file paths
    """
    if output_dir is None:
        output_dir = config.VEHICLES_DIR

    vehicle_dir = output_dir / ref_no
    vehicle_dir.mkdir(parents=True, exist_ok=True)

    # Download zip file
    zip_path = vehicle_dir / f"{ref_no}_images.zip"

    if not download_file(zip_url, zip_path):
        logger.error(f"Failed to download zip file for {ref_no}")
        return []

    # Extract zip file
    extracted_files = []
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            # Get list of files in zip
            file_list = zip_ref.namelist()

            # Extract all files
            zip_ref.extractall(vehicle_dir)

            # Track extracted files
            for file_name in file_list:
                # Skip __MACOSX and other hidden files
                if not file_name.startswith("_") and not file_name.startswith("."):
                    extracted_path = vehicle_dir / file_name
                    if extracted_path.exists():
                        extracted_files.append(str(extracted_path))

        # Clean up zip file
        zip_path.unlink()

        logger.info(f"Extracted {len(extracted_files)} files from zip for {ref_no}")

    except zipfile.BadZipFile:
        logger.error(f"Bad zip file for {ref_no}: {zip_url}")
        # Clean up bad zip file
        if zip_path.exists():
            zip_path.unlink()
        return []

    except Exception as e:
        logger.error(f"Error extracting zip for {ref_no}: {e}")
        return []

    return extracted_files


def download_vehicle_images(
    image_urls: List[str],
    zip_url: str,
    ref_no: str,
    mode: str = config.DEFAULT_IMAGE_MODE,
    output_dir: Path = None,
) -> dict:
    """
    Download images for a vehicle using the specified mode.

    Args:
        image_urls: List of individual image URLs
        zip_url: URL of the zip archive (may be None)
        ref_no: Vehicle reference number
        mode: Download mode ("individual" or "zip")
        output_dir: Base output directory

    Returns:
        Dictionary with download results:
        {
            "mode": mode,
            "folder": str,
            "count": int,
            "files": List[str]
        }
    """
    if output_dir is None:
        output_dir = config.VEHICLES_DIR

    vehicle_dir = output_dir / ref_no
    files = []

    if mode == config.IMAGE_MODE_ZIP and zip_url:
        # Use zip download mode
        files = download_and_extract_zip(zip_url, ref_no, output_dir)
    else:
        # Use individual image download mode
        if not image_urls:
            logger.warning(f"No image URLs available for {ref_no}")
        else:
            files = download_individual_images(image_urls, ref_no, output_dir)

    return {
        "mode": mode,
        "folder": str(vehicle_dir),
        "count": len(files),
        "files": files,
    }
