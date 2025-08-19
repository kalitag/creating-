# ReviewCheckk Bot - Web Scraping Module
import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional, List
import json
import re
from config import REQUEST_TIMEOUT, MAX_RETRIES
from utils import clean_text, get_lowest_price

logger = logging.getLogger(__name__)

def scrape_product(url: str, platform: str, advanced_mode: bool = False) -> Optional[Dict]:
    """Scrape product data from supported platforms."""
    try:
        # Get page content with better headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        response = None
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, allow_redirects=True)
                if response.status_code == 200:
                    break
                elif response.status_code == 403:
                    # Try with different user agent
                    headers['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15'
                    continue
            except Exception as e:
                logger.warning(f"Scraping attempt {attempt + 1} failed: {str(e)}")
                if attempt < MAX_RETRIES - 1:
                    continue
                return None
        
        if not response or response.status_code != 200:
            logger.error(f"Failed to fetch page: {response.status_code if response else 'No response'}")
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
        
        title_selectors = [
            '#productTitle',
            'span#productTitle',
            'h1.a-size-large.a-spacing-none.a-color-base',
            'h1 span',
            '.product-title',
            '[data-automation-id="product-title"]'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                product_data['title'] = clean_text(title_elem.get_text())
                break
        
        price_selectors = [
            '.a-price.a-text-price.a-size-medium.a-color-base .a-offscreen',
            '.a-price-whole',
            '.a-price .a-offscreen',
            'span.a-price-symbol + span.a-price-whole',
            '.a-price-range .a-offscreen',
            '#priceblock_dealprice',
            '#priceblock_ourprice',
            '.a-price.a-text-price .a-offscreen'
        ]
        
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                price_text = clean_text(price_elem.get_text())
                if price_text and any(char.isdigit() for char in price_text):
                    product_data['price'] = price_text
                    break
        
        brand_selectors = [
            '#bylineInfo',
            'a#bylineInfo',
            '.a-link-normal[data-attribute="brand"]',
            '.po-brand .po-break-word',
            'tr.a-spacing-small td.a-span9 span',
            '#feature-bullets ul li span span'
        ]
        
        for selector in brand_selectors:
            brand_elem = soup.select_one(selector)
            if brand_elem:
                brand_text = clean_text(brand_elem.get_text())
                if brand_text and not brand_text.lower().startswith('visit'):
                    product_data['brand'] = brand_text
                    break
        
        image_selectors = [
            '#landingImage',
            '.a-dynamic-image',
            '#imgTagWrapperId img',
            '.a-spacing-small img',
            'img[data-old-hires]'
        ]
        
        images = []
        for selector in image_selectors:
            img_elems = soup.select(selector)
            for img in img_elems:
                src = img.get('data-old-hires') or img.get('src') or img.get('data-src')
                if src and src.startswith('http') and 'amazon' in src:
                    images.append(src)
        
        product_data['images'] = list(set(images))[:3]
        
        availability_selectors = [
            '#availability span',
            '.a-color-state',
            '.a-color-price',
            '#outOfStock',
            '.a-alert-content'
        ]
        
        for selector in availability_selectors:
            avail_elem = soup.select_one(selector)
            if avail_elem:
                avail_text = avail_elem.get_text().lower()
                if any(phrase in avail_text for phrase in ['out of stock', 'unavailable', 'not available', 'currently unavailable']):
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
        
        title_selectors = [
            'span.B_NuCI',
            'h1 span.B_NuCI',
            'h1._35KyD6',
            '.B_NuCI',
            'span._35KyD6',
            'h1 span'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                product_data['title'] = clean_text(title_elem.get_text())
                break
        
        price_selectors = [
            '._30jeq3._16Jk6d',
            '._1_WHN1',
            '._3I9_wc._2p6lqe',
            'div._25b18c div',
            '._30jeq3',
            'div._16Jk6d'
        ]
        
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                price_text = clean_text(price_elem.get_text())
                if price_text and any(char.isdigit() for char in price_text):
                    product_data['price'] = price_text
                    break
        
        image_selectors = [
            '._396cs4 img',
            '._2r_T1I img',
            '.CXW8mj img',
            '._2KpZ6l._396cs4 img',
            'img._396cs4'
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
        
        title_selectors = [
            'h1',
            '.ProductDetail__productName',
            '[data-testid="product-title"]',
            'h1[data-testid="product-title"]',
            '.sc-bcXHqe'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                product_data['title'] = clean_text(title_elem.get_text())
                break
        
        price_selectors = [
            '.ProductDetail__price',
            '[data-testid="product-price"]',
            '.price',
            'h4',
            '.sc-htpNat'
        ]
        
        for selector in price_selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                price_text = clean_text(price_elem.get_text())
                if price_text and any(char.isdigit() for char in price_text):
                    product_data['price'] = price_text
                    break
        
        # Sizes (Meesho specific)
        size_selectors = [
            '.ProductDetail__sizeOption',
            '[data-testid="size-option"]',
            '.size-option',
            'button[data-testid*="size"]'
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
