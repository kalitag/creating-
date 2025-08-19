import requests
import logging
from urllib.parse import urlparse, parse_qs, urlencode, unquote
from typing import Optional, Dict, List
import time
import re
from config import REQUEST_TIMEOUT, MAX_RETRIES

logger = logging.getLogger(__name__)

class AdvancedURLResolver:
    """Advanced URL resolver that handles complex redirect chains and affiliate links."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Common redirect services and their patterns
        self.redirect_services = {
            'bitli.in': self._resolve_bitli,
            'bit.ly': self._resolve_generic,
            'tinyurl.com': self._resolve_generic,
            'amzn.to': self._resolve_amazon_short,
            'fkrt.it': self._resolve_flipkart_short,
            'wishlink.com': self._resolve_wishlink,
            'linkredirect.in': self._resolve_generic,
            'short.link': self._resolve_generic,
            'cutt.ly': self._resolve_generic,
            'rb.gy': self._resolve_generic,
            'tiny.cc': self._resolve_generic,
        }
        
        # Platform-specific URL patterns
        self.platform_patterns = {
            'amazon': {
                'domains': ['amazon.in', 'amazon.com', 'amzn.to'],
                'product_patterns': [
                    r'/dp/([A-Z0-9]{10})',
                    r'/gp/product/([A-Z0-9]{10})',
                    r'/product/([A-Z0-9]{10})',
                    r'asin=([A-Z0-9]{10})',
                ]
            },
            'flipkart': {
                'domains': ['flipkart.com', 'fkrt.it'],
                'product_patterns': [
                    r'/p/([a-zA-Z0-9-]+)',
                    r'pid=([A-Z0-9]+)',
                ]
            },
            'myntra': {
                'domains': ['myntra.com'],
                'product_patterns': [
                    r'/(\d+)/buy',
                    r'/product/(\d+)',
                ]
            },
            'meesho': {
                'domains': ['meesho.com'],
                'product_patterns': [
                    r'/product/([a-zA-Z0-9-]+)',
                    r'/s/p/([a-zA-Z0-9]+)',
                ]
            },
            'ajio': {
                'domains': ['ajio.com'],
                'product_patterns': [
                    r'/p/(\d+)',
                    r'/product/(\d+)',
                ]
            },
            'snapdeal': {
                'domains': ['snapdeal.com'],
                'product_patterns': [
                    r'/product/([a-zA-Z0-9-]+)',
                ]
            }
        }

    def resolve_url(self, url: str) -> Dict[str, str]:
        """
        Resolve URL through all redirects and extract final destination.
        Returns dict with original_url, final_url, platform, and product_id.
        """
        result = {
            'original_url': url,
            'final_url': url,
            'platform': None,
            'product_id': None,
            'error': None
        }
        
        try:
            # Step 1: Clean and validate URL
            clean_url = self._clean_url(url)
            if not self._validate_url(clean_url):
                result['error'] = 'Invalid URL format'
                return result
            
            # Step 2: Resolve through redirect chain
            final_url = self._resolve_redirects(clean_url)
            result['final_url'] = final_url
            
            # Step 3: Detect platform and extract product ID
            platform = self._detect_platform(final_url)
            result['platform'] = platform
            
            if platform:
                product_id = self._extract_product_id(final_url, platform)
                result['product_id'] = product_id
            
            logger.info(f"URL resolved: {url} -> {final_url} (Platform: {platform})")
            return result
            
        except Exception as e:
            logger.error(f"Error resolving URL {url}: {str(e)}")
            result['error'] = str(e)
            return result

    def _clean_url(self, url: str) -> str:
        """Clean URL by removing tracking parameters and normalizing format."""
        try:
            # Add protocol if missing
            if not url.startswith(('http://', 'https://')):
                if url.startswith('www.'):
                    url = 'https://' + url
                else:
                    url = 'https://' + url
            
            # Parse URL
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            
            # Remove tracking parameters
            tracking_params = {
                'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
                'fbclid', 'gclid', 'msclkid', 'ref', 'tag', 'linkCode', 'creative',
                'creativeASIN', 'ascsubtag', 'mc', 'sr', 'icid', 'clickid',
                'offer_id', 'aff_id', 'affid', '_branch_match_id'
            }
            
            clean_params = {
                k: v for k, v in query_params.items()
                if k not in tracking_params
            }
            
            # Reconstruct URL
            clean_query = urlencode(clean_params, doseq=True)
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if clean_query:
                clean_url += f"?{clean_query}"
            
            return clean_url
            
        except Exception as e:
            logger.error(f"Error cleaning URL {url}: {str(e)}")
            return url

    def _resolve_redirects(self, url: str) -> str:
        """Resolve URL through all redirect chains."""
        current_url = url
        redirect_count = 0
        max_redirects = 10
        
        while redirect_count < max_redirects:
            try:
                # Check if this is a known redirect service
                domain = urlparse(current_url).netloc.lower()
                
                # Use specific resolver if available
                for service, resolver in self.redirect_services.items():
                    if service in domain:
                        resolved = resolver(current_url)
                        if resolved and resolved != current_url:
                            current_url = resolved
                            redirect_count += 1
                            continue
                
                # Generic redirect resolution
                response = self.session.head(
                    current_url,
                    allow_redirects=False,
                    timeout=REQUEST_TIMEOUT
                )
                
                if response.status_code in [301, 302, 303, 307, 308]:
                    location = response.headers.get('Location')
                    if location:
                        # Handle relative redirects
                        if location.startswith('/'):
                            parsed = urlparse(current_url)
                            location = f"{parsed.scheme}://{parsed.netloc}{location}"
                        elif not location.startswith(('http://', 'https://')):
                            location = 'https://' + location
                        
                        current_url = location
                        redirect_count += 1
                        continue
                
                # No more redirects
                break
                
            except Exception as e:
                logger.warning(f"Error resolving redirect for {current_url}: {str(e)}")
                break
        
        return current_url

    def _resolve_bitli(self, url: str) -> Optional[str]:
        """Resolve bitli.in URLs by extracting the encoded destination."""
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            if response.status_code == 200:
                # Look for redirect in HTML
                content = response.text
                
                # Check for meta refresh
                meta_match = re.search(r'<meta[^>]*http-equiv=["\']refresh["\'][^>]*content=["\'][^;]*;\s*url=([^"\']+)', content, re.IGNORECASE)
                if meta_match:
                    return meta_match.group(1)
                
                # Check for JavaScript redirect
                js_match = re.search(r'window\.location\.href\s*=\s*["\']([^"\']+)["\']', content)
                if js_match:
                    return js_match.group(1)
                
                # Check for form action (some redirectors use forms)
                form_match = re.search(r'<form[^>]*action=["\']([^"\']+)["\']', content, re.IGNORECASE)
                if form_match:
                    return form_match.group(1)
            
            return None
            
        except Exception as e:
            logger.error(f"Error resolving bitli URL {url}: {str(e)}")
            return None

    def _resolve_amazon_short(self, url: str) -> Optional[str]:
        """Resolve Amazon short URLs (amzn.to)."""
        try:
            response = self.session.head(url, allow_redirects=True, timeout=REQUEST_TIMEOUT)
            return response.url if response.status_code < 400 else None
        except Exception as e:
            logger.error(f"Error resolving Amazon short URL {url}: {str(e)}")
            return None

    def _resolve_flipkart_short(self, url: str) -> Optional[str]:
        """Resolve Flipkart short URLs (fkrt.it)."""
        try:
            response = self.session.head(url, allow_redirects=True, timeout=REQUEST_TIMEOUT)
            return response.url if response.status_code < 400 else None
        except Exception as e:
            logger.error(f"Error resolving Flipkart short URL {url}: {str(e)}")
            return None

    def _resolve_wishlink(self, url: str) -> Optional[str]:
        """Resolve Wishlink URLs by extracting the target URL."""
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            if response.status_code == 200:
                # Wishlink usually redirects via JavaScript or meta refresh
                content = response.text
                
                # Look for the actual product URL in the page
                patterns = [
                    r'var\s+redirectUrl\s*=\s*["\']([^"\']+)["\']',
                    r'window\.location\.href\s*=\s*["\']([^"\']+)["\']',
                    r'<meta[^>]*http-equiv=["\']refresh["\'][^>]*url=([^"\']+)',
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        return unquote(match.group(1))
            
            return None
            
        except Exception as e:
            logger.error(f"Error resolving Wishlink URL {url}: {str(e)}")
            return None

    def _resolve_generic(self, url: str) -> Optional[str]:
        """Generic redirect resolver for most URL shorteners."""
        try:
            response = self.session.head(url, allow_redirects=True, timeout=REQUEST_TIMEOUT)
            return response.url if response.status_code < 400 else None
        except Exception as e:
            logger.error(f"Error resolving generic short URL {url}: {str(e)}")
            return None

    def _detect_platform(self, url: str) -> Optional[str]:
        """Detect e-commerce platform from URL."""
        try:
            domain = urlparse(url).netloc.lower()
            
            for platform, config in self.platform_patterns.items():
                if any(d in domain for d in config['domains']):
                    return platform
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting platform for {url}: {str(e)}")
            return None

    def _extract_product_id(self, url: str, platform: str) -> Optional[str]:
        """Extract product ID from URL based on platform."""
        try:
            if platform not in self.platform_patterns:
                return None
            
            patterns = self.platform_patterns[platform]['product_patterns']
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting product ID from {url}: {str(e)}")
            return None

    def _validate_url(self, url: str) -> bool:
        """Validate URL format."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

# Global resolver instance
url_resolver = AdvancedURLResolver()
