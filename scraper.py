# ReviewCheckk Bot - Web Scraping Module
import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional, List
from config import REQUEST_TIMEOUT, MAX_RETRIES
from utils import clean_text, get_lowest_price

logger = logging.getLogger(__name__)

def scrape_product(url: str, platform: str, advanced_mode: bool = False) -> Optional[Dict]:
    """Scrape product data from supported platforms."""
    try:
        # Get page content
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
                if response.status_code == 200:
                    break
            except Exception as e:
                logger.warning(f"Scraping attempt {attempt + 1} failed: {str(e)}")
                if attempt < MAX_RETRIES - 1:
                    continue
                return None
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch page: {response.status_code}")
            return None
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Platform-specific scraping
        if platform == "amazon":
            return scrape_amazon(soup, url, advanced_mode)
        elif platform == "flipkart":
            return scrape_flipkart(soup, url, advanced_mode)
        elif platform == "meesho":
            return scrape_meesho(soup, url, advanced_mode)
        elif platform == "myntra":
            return scrape_myntra(soup, url, advanced_mode)
        elif platform == "ajio":
            return scrape_ajio(soup, url, advanced_mode)
        elif platform == "snapdeal":
            return scrape_snapdeal(soup, url, advanced_mode)
        elif platform == "wishlink":
            return scrape_wishlink(soup, url, advanced_mode)
        else:
            logger.error(f"Unsupported platform: {platform}")
            return None
            
    except Exception as e:
        logger.error(f"Error scraping {url}: {str(e)}")
        return None

def scrape_amazon(soup: BeautifulSoup, url: str, advanced_mode: bool) -> Optional[Dict]:
    """Scrape Amazon product data."""
    try:
        product_data = {
            'platform': 'amazon',
            'url': url,
            'out_of_stock': False
        }
        
        # Title
        title_selectors = [
            '#productTitle',
            '.product-title',
            'h1.a-size-large'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                product_data['title'] = clean_text(title_elem.get_text())
                break
        
        # Price
        price_selectors = [
            '.a-price-whole',
            '.a-offscreen',
            '.a-price .a-offscreen'
        ]
        
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                product_data['price'] = clean_text(price_elem.get_text())
                break
        
        # Brand
        brand_selectors = [
            '#bylineInfo',
            '.a-link-normal[data-attribute="brand"]',
            '.po-brand .po-break-word'
        ]
        
        for selector in brand_selectors:
            brand_elem = soup.select_one(selector)
            if brand_elem:
                product_data['brand'] = clean_text(brand_elem.get_text())
                break
        
        # Images
        image_selectors = [
            '#landingImage',
            '.a-dynamic-image',
            '#imgTagWrapperId img'
        ]
        
        images = []
        for selector in image_selectors:
            img_elems = soup.select(selector)
            for img in img_elems:
                src = img.get('src') or img.get('data-src')
                if src and src.startswith('http'):
                    images.append(src)
        
        product_data['images'] = list(set(images))[:3]  # Limit to 3 unique images
        
        # Check availability
        availability_selectors = [
            '#availability span',
            '.a-color-state',
            '.a-color-price'
        ]
        
        for selector in availability_selectors:
            avail_elem = soup.select_one(selector)
            if avail_elem:
                avail_text = avail_elem.get_text().lower()
                if any(phrase in avail_text for phrase in ['out of stock', 'unavailable', 'not available']):
                    product_data['out_of_stock'] = True
                break
        
        return product_data if product_data.get('title') else None
        
    except Exception as e:
        logger.error(f"Error scraping Amazon: {str(e)}")
        return None

def scrape_flipkart(soup: BeautifulSoup, url: str, advanced_mode: bool) -> Optional[Dict]:
    """Scrape Flipkart product data."""
    try:
        product_data = {
            'platform': 'flipkart',
            'url': url,
            'out_of_stock': False
        }
        
        # Title
        title_selectors = [
            '.B_NuCI',
            'h1 span',
            '._35KyD6'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                product_data['title'] = clean_text(title_elem.get_text())
                break
        
        # Price
        price_selectors = [
            '._30jeq3._16Jk6d',
            '._1_WHN1',
            '._3I9_wc._2p6lqe'
        ]
        
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                product_data['price'] = clean_text(price_elem.get_text())
                break
        
        # Images
        image_selectors = [
            '._396cs4 img',
            '._2r_T1I img',
            '.CXW8mj img'
        ]
        
        images = []
        for selector in image_selectors:
            img_elems = soup.select(selector)
            for img in img_elems:
                src = img.get('src') or img.get('data-src')
                if src and src.startswith('http'):
                    images.append(src)
        
        product_data['images'] = list(set(images))[:3]
        
        return product_data if product_data.get('title') else None
        
    except Exception as e:
        logger.error(f"Error scraping Flipkart: {str(e)}")
        return None

def scrape_meesho(soup: BeautifulSoup, url: str, advanced_mode: bool) -> Optional[Dict]:
    """Scrape Meesho product data."""
    try:
        product_data = {
            'platform': 'meesho',
            'url': url,
            'out_of_stock': False
        }
        
        # Title
        title_selectors = [
            'h1',
            '.ProductDetail__productName',
            '[data-testid="product-title"]'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                product_data['title'] = clean_text(title_elem.get_text())
                break
        
        # Price
        price_selectors = [
            '.ProductDetail__price',
            '[data-testid="product-price"]',
            '.price'
        ]
        
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                product_data['price'] = clean_text(price_elem.get_text())
                break
        
        # Sizes (Meesho specific)
        size_selectors = [
            '.ProductDetail__sizeOption',
            '[data-testid="size-option"]',
            '.size-option'
        ]
        
        sizes = []
        for selector in size_selectors:
            size_elems = soup.select(selector)
            for size_elem in size_elems:
                size_text = clean_text(size_elem.get_text())
                if size_text:
                    sizes.append(size_text)
        
        if sizes:
            product_data['sizes'] = sizes
        
        return product_data if product_data.get('title') else None
        
    except Exception as e:
        logger.error(f"Error scraping Meesho: {str(e)}")
        return None

def scrape_myntra(soup: BeautifulSoup, url: str, advanced_mode: bool) -> Optional[Dict]:
    """Scrape Myntra product data."""
    try:
        product_data = {
            'platform': 'myntra',
            'url': url,
            'out_of_stock': False
        }
        
        # Title
        title_selectors = [
            '.pdp-product-name',
            'h1.pdp-name',
            '.product-name'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                product_data['title'] = clean_text(title_elem.get_text())
                break
        
        # Price
        price_selectors = [
            '.pdp-price strong',
            '.product-discountedPrice',
            '.pdp-price'
        ]
        
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                product_data['price'] = clean_text(price_elem.get_text())
                break
        
        return product_data if product_data.get('title') else None
        
    except Exception as e:
        logger.error(f"Error scraping Myntra: {str(e)}")
        return None

def scrape_ajio(soup: BeautifulSoup, url: str, advanced_mode: bool) -> Optional[Dict]:
    """Scrape Ajio product data."""
    try:
        product_data = {
            'platform': 'ajio',
            'url': url,
            'out_of_stock': False
        }
        
        # Title
        title_selectors = [
            '.prod-name',
            'h1.product-title',
            '.product-name'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                product_data['title'] = clean_text(title_elem.get_text())
                break
        
        # Price
        price_selectors = [
            '.prod-sp',
            '.product-price',
            '.price-current'
        ]
        
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                product_data['price'] = clean_text(price_elem.get_text())
                break
        
        return product_data if product_data.get('title') else None
        
    except Exception as e:
        logger.error(f"Error scraping Ajio: {str(e)}")
        return None

def scrape_snapdeal(soup: BeautifulSoup, url: str, advanced_mode: bool) -> Optional[Dict]:
    """Scrape Snapdeal product data."""
    try:
        product_data = {
            'platform': 'snapdeal',
            'url': url,
            'out_of_stock': False
        }
        
        # Title
        title_selectors = [
            'h1[itemprop="name"]',
            '.pdp-product-name',
            '.product-title'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                product_data['title'] = clean_text(title_elem.get_text())
                break
        
        # Price
        price_selectors = [
            '.payBlkBig',
            '.product-price',
            '.price-current'
        ]
        
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                product_data['price'] = clean_text(price_elem.get_text())
                break
        
        return product_data if product_data.get('title') else None
        
    except Exception as e:
        logger.error(f"Error scraping Snapdeal: {str(e)}")
        return None

def scrape_wishlink(soup: BeautifulSoup, url: str, advanced_mode: bool) -> Optional[Dict]:
    """Scrape Wishlink product data."""
    try:
        product_data = {
            'platform': 'wishlink',
            'url': url,
            'out_of_stock': False
        }
        
        # Title
        title_selectors = [
            '.product-title',
            'h1.title',
            '.product-name'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                product_data['title'] = clean_text(title_elem.get_text())
                break
        
        # Price
        price_selectors = [
            '.product-price',
            '.price-current',
            '.price'
        ]
        
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                product_data['price'] = clean_text(price_elem.get_text())
                break
        
        return product_data if product_data.get('title') else None
        
    except Exception as e:
        logger.error(f"Error scraping Wishlink: {str(e)}")
        return None
