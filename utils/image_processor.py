"""
BE FORWARD Web Scraper - Image Processor Module
Handles image cropping to remove watermarks while preserving quality.
"""

import os
from PIL import Image
import logging

logger = logging.getLogger(__name__)

# Watermark is at the bottom center of the image
# Analysis shows it's approximately 5-8% of the image height
# We'll crop 6-8% from the bottom to remove it completely

DEFAULT_CROP_PERCENTAGE = 7  # Crop 7% from bottom


def crop_bottom(
    image_path: str,
    crop_percentage: int = DEFAULT_CROP_PERCENTAGE,
    overwrite: bool = True,
    quality: int = 95
) -> str:
    """
    Crop the bottom portion of an image to remove the watermark.

    Args:
        image_path: Path to the image file
        crop_percentage: Percentage of height to crop from bottom (5-10)
        overwrite: If True, overwrite original; if False, save as _cropped
        quality: JPEG quality (85-100, higher = less compression, default 95)

    Returns:
        Path to the cropped image file
    """
    try:
        img = Image.open(image_path)
        width, height = img.size

        # Calculate how many pixels to crop from bottom
        crop_pixels = int(height * (crop_percentage / 100))

        # Ensure we don't crop too much
        if crop_pixels < 10:
            crop_pixels = 10
        elif crop_pixels > height * 0.15:  # Don't crop more than 15%
            crop_pixels = int(height * 0.15)

        # Define crop box: (left, top, right, bottom)
        # Crop everything except the bottom portion
        box = (0, 0, width, height - crop_pixels)

        # Crop the image
        cropped_img = img.crop(box)

        # Get file extension before determining output path
        base, ext = os.path.splitext(image_path)

        # Determine output path
        if overwrite:
            output_path = image_path
        else:
            output_path = f"{base}_cropped{ext}"

        # Save with original quality preservation
        # Get original format info if JPEG
        if ext.lower() in ['.jpg', '.jpeg']:
            # Save with specified quality
            cropped_img.save(output_path, 'JPEG', quality=quality, optimize=True)
        else:
            # For PNG and other formats, save without compression loss
            cropped_img.save(output_path, optimize=True)

        logger.debug(f"Cropped {crop_pixels}px from bottom: {output_path}")

        return output_path

    except Exception as e:
        logger.error(f"Error cropping {image_path}: {e}")
        return image_path


def batch_crop_images(
    image_dir: str,
    crop_percentage: int = DEFAULT_CROP_PERCENTAGE,
    quality: int = 95
) -> dict:
    """
    Crop all images in a directory.

    Args:
        image_dir: Directory containing images
        crop_percentage: Percentage to crop from bottom
        quality: JPEG quality for saving

    Returns:
        Dictionary with results: {filename: status, cropped_count, failed_count}
    """
    results = {
        "cropped": [],
        "failed": [],
        "total": 0,
    }

    if not os.path.exists(image_dir):
        logger.error(f"Image directory not found: {image_dir}")
        return results

    # Get all image files
    image_extensions = ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']
    image_files = [
        f for f in os.listdir(image_dir)
        if os.path.splitext(f)[1] in image_extensions
    ]

    results["total"] = len(image_files)

    logger.info(f"Cropping {len(image_files)} images in {image_dir}...")

    for img_file in image_files:
        img_path = os.path.join(image_dir, img_file)

        try:
            cropped_path = crop_bottom(
                img_path,
                crop_percentage=crop_percentage,
                overwrite=True,
                quality=quality
            )
            results["cropped"].append(img_file)
            logger.debug(f"Cropped: {img_file}")

        except Exception as e:
            logger.error(f"Failed to crop {img_file}: {e}")
            results["failed"].append(img_file)

    logger.info(
        f"Cropping complete: "
        f"{len(results['cropped'])} cropped, "
        f"{len(results['failed'])} failed"
    )

    return results


def auto_crop_after_download(
    image_urls: list,
    ref_no: str,
    output_dir: str,
    crop_percentage: int = DEFAULT_CROP_PERCENTAGE,
    quality: int = 95
) -> list:
    """
    Download images and automatically crop them.

    This is meant to be called from the downloader after images are downloaded.

    Args:
        image_urls: List of image URLs (not used, files already downloaded)
        ref_no: Reference number for folder naming
        output_dir: Directory containing downloaded images
        crop_percentage: Percentage to crop from bottom
        quality: JPEG quality for saving

    Returns:
        List of cropped file paths
    """
    images_dir = os.path.join(output_dir, ref_no, "images")

    if not os.path.exists(images_dir):
        logger.warning(f"Images directory not found: {images_dir}")
        return []

    results = batch_crop_images(images_dir, crop_percentage, quality)

    # Return list of successfully cropped files
    cropped_files = [
        os.path.join(images_dir, f)
        for f in results["cropped"]
    ]

    return cropped_files
