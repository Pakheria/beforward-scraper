"""
BE FORWARD Web Scraper - Configuration Settings
"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
DATA_DIR = OUTPUT_DIR / "data"
VEHICLES_DIR = OUTPUT_DIR / "vehicles"

# Create directories if they don't exist
for dir_path in [OUTPUT_DIR, DATA_DIR, VEHICLES_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# BE FORWARD URLs
BASE_URL = "https://www.beforward.jp"

# Country stock codes for BE FORWARD
# Source: https://www.beforward.jp stock locations
COUNTRY_CODES = {
    "uae": 44,        # United Arab Emirates
    "japan": 1,       # Japan
    "korea": 2,       # Korea
    "thailand": 3,    # Thailand
    "uk": 5,          # United Kingdom
    "singapore": 6,   # Singapore
    "australia": 7,   # Australia
    "philippines": 8, # Philippines
    "belgium": 9,     # Belgium
    "south_africa": 10, # South Africa
    "new_zealand": 11,  # New Zealand
    "tanzania": 12,     # Tanzania
    "zambia": 13,       # Zambia
    "kenya": 14,        # Kenya
    "uganda": 15,       # Uganda
    "mozambique": 16,   # Mozambique
    "zimbabwe": 17,     # Zimbabwe
    "botswana": 18,     # Botswana
    "namibia": 19,      # Namibia
    "lesotho": 20,      # Lesotho
    "malawi": 21,       # Malawi
    "rwanda": 22,       # Rwanda
    "burundi": 23,      # Burundi
    "ghana": 24,        # Ghana
    "senegal": 25,      # Senegal
    "gabon": 26,        # Gabon
    "nigeria": 27,      # Nigeria
    "angola": 28,       # Angola
    "egypt": 29,        # Egypt
    "saudi_arabia": 30, # Saudi Arabia
    "georgia": 31,      # Georgia
    "germany": 32,      # Germany
    "usa": 33,          # USA
    "canada": 34,       # Canada
    "ukraine": 35,      # Ukraine
    "armenia": 36,      # Armenia
    "azerbaijan": 37,   # Azerbaijan
    "russia": 38,       # Russia
    "kyrgyzstan": 39,   # Kyrgyzstan
    "bangladesh": 40,   # Bangladesh
    "pakistan": 41,     # Pakistan
    "mongolia": 42,     # Mongolia
    "sri_lanka": 43,    # Sri Lanka
    "mexico": 45,       # Mexico
    "taiwan": 46,       # Taiwan
    "albania": 47,      # Albania
}

# Default country (UAE)
DEFAULT_COUNTRY = "uae"
DEFAULT_COUNTRY_CODE = COUNTRY_CODES[DEFAULT_COUNTRY]

# Current configuration (can be overridden by CLI args or config file)
CURRENT_COUNTRY = DEFAULT_COUNTRY
CURRENT_COUNTRY_CODE = DEFAULT_COUNTRY_CODE

def get_stock_list_url(country: str = None) -> str:
    """Get the stock list URL for a specific country."""
    if country:
        country_lower = country.lower()
        if country_lower in COUNTRY_CODES:
            code = COUNTRY_CODES[country_lower]
            return f"{BASE_URL}/stocklist/stock_country={code}/sortkey=n"
        elif country.isdigit():
            # Direct country code
            return f"{BASE_URL}/stocklist/stock_country={country}/sortkey=n"

    # Use current country setting
    return f"{BASE_URL}/stocklist/stock_country={CURRENT_COUNTRY_CODE}/sortkey=n"

# Default stock list URL (UAE)
STOCK_LIST_URL = get_stock_list_url()

# Request settings
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Rate limiting
REQUEST_DELAY_MIN = 1.0  # seconds
REQUEST_DELAY_MAX = 3.0  # seconds
MAX_RETRIES = 3
TIMEOUT = 30  # seconds

# Pagination
ITEMS_PER_PAGE = 25

# Image download modes
IMAGE_MODE_INDIVIDUAL = "individual"
IMAGE_MODE_ZIP = "zip"

# Image cropping settings
ENABLE_CROPPING = True  # Automatically crop watermarks from downloaded images
CROP_PERCENTAGE = 7  # Percentage of image height to crop from bottom (5-10%)
CROP_QUALITY = 95  # JPEG quality when saving cropped images (85-100, higher = better)

# Default settings
DEFAULT_VEHICLE_LIMIT = None  # None = scrape all vehicles
DEFAULT_IMAGE_MODE = IMAGE_MODE_INDIVIDUAL

# Spec table field mappings (from the website's labels to our internal keys)
FIELD_MAPPING = {
    "Ref. No.": "ref_no",
    "Mileage": "mileage",
    "Chassis No.": "chassis_no",
    "Engine Code": "engine_code",
    "Model Code": "model_code",
    "Steering": "steering",
    "Engine Size": "engine_size",
    "Ext. Color": "ext_color",
    "Location": "location",
    "Fuel": "fuel",
    "Version/Class": "version_class",
    "Seats": "seats",
    "Drive": "drive",
    "Doors": "doors",
    "Transmission": "transmission",
}

# Fields to extract (in order for consistent output)
SPEC_FIELDS = [
    "ref_no",
    "mileage",
    "chassis_no",
    "engine_code",
    "model_code",
    "steering",
    "engine_size",
    "ext_color",
    "location",
    "fuel",
    "version_class",
    "seats",
    "drive",
    "doors",
    "transmission",
]

# Output filenames
JSON_OUTPUT_FILE = DATA_DIR / "vehicles.json"
CSV_OUTPUT_FILE = DATA_DIR / "vehicles.csv"
CHECKPOINT_FILE = DATA_DIR / ".checkpoint.json"

# Logging
LOG_LEVEL = "INFO"

# =============================================================================
# DAILY MODE SETTINGS
# =============================================================================

# State tracking
STATE_DIR = BASE_DIR / "state"
STATE_FILE = STATE_DIR / "scraper_state.json"

# Daily mode organized output structure
DAILY_VEHICLE_BASE_DIR = OUTPUT_DIR / "vehicles"

# Facebook post settings
FACEBOOK_POST_TEMPLATE = {
    "headline": "🚗 FOR SALE: {title}",
    "intro": "Check out this amazing deal from BE FORWARD!",
    "emojis": {
        "location": "📍",
        "price": "💰",
        "mileage": "📏",
        "engine": "⚙️",
        "transmission": "🔄",
        "drive": "🚗",
        "fuel": "⛽",
    },
    "cta": "DM for inquiries! 📞\n\n{link}",
    "default_hashtags": ["#BEFORWARD", "#Japanesecars", "#Dubai", "#UAE"],
}

# Service settings
SERVICE_NAME = "beforward-daily"
SERVICE_DESCRIPTION = "BE FORWARD Daily Vehicle Scraper"
SERVICE_USER = None  # None = current user, or specify username
SERVICE_WORKING_DIR = str(BASE_DIR)
SERVICE_EXECUTABLE = "/usr/bin/python3"
SERVICE_SCRIPT = str(BASE_DIR / "daily_scraper.py")

# Logging for service
SERVICE_LOG_FILE = STATE_DIR / "scraper.log"
