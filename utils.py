# ReviewCheckk Bot - Utility Functions
import re
import logging
import time
from collections import defaultdict
from urllib.parse import urlparse, parse_qs, urlencode
from typing import List, Optional
import requests
from config import (
    SHORTENED_URL_SERVICES, 
    REQUEST_TIMEOUT, 
    MAX_RETRIES,
    SUPPORTED_DOMAINS,
    BRANDS,
    LOG_LEVEL,
    LOG_FILE,
    RATE_LIMIT_WINDOW,
    RATE_LIMIT_MAX_REQUESTS
)
from url_resolver import url_resolver

logger = logging.getLogger(__name__)

def setup_logging():
    """Configure logging for the bot."""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename=LOG_FILE
    )
    console = logging.StreamHandler()
    console.setLevel(getattr(logging, LOG_LEVEL.upper()))
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

class RateLimiter:
    """Simple rate limiter to prevent spam."""
    
    def __init__(self):
        self.requests = defaultdict(list)
    
    def allow_request(self, user_id: int) -> bool:
        """Check if user is allowed to make a request."""
        now = time.time()
        user_requests = self.requests[user_id]
        
        # Remove old requests outside the window
        user_requests[:] = [req_time for req_time in user_requests if now - req_time < RATE_LIMIT_WINDOW]
        
        # Check if under limit
        if len(user_requests) < RATE_LIMIT_MAX_REQUESTS:
            user_requests.append(now)
            return True
        
        return False

def unshorten_url(url: str) -> str:
    """Expand shortened URLs to their original form using advanced resolver."""
    try:
        result = url_resolver.resolve_url(url)
        if result['error']:
            logger.warning(f"URL resolution failed: {result['error']}")
            return url
        return result['final_url']
    except Exception as e:
        logger.error(f"Error expanding URL {url}: {str(e)}")
        return url

def clean_link(url: str) -> str:
    """Remove affiliate tags and UTM parameters from URL."""
    try:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Parameters to remove (affiliate and tracking)
        params_to_remove = {
            'ref', 'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'aff', 'mc', 'sr', 'icid', 'clickid', 'offer_id', 'aff_id', 'affid',
            'tag', 'linkCode', 'creative', 'creativeASIN', 'ascsubtag', 'gclid',
            'fbclid', 'msclkid', '_branch_match_id'
        }
        
        # Remove affiliate and tracking parameters
        clean_params = {
            k: v for k, v in query_params.items() 
            if not any(param in k.lower() for param in params_to_remove)
        }
        
        # Reconstruct clean URL
        clean_query = urlencode(clean_params, doseq=True)
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if clean_query:
            clean_url += f"?{clean_query}"
        
        return clean_url
    except Exception as e:
        logger.error(f"Error cleaning link {url}: {str(e)}")
        return url

def detect_platform(url: str) -> Optional[str]:
    """Detect which e-commerce platform the URL belongs to using advanced resolver."""
    try:
        result = url_resolver.resolve_url(url)
        return result['platform']
    except Exception as e:
        logger.error(f"Error detecting platform for {url}: {str(e)}")
        return None

def extract_links(text: str) -> List[str]:
    """Extract all URLs from text or caption."""
    if not text:
        return []
    
    # Regex to match URLs (http, https, www)
    url_patterns = [
        r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*(?:\?[\w=&%-]*)?(?:#[\w-]*)?',
        r'www\.(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*(?:\?[\w=&%-]*)?(?:#[\w-]*)?'
    ]
    
    links = []
    for pattern in url_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if not match.startswith(('http://', 'https://')):
                match = 'https://' + match
            links.append(match)
    
    return list(set(links))  # Remove duplicates

def format_title(product_data: dict) -> str:
    """Format title according to ReviewCheckk Bot Master Rulebook."""
    try:
        # Extract relevant data
        brand = product_data.get('brand', '').strip()
        title = product_data.get('title', '').strip()
        price = product_data.get('price', '')
        category = product_data.get('category', '').lower()
        gender = product_data.get('gender', '').strip()
        quantity = product_data.get('quantity', '').strip()
        
        # Handle missing brand
        if not brand:
            # Try to extract brand from title
            for b in BRANDS:
                if b.lower() in title.lower():
                    brand = b
                    break
        
        # Clean title by removing brand, price, and fluff
        clean_title = title
        if brand:
            clean_title = re.sub(re.escape(brand), '', clean_title, flags=re.IGNORECASE)
        
        # Remove price mentions
        clean_title = re.sub(r'[\d,]+(?:\.\d+)?\s*(?:rs|₹|inr)', '', clean_title, flags=re.IGNORECASE)
        
        # Remove marketing fluff
        fluff_words = [
            'best offer', 'limited time', 'special offer', 'deal of the day', 
            'exclusive', 'only', 'just', 'hurry', 'sale', 'discount', 'offer',
            'combo', 'set of', 'pack of', 'bundle', 'free', 'gift', 'new',
            'latest', 'trending', 'hot', 'popular', 'fashion', 'stylish',
            'premium', 'luxury', 'branded', 'original', 'authentic'
        ]
        for word in fluff_words:
            clean_title = re.sub(r'\b' + re.escape(word) + r'\b', '', clean_title, flags=re.IGNORECASE)
        
        # Remove duplicate words
        words = clean_title.split()
        seen = set()
        unique_words = []
        for word in words:
            if word.lower() not in seen:
                seen.add(word.lower())
                unique_words.append(word)
        clean_title = ' '.join(unique_words)
        
        # Trim extra spaces and punctuation
        clean_title = re.sub(r'\s+', ' ', clean_title).strip(' ,.-')
        
        # Format based on category
        if any(cat in category for cat in ['clothing', 'apparel', 'footwear', 'fashion']):
            # Clothing format: [Brand] [Gender] [Quantity] [Product Name]
            parts = []
            if brand:
                parts.append(brand)
            if gender:
                parts.append(gender)
            if quantity:
                parts.append(quantity)
            parts.append(clean_title)
            formatted = ' '.join(parts)
        else:
            # Non-clothing format: [Brand] [Product Title]
            parts = []
            if brand:
                parts.append(brand)
            parts.append(clean_title)
            formatted = ' '.join(parts)
        
        # Add price if available
        if price and price != "Price unavailable":
            formatted += f" from @{format_price_number(price)} rs"
        
        # Ensure title is 5-8 words max
        words = formatted.split()
        if len(words) > 8:
            formatted = ' '.join(words[:8])
        
        return formatted.strip()
    except Exception as e:
        logger.error(f"Error formatting title: {str(e)}")
        # Fallback to clean extracted title
        return product_data.get('title', '').strip()

def format_price_number(price_str: str) -> str:
    """Extract and format price number."""
    if not price_str or price_str == "Price unavailable":
        return "Price unavailable"
    
    # Extract numeric value
    numeric_price = re.sub(r'[^\d]', '', str(price_str))
    if not numeric_price:
        return "Price unavailable"
    
    return numeric_price

def get_lowest_price(price_data) -> Optional[int]:
    """Get lowest price from price data (for multiple sizes/options)."""
    try:
        if isinstance(price_data, list):
            # If price_data is a list of prices, return the lowest
            prices = []
            for p in price_data:
                num = re.sub(r'[^\d]', '', str(p))
                if num:
                    prices.append(int(num))
            return min(prices) if prices else None
        elif isinstance(price_data, dict):
            # If price_data is a dict of size:price, return lowest price
            prices = []
            for size, price in price_data.items():
                num = re.sub(r'[^\d]', '', str(price))
                if num:
                    prices.append(int(num))
            return min(prices) if prices else None
        else:
            # Single price string
            num = re.sub(r'[^\d]', '', str(price_data))
            return int(num) if num else None
    except Exception as e:
        logger.error(f"Error getting lowest price: {str(e)}")
        return None

def clean_text(text: str) -> str:
    """Clean text by removing extra spaces and special characters."""
    if not text:
        return ""
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text)
    # Remove leading/trailing spaces and punctuation
    text = text.strip(' ,.-')
    return text

def validate_url(url: str) -> bool:
    """Validate if URL is properly formatted."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False
    """Simple rate limiter to prevent spam."""
    
    def __init__(self):
        self.requests = defaultdict(list)
    
    def allow_request(self, user_id: int) -> bool:
        """Check if user is allowed to make a request."""
        now = time.time()
        user_requests = self.requests[user_id]
        
        # Remove old requests outside the window
        user_requests[:] = [req_time for req_time in user_requests if now - req_time < RATE_LIMIT_WINDOW]
        
        # Check if under limit
        if len(user_requests) < RATE_LIMIT_MAX_REQUESTS:
            user_requests.append(now)
            return True
        
        return False

def unshorten_url(url: str) -> str:
    """Expand shortened URLs to their original form."""
    try:
        # Check if it's already a full URL
        if not any(service in url for service in SHORTENED_URL_SERVICES):
            return url
        
        # Try to resolve the shortened URL
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.head(
                    url, 
                    allow_redirects=True, 
                    timeout=REQUEST_TIMEOUT,
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    }
                )
                if response.status_code < 400:
                    return response.url
            except Exception as e:
                logger.warning(f"URL expansion attempt {attempt + 1} failed: {str(e)}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(1)  # Wait before retry
                continue
        
        # If all retries failed, return original URL
        logger.warning(f"Failed to expand URL after {MAX_RETRIES} attempts: {url}")
        return url
    except Exception as e:
        logger.error(f"Error expanding URL {url}: {str(e)}")
        return url

def clean_link(url: str) -> str:
    """Remove affiliate tags and UTM parameters from URL."""
    try:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Parameters to remove (affiliate and tracking)
        params_to_remove = {
            'ref', 'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'aff', 'mc', 'sr', 'icid', 'clickid', 'offer_id', 'aff_id', 'affid',
            'tag', 'linkCode', 'creative', 'creativeASIN', 'ascsubtag', 'gclid',
            'fbclid', 'msclkid', '_branch_match_id'
        }
        
        # Remove affiliate and tracking parameters
        clean_params = {
            k: v for k, v in query_params.items() 
            if not any(param in k.lower() for param in params_to_remove)
        }
        
        # Reconstruct clean URL
        clean_query = urlencode(clean_params, doseq=True)
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if clean_query:
            clean_url += f"?{clean_query}"
        
        return clean_url
    except Exception as e:
        logger.error(f"Error cleaning link {url}: {str(e)}")
        return url

def detect_platform(url: str) -> Optional[str]:
    """Detect which e-commerce platform the URL belongs to."""
    try:
        domain = urlparse(url).netloc.lower()
        
        for platform, domains in SUPPORTED_DOMAINS.items():
            if any(d in domain for d in domains):
                return platform
        
        return None
    except Exception as e:
        logger.error(f"Error detecting platform for {url}: {str(e)}")
        return None

def extract_links(text: str) -> List[str]:
    """Extract all URLs from text or caption."""
    if not text:
        return []
    
    # Regex to match URLs (http, https, www)
    url_patterns = [
        r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*(?:\?[\w=&%-]*)?(?:#[\w-]*)?',
        r'www\.(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\.-]*(?:\?[\w=&%-]*)?(?:#[\w-]*)?'
    ]
    
    links = []
    for pattern in url_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if not match.startswith(('http://', 'https://')):
                match = 'https://' + match
            links.append(match)
    
    return list(set(links))  # Remove duplicates

def format_title(product_data: dict) -> str:
    """Format title according to ReviewCheckk Bot Master Rulebook."""
    try:
        # Extract relevant data
        brand = product_data.get('brand', '').strip()
        title = product_data.get('title', '').strip()
        price = product_data.get('price', '')
        category = product_data.get('category', '').lower()
        gender = product_data.get('gender', '').strip()
        quantity = product_data.get('quantity', '').strip()
        
        # Handle missing brand
        if not brand:
            # Try to extract brand from title
            for b in BRANDS:
                if b.lower() in title.lower():
                    brand = b
                    break
        
        # Clean title by removing brand, price, and fluff
        clean_title = title
        if brand:
            clean_title = re.sub(re.escape(brand), '', clean_title, flags=re.IGNORECASE)
        
        # Remove price mentions
        clean_title = re.sub(r'[\d,]+(?:\.\d+)?\s*(?:rs|₹|inr)', '', clean_title, flags=re.IGNORECASE)
        
        # Remove marketing fluff
        fluff_words = [
            'best offer', 'limited time', 'special offer', 'deal of the day', 
            'exclusive', 'only', 'just', 'hurry', 'sale', 'discount', 'offer',
            'combo', 'set of', 'pack of', 'bundle', 'free', 'gift', 'new',
            'latest', 'trending', 'hot', 'popular', 'fashion', 'stylish',
            'premium', 'luxury', 'branded', 'original', 'authentic'
        ]
        for word in fluff_words:
            clean_title = re.sub(r'\b' + re.escape(word) + r'\b', '', clean_title, flags=re.IGNORECASE)
        
        # Remove duplicate words
        words = clean_title.split()
        seen = set()
        unique_words = []
        for word in words:
            if word.lower() not in seen:
                seen.add(word.lower())
                unique_words.append(word)
        clean_title = ' '.join(unique_words)
        
        # Trim extra spaces and punctuation
        clean_title = re.sub(r'\s+', ' ', clean_title).strip(' ,.-')
        
        # Format based on category
        if any(cat in category for cat in ['clothing', 'apparel', 'footwear', 'fashion']):
            # Clothing format: [Brand] [Gender] [Quantity] [Product Name]
            parts = []
            if brand:
                parts.append(brand)
            if gender:
                parts.append(gender)
            if quantity:
                parts.append(quantity)
            parts.append(clean_title)
            formatted = ' '.join(parts)
        else:
            # Non-clothing format: [Brand] [Product Title]
            parts = []
            if brand:
                parts.append(brand)
            parts.append(clean_title)
            formatted = ' '.join(parts)
        
        # Add price if available
        if price and price != "Price unavailable":
            formatted += f" from @{format_price_number(price)} rs"
        
        # Ensure title is 5-8 words max
        words = formatted.split()
        if len(words) > 8:
            formatted = ' '.join(words[:8])
        
        return formatted.strip()
    except Exception as e:
        logger.error(f"Error formatting title: {str(e)}")
        # Fallback to clean extracted title
        return product_data.get('title', '').strip()

def format_price_number(price_str: str) -> str:
    """Extract and format price number."""
    if not price_str or price_str == "Price unavailable":
        return "Price unavailable"
    
    # Extract numeric value
    numeric_price = re.sub(r'[^\d]', '', str(price_str))
    if not numeric_price:
        return "Price unavailable"
    
    return numeric_price

def get_lowest_price(price_data) -> Optional[int]:
    """Get lowest price from price data (for multiple sizes/options)."""
    try:
        if isinstance(price_data, list):
            # If price_data is a list of prices, return the lowest
            prices = []
            for p in price_data:
                num = re.sub(r'[^\d]', '', str(p))
                if num:
                    prices.append(int(num))
            return min(prices) if prices else None
        elif isinstance(price_data, dict):
            # If price_data is a dict of size:price, return lowest price
            prices = []
            for size, price in price_data.items():
                num = re.sub(r'[^\d]', '', str(price))
                if num:
                    prices.append(int(num))
            return min(prices) if prices else None
        else:
            # Single price string
            num = re.sub(r'[^\d]', '', str(price_data))
            return int(num) if num else None
    except Exception as e:
        logger.error(f"Error getting lowest price: {str(e)}")
        return None

def clean_text(text: str) -> str:
    """Clean text by removing extra spaces and special characters."""
    if not text:
        return ""
    # Remove extra spaces
    text = re.sub(r'\s+', ' ', text)
    # Remove leading/trailing spaces and punctuation
    text = text.strip(' ,.-')
    return text

def validate_url(url: str) -> bool:
    """Validate if URL is properly formatted."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False
