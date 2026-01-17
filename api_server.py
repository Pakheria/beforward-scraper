#!/usr/bin/env python3
"""
BE FORWARD Scraper - Simple HTTP API Server
Provides REST endpoints for n8n to trigger scraping and retrieve data.
"""

import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

import config

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for n8n

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_latest_vehicle() -> Dict | None:
    """
    Get the most recently scraped vehicle data.

    Returns:
        Dictionary with vehicle data or None if no vehicles found
    """
    vehicles_dir = config.DAILY_VEHICLE_BASE_DIR

    if not vehicles_dir.exists():
        return None

    # Get all vehicle folders, sorted by modification time (newest first)
    vehicle_folders = sorted(
        [d for d in vehicles_dir.iterdir() if d.is_dir()],
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )

    if not vehicle_folders:
        return None

    # Get the latest vehicle folder
    latest_folder = vehicle_folders[0]

    # Load data.json
    data_file = latest_folder / "data.json"
    if not data_file.exists():
        return None

    with open(data_file, "r") as f:
        vehicle_data = json.load(f)

    # Add folder path for image retrieval
    vehicle_data["folder_path"] = str(latest_folder)

    # Load facebook.json if exists
    fb_file = latest_folder / "facebook.json"
    if fb_file.exists():
        with open(fb_file, "r") as f:
            vehicle_data["facebook_post"] = json.load(f)

    # Get list of images
    images_dir = latest_folder / "images"
    if images_dir.exists():
        vehicle_data["images"] = [
            str(images_dir / f)
            for f in sorted(os.listdir(images_dir))
            if f.lower().endswith(('.jpg', '.jpeg', '.png'))
        ]

    return vehicle_data


def get_all_vehicles(limit: int = 10) -> list:
    """
    Get all scraped vehicles, sorted by newest first.

    Args:
        limit: Maximum number of vehicles to return

    Returns:
        List of vehicle data dictionaries
    """
    vehicles_dir = config.DAILY_VEHICLE_BASE_DIR

    if not vehicles_dir.exists():
        return []

    # Get all vehicle folders, sorted by modification time (newest first)
    vehicle_folders = sorted(
        [d for d in vehicles_dir.iterdir() if d.is_dir()],
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )[:limit]

    vehicles = []
    for folder in vehicle_folders:
        data_file = folder / "data.json"
        if data_file.exists():
            with open(data_file, "r") as f:
                data = json.load(f)
                data["folder_path"] = str(folder)
                vehicles.append(data)

    return vehicles


@app.route("/", methods=["GET"])
def index():
    """Root endpoint with API information."""
    return jsonify({
        "service": "BE FORWARD Scraper API",
        "version": "1.0",
        "endpoints": {
            "POST /scrape": "Trigger daily scraper",
            "POST /scrape/force": "Force scrape even if already ran today",
            "GET /vehicle/latest": "Get latest scraped vehicle",
            "GET /vehicle/all": "Get all vehicles (limit=10)",
            "GET /vehicle/<ref_no>": "Get vehicle by reference number",
            "GET /images/<ref_no>": "Get list of images for a vehicle",
            "GET /image/<ref_no>/<filename>": "Download a specific image",
            "GET /health": "Health check",
        }
    })


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "output_dir": str(config.DAILY_VEHICLE_BASE_DIR),
        "state_file": str(config.STATE_FILE)
    })


@app.route("/scrape", methods=["POST"])
def scrape():
    """
    Trigger the daily scraper.

    Request body (optional):
    {
        "force": false,
        "country": "uae",
        "skip_images": false,
        "mode": "individual"
    }
    """
    try:
        data = request.get_json() or {}

        # Build command
        cmd = [sys.executable, "daily_scraper.py"]

        if data.get("force"):
            cmd.append("--force")

        if data.get("country"):
            cmd.extend(["--country", data["country"]])

        if data.get("skip_images"):
            cmd.append("--skip-images")

        if data.get("mode"):
            cmd.extend(["--mode", data["mode"]])

        if data.get("no_crop"):
            cmd.append("--no-crop")

        # Run scraper
        logger.info(f"Running scraper: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
            cwd=str(Path(__file__).parent)
        )

        if result.returncode == 0:
            # Get the latest scraped vehicle
            latest = get_latest_vehicle()
            return jsonify({
                "success": True,
                "message": "Scraping completed successfully",
                "vehicle": latest,
                "stdout": result.stdout
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": "Scraping failed",
                "stderr": result.stderr,
                "stdout": result.stdout
            }), 500

    except subprocess.TimeoutExpired:
        return jsonify({
            "success": False,
            "message": "Scraping timed out after 5 minutes"
        }), 504
    except Exception as e:
        logger.exception("Error during scraping")
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@app.route("/scrape/force", methods=["POST"])
def scrape_force():
    """Force scrape even if already ran today."""
    return scrape()  # This will check request body for force flag


@app.route("/vehicle/latest", methods=["GET"])
def vehicle_latest():
    """Get the latest scraped vehicle."""
    vehicle = get_latest_vehicle()

    if vehicle:
        # Remove absolute paths for API responses
        if "folder_path" in vehicle:
            vehicle["folder_path"] = os.path.basename(vehicle["folder_path"])
        if "image_folder" in vehicle:
            vehicle["image_folder"] = vehicle["folder_path"] + "/images"
        return jsonify(vehicle), 200
    else:
        return jsonify({"error": "No vehicles found"}), 404


@app.route("/vehicle/all", methods=["GET"])
def vehicle_all():
    """Get all scraped vehicles."""
    limit = request.args.get("limit", 10, type=int)
    vehicles = get_all_vehicles(limit)

    # Clean up paths
    for v in vehicles:
        if "folder_path" in v:
            v["folder_path"] = os.path.basename(v["folder_path"])
        if "image_folder" in v:
            v["image_folder"] = v["folder_path"] + "/images"
        if "images" in v:
            v["images"] = [os.path.basename(p) for p in v["images"]]

    return jsonify(vehicles), 200


@app.route("/vehicle/<ref_no>", methods=["GET"])
def vehicle_by_ref(ref_no: str):
    """Get a specific vehicle by reference number."""
    vehicles_dir = config.DAILY_VEHICLE_BASE_DIR

    # Find folder matching the ref number
    for folder in vehicles_dir.iterdir():
        if folder.is_dir() and ref_no.upper() in folder.name.upper():
            data_file = folder / "data.json"
            if data_file.exists():
                with open(data_file, "r") as f:
                    data = json.load(f)
                    data["folder_path"] = folder.name
                    return jsonify(data), 200

    return jsonify({"error": f"Vehicle {ref_no} not found"}), 404


@app.route("/images/<ref_no>", methods=["GET"])
def vehicle_images(ref_no: str):
    """Get list of images for a vehicle."""
    vehicles_dir = config.DAILY_VEHICLE_BASE_DIR

    for folder in vehicles_dir.iterdir():
        if folder.is_dir() and ref_no.upper() in folder.name.upper():
            images_dir = folder / "images"
            if images_dir.exists():
                images = [
                    f for f in os.listdir(images_dir)
                    if f.lower().endswith(('.jpg', '.jpeg', '.png'))
                ]
                return jsonify({
                    "ref_no": ref_no,
                    "folder": folder.name,
                    "images": sorted(images)
                }), 200

    return jsonify({"error": f"Images for {ref_no} not found"}), 404


@app.route("/image/<ref_no>/<filename>", methods=["GET"])
def get_image(ref_no: str, filename: str):
    """Download a specific image file."""
    vehicles_dir = config.DAILY_VEHICLE_BASE_DIR

    for folder in vehicles_dir.iterdir():
        if folder.is_dir() and ref_no.upper() in folder.name.upper():
            images_dir = folder / "images"
            image_path = images_dir / filename

            if image_path.exists():
                return send_file(image_path)

    return jsonify({"error": "Image not found"}), 404


@app.route("/webhook/new-vehicle", methods=["POST"])
def webhook_new_vehicle():
    """
    Webhook endpoint for n8n to poll for new vehicles.
    Returns the latest vehicle that hasn't been posted yet.

    This works in conjunction with a state file to track which vehicles
    have been sent to n8n for Facebook posting.
    """
    # Get posted vehicles state
    posted_state_file = config.STATE_DIR / "posted_vehicles.json"
    posted_refs = set()

    if posted_state_file.exists():
        with open(posted_state_file, "r") as f:
            posted_refs = set(json.load(f).get("posted_vehicles", []))

    # Get latest vehicle
    latest = get_latest_vehicle()

    if not latest:
        return jsonify({"message": "No vehicles found"}), 404

    ref_no = latest.get("specs", {}).get("ref_no", "")

    if ref_no in posted_refs:
        return jsonify({
            "message": "No new vehicles to post",
            "latest_ref": ref_no
        }), 200

    # Mark as posted
    posted_refs.add(ref_no)
    posted_state_file.parent.mkdir(parents=True, exist_ok=True)
    with open(posted_state_file, "w") as f:
        json.dump({"posted_vehicles": list(posted_refs)}, f)

    # Return vehicle data for posting
    return jsonify({
        "vehicle": latest,
        "post_required": True
    }), 200


if __name__ == "__main__":
    # Run Flask server
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False  # Set to True for development
    )
