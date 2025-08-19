# ReviewCheckk Bot - Advanced Web Scraping Module
import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional, List, Union
import json
import re
import time
from urllib.parse import urljoin, urlparse
from config import REQUEST_TIMEOUT, MAX_RETRIES
from utils import clean_text, get_lowest_price
from url_resolver import url_resolver

logger = logging.getLogger(__name__)

class ModernScraper:
    """Advanced web scraper with modern techniques and fallback strategies."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
            'DNT': '1'
        })
        
        # Updated selectors for 2024/2025
        self.platform_selectors = {
            'amazon': {
                'title': [
                    '#productTitle',
                    'span#productTitle',
                    'h1.a-size-large.a-spacing-none.a-color-base',
                    'h1 span[data-automation-id="product-title"]',
                    '.product-title h1',
                    '[data-testid="product-title"]',
                    'h1.a-size-large'
                ],
                'price': [
                    '.a-price.a-text-price.a-size-medium.a-color-base .a-offscreen',
                    '.a-price-whole',
                    '.a-price .a-offscreen',
                    'span.a-price-symbol + span.a-price-whole',
                    '.a-price-range .a-offscreen',
                    '#apex_desktop .a-price .a-offscreen',
                    '.a-price.a-text-price .a-offscreen',
                    '[data-testid="price"] .a-offscreen',
                    '.a-price.a-text-normal .a-offscreen'
                ],
                'brand': [
                    '#bylineInfo',
                    'a#bylineInfo',
                    '.a-link-normal[data-attribute="brand"]',
                    '.po-brand .po-break-word',
                    'tr.a-spacing-small td.a-span9 span',
                    '[data-testid="brand-name"]',
                    '.a-row .a-text-bold:contains("Brand")+span'
                ],
                'images': [
                    '#landingImage',
                    '.a-dynamic-image',
                    '#imgTagWrapperId img',
                    'img[data-old-hires]',
                    '.a-spacing-small img[src*="amazon"]'
                ],
                'availability': [
                    '#availability span',
                    '.a-color-state',
                    '.a-color-price',
                    '#outOfStock',
                    '.a-alert-content',
                    '[data-testid="availability"]'
                ]
            },
            'flipkart': {
                'title': [
                    'span.VU-ZEz',
                    'span.B_NuCI', 
                    'h1 span.VU-ZEz',
                    'h1._35KyD6',
                    '.B_NuCI',
                    'span._35KyD6',
                    'h1 span',
                    '[data-testid="product-title"]'
                ],
                'price': [
                    'div.Nx9bqj.CxhGGd',
                    '._30jeq3._16Jk6d',
                    '._1_WHN1',
                    '._3I9_wc._2p6lqe',
                    'div._25b18c div',
                    '._30jeq3',
                    'div._16Jk6d',
                    '[data-testid="selling-price"]'
                ],
                'brand': [
                    '.G6XhBx',
                    '.aMaAEs',
                    'span.G6XhBx',
                    '[data-testid="brand-name"]'
                ],
                'images': [
                    '._396cs4 img',
                    '._2r_T1I img', 
                    '.CXW8mj img',
                    '._2KpZ6l._396cs4 img',
                    'img._396cs4',
                    '[data-testid="product-image"] img'
                ]
            },
            'meesho': {
                'title': [
                    'h1[data-testid="product-title"]',
                    'h1.sc-eDvSVe',
                    '.ProductDetail__productName',
                    'h1',
                    '.sc-bcXHqe',
                    '[data-testid="pdp-product-name"]'
                ],
                'price': [
                    'h4[data-testid="product-price"]',
                    '.ProductDetail__price',
                    'h4.sc-htpNat',
                    '.price',
                    'h4',
                    '[data-testid="selling-price"]'
                ],
                'brand': [
                    '[data-testid="brand-name"]',
                    '.brand-name',
                    '.ProductDetail__brand'
                ],
                'images': [
                    '[data-testid="product-image"] img',
                    '.ProductDetail__image img',
                    '.product-image img'
                ]
            },
            'myntra': {
                'title': [
                    'h1.pdp-name',
                    '.pdp-product-name',
                    'h1[data-testid="product-name"]',
                    '.product-name',
                    '.pdp-name'
                ],
                'price': [
                    '.pdp-price strong',
                    '.product-discountedPrice',
                    '.pdp-price',
                    '[data-testid="price"] strong',
                    '.price-current'
                ],
                'brand': [
                    '.pdp-title',
                    '[data-testid="brand-name"]',
                    '.brand-name'
                ],
                'images': [
                    '.image-grid-image',
                    '.product-image img',
                    '[data-testid="product-image"] img'
                ]
            },
            'ajio': {
                'title': [
                    '.prod-name',
                    'h1.product-title',
                    '.product-name',
                    '[data-testid="product-title"]'
                ],
                'price': [
                    '.prod-sp',
                    '.product-price',
                    '.price-current',
                    '[data-testid="selling-price"]'
                ],
                'brand': [
                    '.prod-brand',
                    '[data-testid="brand-name"]',
                    '.brand-name'
                ],
                'images': [
                    '.prod-image img',
                    '.product-image img'
                ]
            },
            'snapdeal': {
                'title': [
                    'h1[itemprop="name"]',
                    '.pdp-product-name',
                    '.product-title',
                    '[data-testid="product-title"]'
                ],
                'price': [
                    '.payBlkBig',
                    '.product-price',
                    '.price-current',
                    '[data-testid="selling-price"]'
                ],
                'brand': [
                    '.brand-name',
                    '[data-testid="brand-name"]'
                ],
                'images': [
                    '.product-image img',
                    '.pdp-image img'
                ]
            },
            'wishlink': {
                'title': [
                    '.product-title',
                    'h1.title',
                    '.product-name'
                ],
                'price': [
                    '.product-price',
                    '.price-current',
                    '.price'
                ]
            }
        }

    def scrape_product(self, url: str, platform: str = None, advanced_mode: bool = False) -> Optional[Dict]:
        """Main scraping method with intelligent platform detection and fallback strategies."""
        try:
            # Step 1: Resolve URL and detect platform
            if not platform:
                url_info = url_resolver.resolve_url(url)
                if url_info['error']:
                    logger.error(f"URL resolution failed: {url_info['error']}")
                    return None
                
                url = url_info['final_url']
                platform = url_info['platform']
            
            if not platform:
                logger.error(f"Could not detect platform for URL: {url}")
                return None
            
            logger.info(f"Scraping {platform} product: {url}")
            
            # Step 2: Get page content with retry logic
            soup = self._get_page_content(url)
            if not soup:
                return None
            
            # Step 3: Extract product data
            product_data = self._extract_product_data(soup, url, platform, advanced_mode)
            
            # Step 4: Validate and enhance data
            if product_data and self._validate_product_data(product_data):
                product_data = self._enhance_product_data(product_data, soup, platform)
                logger.info(f"Successfully scraped product: {product_data.get('title', 'Unknown')}")
                return product_data
            else:
                logger.warning(f"Failed to extract valid product data from {url}")
                return None
                
        except Exception as e:
            logger.error(f"Error scraping product {url}: {str(e)}")
            return None

    def _get_page_content(self, url: str) -> Optional[BeautifulSoup]:
        """Get page content with multiple retry strategies."""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0'
        ]
        
        for attempt in range(MAX_RETRIES):
            try:
                # Rotate user agents
                self.session.headers['User-Agent'] = user_agents[attempt % len(user_agents)]
                
                # Add random delay to avoid rate limiting
                if attempt > 0:
                    time.sleep(1 + attempt)
                
                response = self.session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
                
                if response.status_code == 200:
                    return BeautifulSoup(response.content, 'html.parser')
                elif response.status_code == 403:
                    logger.warning(f"Access forbidden (403) for {url}, trying different approach")
                    continue
                elif response.status_code == 429:
                    logger.warning(f"Rate limited (429) for {url}, waiting longer")
                    time.sleep(5)
                    continue
                else:
                    logger.warning(f"HTTP {response.status_code} for {url}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on attempt {attempt + 1} for {url}")
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed on attempt {attempt + 1}: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {str(e)}")
        
        logger.error(f"Failed to fetch page after {MAX_RETRIES} attempts: {url}")
        return None

    def _extract_product_data(self, soup: BeautifulSoup, url: str, platform: str, advanced_mode: bool) -> Optional[Dict]:
        """Extract product data using platform-specific selectors with fallbacks."""
        product_data = {
            'platform': platform,
            'url': url,
            'out_of_stock': False,
            'extraction_method': 'css_selectors'
        }
        
        # Get platform selectors
        selectors = self.platform_selectors.get(platform, {})
        
        # Extract title
        product_data['title'] = self._extract_with_fallback(soup, selectors.get('title', []), 'title')
        
        # Extract price
        product_data['price'] = self._extract_price(soup, selectors.get('price', []))
        
        # Extract brand
        product_data['brand'] = self._extract_with_fallback(soup, selectors.get('brand', []), 'brand')
        
        # Extract images
        product_data['images'] = self._extract_images(soup, selectors.get('images', []), url)
        
        # Check availability
        product_data['out_of_stock'] = self._check_availability(soup, selectors.get('availability', []))
        
        # Try JSON-LD extraction as fallback
        if not product_data.get('title') or not product_data.get('price'):
            json_data = self._extract_json_ld(soup)
            if json_data:
                product_data.update(json_data)
                product_data['extraction_method'] = 'json_ld'
        
        # Try microdata extraction as another fallback
        if not product_data.get('title') or not product_data.get('price'):
            microdata = self._extract_microdata(soup)
            if microdata:
                product_data.update(microdata)
                product_data['extraction_method'] = 'microdata'
        
        return product_data

    def _extract_with_fallback(self, soup: BeautifulSoup, selectors: List[str], field_type: str) -> Optional[str]:
        """Extract text using multiple selectors as fallbacks."""
        for selector in selectors:
            try:
                if ':contains(' in selector:
                    # Handle pseudo-selectors
                    continue
                
                element = soup.select_one(selector)
                if element:
                    text = clean_text(element.get_text())
                    if text and len(text.strip()) > 0:
                        # Additional validation based on field type
                        if field_type == 'title' and len(text) > 10:
                            return text
                        elif field_type == 'brand' and len(text) < 50:
                            return text
                        elif field_type not in ['title', 'brand']:
                            return text
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {str(e)}")
                continue
        
        return None

    def _extract_price(self, soup: BeautifulSoup, selectors: List[str]) -> Optional[str]:
        """Extract price with special handling for currency and formatting."""
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    price_text = clean_text(element.get_text())
                    if price_text and any(char.isdigit() for char in price_text):
                        # Clean and validate price
                        price_match = re.search(r'[\d,]+(?:\.\d+)?', price_text)
                        if price_match:
                            return price_text
            except Exception as e:
                logger.debug(f"Price selector {selector} failed: {str(e)}")
                continue
        
        return None

    def _extract_images(self, soup: BeautifulSoup, selectors: List[str], base_url: str) -> List[str]:
        """Extract product images with URL validation."""
        images = []
        
        for selector in selectors:
            try:
                img_elements = soup.select(selector)
                for img in img_elements:
                    # Try different src attributes
                    src = (img.get('data-old-hires') or 
                          img.get('data-src') or 
                          img.get('src') or 
                          img.get('data-lazy-src'))
                    
                    if src:
                        # Convert relative URLs to absolute
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif src.startswith('/'):
                            src = urljoin(base_url, src)
                        
                        # Validate image URL
                        if (src.startswith('http') and 
                            any(ext in src.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']) and
                            src not in images):
                            images.append(src)
                            
                        if len(images) >= 3:  # Limit to 3 images
                            break
                            
            except Exception as e:
                logger.debug(f"Image selector {selector} failed: {str(e)}")
                continue
        
        return images

    def _check_availability(self, soup: BeautifulSoup, selectors: List[str]) -> bool:
        """Check if product is out of stock."""
        out_of_stock_phrases = [
            'out of stock', 'unavailable', 'not available', 'currently unavailable',
            'sold out', 'temporarily unavailable', 'stock out', 'not in stock'
        ]
        
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element:
                    text = element.get_text().lower()
                    if any(phrase in text for phrase in out_of_stock_phrases):
                        return True
            except Exception as e:
                logger.debug(f"Availability selector {selector} failed: {str(e)}")
                continue
        
        return False

    def _extract_json_ld(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Extract product data from JSON-LD structured data."""
        try:
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, list):
                        data = data[0]
                    
                    if data.get('@type') == 'Product':
                        result = {}
                        if data.get('name'):
                            result['title'] = clean_text(data['name'])
                        if data.get('brand', {}).get('name'):
                            result['brand'] = clean_text(data['brand']['name'])
                        if data.get('offers', {}).get('price'):
                            result['price'] = str(data['offers']['price'])
                        if data.get('image'):
                            images = data['image'] if isinstance(data['image'], list) else [data['image']]
                            result['images'] = images[:3]
                        
                        return result
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            logger.debug(f"JSON-LD extraction failed: {str(e)}")
        
        return None

    def _extract_microdata(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Extract product data from microdata."""
        try:
            result = {}
            
            # Look for itemtype="http://schema.org/Product"
            product_elem = soup.find(attrs={'itemtype': re.compile(r'.*Product.*')})
            if product_elem:
                # Extract name
                name_elem = product_elem.find(attrs={'itemprop': 'name'})
                if name_elem:
                    result['title'] = clean_text(name_elem.get_text())
                
                # Extract brand
                brand_elem = product_elem.find(attrs={'itemprop': 'brand'})
                if brand_elem:
                    result['brand'] = clean_text(brand_elem.get_text())
                
                # Extract price
                price_elem = product_elem.find(attrs={'itemprop': 'price'})
                if price_elem:
                    result['price'] = clean_text(price_elem.get_text() or price_elem.get('content', ''))
                
                return result if result else None
                
        except Exception as e:
            logger.debug(f"Microdata extraction failed: {str(e)}")
        
        return None

    def _validate_product_data(self, product_data: Dict) -> bool:
        """Validate that extracted product data is meaningful."""
        if not product_data:
            return False
        
        # Must have title
        title = product_data.get('title', '').strip()
        if not title or len(title) < 5:
            return False
        
        # Should have price (unless it's a special case)
        price = product_data.get('price', '').strip()
        if not price:
            logger.warning("Product has no price information")
        
        return True

    def _enhance_product_data(self, product_data: Dict, soup: BeautifulSoup, platform: str) -> Dict:
        """Enhance product data with additional information."""
        try:
            # Extract category if possible
            category_selectors = [
                '[data-testid="breadcrumb"]',
                '.breadcrumb',
                '.nav-breadcrumb',
                '#wayfinding-breadcrumbs_feature_div'
            ]
            
            for selector in category_selectors:
                elem = soup.select_one(selector)
                if elem:
                    category_text = clean_text(elem.get_text())
                    if category_text:
                        product_data['category'] = category_text
                        break
            
            # Clean and format price
            if product_data.get('price'):
                price_text = product_data['price']
                # Extract numeric price
                price_match = re.search(r'[\d,]+(?:\.\d+)?', price_text.replace(',', ''))
                if price_match:
                    product_data['price_numeric'] = float(price_match.group().replace(',', ''))
            
            # Add timestamp
            product_data['scraped_at'] = time.time()
            
        except Exception as e:
            logger.debug(f"Enhancement failed: {str(e)}")
        
        return product_data

# Global scraper instance
modern_scraper = ModernScraper()

# Legacy function for backward compatibility
def scrape_product(url: str, platform: str = None, advanced_mode: bool = False) -> Optional[Dict]:
    """Legacy wrapper for the modern scraper."""
    return modern_scraper.scrape_product(url, platform, advanced_mode)

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
            'h1 span[data-automation-id="product-title"]',
            '.product-title h1',
            '[data-testid="product-title"]',
            'h1.a-size-large'
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
            '#apex_desktop .a-price .a-offscreen',
            '.a-price.a-text-price .a-offscreen',
            '[data-testid="price"] .a-offscreen',
            '.a-price.a-text-normal .a-offscreen'
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
            '[data-testid="brand-name"]',
            '.a-row .a-text-bold:contains("Brand")+span'
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
            'img[data-old-hires]',
            '.a-spacing-small img[src*="amazon"]'
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
            '.a-alert-content',
            '[data-testid="availability"]'
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
            'span.VU-ZEz',
            'span.B_NuCI', 
            'h1 span.VU-ZEz',
            'h1._35KyD6',
            '.B_NuCI',
            'span._35KyD6',
            'h1 span',
            '[data-testid="product-title"]'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                product_data['title'] = clean_text(title_elem.get_text())
                break
        
        price_selectors = [
            'div.Nx9bqj.CxhGGd',
            '._30jeq3._16Jk6d',
            '._1_WHN1',
            '._3I9_wc._2p6lqe',
            'div._25b18c div',
            '._30jeq3',
            'div._16Jk6d',
            '[data-testid="selling-price"]'
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
            'img._396cs4',
            '[data-testid="product-image"] img'
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
            'h1[data-testid="product-title"]',
            'h1.sc-eDvSVe',
            '.ProductDetail__productName',
            'h1',
            '.sc-bcXHqe',
            '[data-testid="pdp-product-name"]'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                product_data['title'] = clean_text(title_elem.get_text())
                break
        
        price_selectors = [
            'h4[data-testid="product-price"]',
            '.ProductDetail__price',
            'h4.sc-htpNat',
            '.price',
            'h4',
            '[data-testid="selling-price"]'
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
            'h1.pdp-name',
            '.pdp-product-name',
            'h1[data-testid="product-name"]',
            '.product-name',
            '.pdp-name'
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
            '.pdp-price',
            '[data-testid="price"] strong',
            '.price-current'
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
            '.product-name',
            '[data-testid="product-title"]'
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
            '.price-current',
            '[data-testid="selling-price"]'
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
            '.product-title',
            '[data-testid="product-title"]'
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
            '.price-current',
            '[data-testid="selling-price"]'
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
