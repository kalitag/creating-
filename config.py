# ReviewCheckk Bot Configuration
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Bot Configuration - Using environment variables for security
BOT_TOKEN = os.getenv("BOT_TOKEN", "8327175937:AAGpC7M85iY-kbMVAcKJTrhXzKokWLGctCo")
BOT_NAME = os.getenv("BOT_NAME", "ReviewCheckk Bot")
BOT_USERNAME = os.getenv("BOT_USERNAME", "@Easy_uknowbot")

# Supported Platforms
SUPPORTED_DOMAINS = {
    "amazon": ["amazon.in", "amazon.com"],
    "flipkart": ["flipkart.com"],
    "meesho": ["meesho.com"],
    "myntra": ["myntra.com"],
    "ajio": ["ajio.com"],
    "snapdeal": ["snapdeal.com"],
    "wishlink": ["wishlink.com"]
}

# Shortened URL Services to Expand
SHORTENED_URL_SERVICES = [
    "cutt.ly", "fkrt.cc", "bitli.in", "amzn.to", "amzn-to.co",
    "spoo.me", "da.gd", "wishlink.com", "bit.ly", "tinyurl.com"
]

# Brand List for Title Formatting
BRANDS = [
    "H&M", "Max", "Pantaloons", "United Colors Of Benetton",
    "U.S. Polo Assn.", "Mothercare", "HRX", "Philips", "LOreal",
    "Bath & Body Works", "THE BODY SHOP", "Biotique", "Mamaearth",
    "MCaffeine", "Nivea", "Lotus Herbals", "KAMA AYURVEDA",
    "M.A.C", "Forest Essentials", "Genz", "Nike", "Adidas",
    "Puma", "Reebok", "Levi's", "Zara", "Forever 21"
]

# Default Pin Code for Meesho
DEFAULT_PIN = "110001"

# Advanced Mode Settings
ADVANCED_MODE = False
STOCK_CHECK_ENABLED = False

# Error Messages
ERROR_UNSUPPORTED_LINK = "❌ Unsupported or invalid product link."
ERROR_UNABLE_TO_EXTRACT = "❌ Unable to extract product info."
ERROR_OUT_OF_STOCK = "❌ Out of stock."
ERROR_RATE_LIMITED = "⏳ Rate limited. Please try again later."
ERROR_NETWORK = "🌐 Network error. Please check your connection."

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = "reviewcheckk_bot.log"

# Performance Settings
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "10"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RESPONSE_TIMEOUT = int(os.getenv("RESPONSE_TIMEOUT", "3"))  # seconds

# Security Settings
MAX_MESSAGE_LENGTH = 4096  # Telegram's message limit
MAX_LINKS_PER_MESSAGE = 5  # Prevent spam
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 10  # requests per window

# Cache Settings
CACHE_TTL = 300  # 5 minutes cache for product data
MAX_CACHE_SIZE = 1000  # Maximum cached items
