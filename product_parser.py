import re
import logging
from typing import Dict, Optional, List, Tuple
from config import BRANDS
from utils import clean_text, format_price_number
from debug_framework import debug_tracker, DebugLevel

logger = logging.getLogger(__name__)

class SmartProductParser:
    """Intelligent product parser that formats data according to ReviewCheckk style."""
    
    def __init__(self):
        # Extended brand list with common variations
        self.brands = set([brand.lower() for brand in BRANDS] + [
            # Fashion brands
            'tokyo talkies', 'bombay shaving', 'vi-john', 'biotique', 'handaiyan',
            'roadster', 'hrx', 'here&now', 'dressberry', 'all about you',
            'mast & harbour', 'anouk', 'sangria', 'libas', 'vishudh',
            # Beauty brands
            'lakme', 'maybelline', 'loreal', 'revlon', 'colorbar', 'nykaa',
            'sugar', 'faces', 'chambor', 'blue heaven', 'insight',
            # Home brands
            'home centre', 'urban ladder', 'pepperfry', 'fabindia', 'westside',
            # Electronics
            'boat', 'noise', 'realme', 'redmi', 'oneplus', 'samsung', 'apple'
        ])
        
        # Category keywords for better classification
        self.category_keywords = {
            'clothing': ['dress', 'shirt', 'top', 'kurta', 'kurti', 'saree', 'lehenga', 'jeans', 'trouser', 'pant'],
            'footwear': ['shoes', 'sandal', 'slipper', 'boot', 'sneaker', 'heel', 'flat', 'chappal'],
            'beauty': ['lipstick', 'foundation', 'mascara', 'eyeliner', 'compact', 'scrub', 'cream', 'serum'],
            'accessories': ['watch', 'bag', 'wallet', 'belt', 'sunglasses', 'jewelry', 'earring', 'necklace'],
            'home': ['jar', 'bottle', 'container', 'organizer', 'storage', 'decor', 'cushion', 'curtain'],
            'electronics': ['phone', 'earphone', 'charger', 'speaker', 'headphone', 'cable', 'adapter']
        }
        
        # Size patterns
        self.size_patterns = [
            r'\b(XS|S|M|L|XL|XXL|XXXL)\b',
            r'\b(\d+(?:\.\d+)?)\s*(?:inch|inches|cm|mm)\b',
            r'\b(Free Size|One Size|OS)\b',
            r'\b(\d+)\s*(?:UK|US|EU|IND)\b'
        ]
        
        # Price cleaning patterns
        self.price_patterns = [
            r'₹\s*(\d+(?:,\d+)*(?:\.\d+)?)',
            r'Rs\.?\s*(\d+(?:,\d+)*(?:\.\d+)?)',
            r'INR\s*(\d+(?:,\d+)*(?:\.\d+)?)',
            r'(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:₹|Rs|INR)'
        ]
        
        self.response_templates = {
            'standard': "{brand} {title} @{price} rs {url}",
            'with_size': "{brand} {title} Size - {size} @{price} rs {url}",
            'with_color': "{brand} {title} Color - {color} @{price} rs {url}",
            'with_pack': "{brand} {title} ({pack}) @{price} rs {url}",
            'minimal': "{title} @{price} rs {url}",
            'no_price': "{brand} {title} {url}",
            'error_fallback': "Product from {platform} {url}"
        }
        
        self.quality_weights = {
            'has_title': 40,
            'has_price': 30,
            'has_brand': 15,
            'has_images': 10,
            'title_length_good': 5
        }

    def parse_product(self, raw_data: Dict) -> Optional[Dict]:
        """Parse raw scraped data into ReviewCheckk format."""
        try:
            if not raw_data or not raw_data.get('title'):
                debug_tracker.log_event(
                    DebugLevel.WARNING, 'parser', 'parse_failed',
                    'No title in raw data', {'raw_data_keys': list(raw_data.keys()) if raw_data else []}
                )
                return None
            
            parsed_data = {
                'platform': raw_data.get('platform', 'unknown'),
                'url': raw_data.get('url', ''),
                'raw_title': raw_data.get('title', ''),
                'out_of_stock': raw_data.get('out_of_stock', False)
            }
            
            # Step 1: Clean and analyze title
            title_analysis = self._analyze_title(raw_data['title'])
            parsed_data.update(title_analysis)
            
            # Step 2: Parse and format price
            price_info = self._parse_price(raw_data.get('price', ''))
            parsed_data.update(price_info)
            
            # Step 3: Extract brand information
            brand_info = self._extract_brand(raw_data.get('brand', ''), parsed_data['clean_title'])
            parsed_data.update(brand_info)
            
            # Step 4: Detect category and attributes
            category_info = self._detect_category(parsed_data['clean_title'])
            parsed_data.update(category_info)
            
            quality_score = self._assess_quality(parsed_data)
            parsed_data['quality_score'] = quality_score
            
            template_choice = self._select_template(parsed_data)
            parsed_data['template_used'] = template_choice
            
            # Step 5: Format final message using smart template
            formatted_message = self._format_message_smart(parsed_data, template_choice)
            parsed_data['formatted_message'] = formatted_message
            
            # Step 6: Generate wishlink-style URL (if needed)
            if parsed_data.get('price_numeric'):
                parsed_data['wishlink_url'] = self._generate_wishlink_style(parsed_data)
            
            debug_tracker.log_event(
                DebugLevel.INFO, 'parser', 'parse_success',
                f'Successfully parsed: {parsed_data.get("display_title", "Unknown")}',
                {
                    'quality_score': quality_score,
                    'template_used': template_choice,
                    'has_price': bool(parsed_data.get('price_numeric')),
                    'has_brand': bool(parsed_data.get('brand'))
                }
            )
            
            return parsed_data
            
        except Exception as e:
            debug_tracker.log_event(
                DebugLevel.ERROR, 'parser', 'parse_error',
                f'Error parsing product data: {str(e)}',
                {'raw_data': raw_data}
            )
            logger.error(f"Error parsing product data: {str(e)}")
            return None

    def _analyze_title(self, title: str) -> Dict:
        """Analyze and clean product title."""
        try:
            # Clean title
            clean_title = self._clean_title(title)
            
            # Extract size information
            sizes = self._extract_sizes(title)
            
            # Extract quantity/pack information
            quantity_info = self._extract_quantity(title)
            
            # Extract color information
            color_info = self._extract_color(title)
            
            return {
                'clean_title': clean_title,
                'sizes': sizes,
                'quantity': quantity_info.get('quantity'),
                'pack_size': quantity_info.get('pack_size'),
                'color': color_info
            }
            
        except Exception as e:
            logger.error(f"Error analyzing title: {str(e)}")
            return {'clean_title': title}

    def _clean_title(self, title: str) -> str:
        """Clean product title by removing noise and formatting."""
        try:
            # Remove extra spaces and normalize
            title = re.sub(r'\s+', ' ', title).strip()
            
            # Remove common noise patterns
            noise_patterns = [
                r'$$[^)]*$$',  # Remove content in parentheses
                r'\[[^\]]*\]',  # Remove content in brackets
                r'(?i)\b(?:best|offer|deal|sale|discount|free|gift|new|latest|trending|hot|popular)\b',
                r'(?i)\b(?:premium|luxury|branded|original|authentic|genuine)\b',
                r'(?i)\b(?:combo|set of|pack of|bundle)\b',
                r'(?i)\b(?:for men|for women|for girls|for boys|unisex)\b',
                r'(?i)\b(?:size|color|colour):\s*\w+\b',
                r'₹[\d,]+(?:\.\d+)?',  # Remove price mentions
                r'Rs\.?[\d,]+(?:\.\d+)?',
                r'\d+%\s*off',  # Remove discount percentages
                r'(?i)\b(?:limited time|hurry|only|just)\b'
            ]
            
            for pattern in noise_patterns:
                title = re.sub(pattern, '', title)
            
            # Clean up extra spaces and punctuation
            title = re.sub(r'\s*[,.-]\s*', ' ', title)
            title = re.sub(r'\s+', ' ', title).strip()
            
            # Capitalize properly
            title = self._proper_case(title)
            
            return title
            
        except Exception as e:
            logger.error(f"Error cleaning title: {str(e)}")
            return title

    def _extract_sizes(self, title: str) -> List[str]:
        """Extract size information from title."""
        sizes = []
        try:
            for pattern in self.size_patterns:
                matches = re.findall(pattern, title, re.IGNORECASE)
                sizes.extend(matches)
            
            # Clean and deduplicate sizes
            sizes = list(set([size.upper() for size in sizes if size]))
            return sizes[:3]  # Limit to 3 sizes
            
        except Exception as e:
            logger.debug(f"Error extracting sizes: {str(e)}")
            return []

    def _extract_quantity(self, title: str) -> Dict:
        """Extract quantity and pack information."""
        try:
            quantity_patterns = [
                r'(?i)\b(?:pack of|set of)\s*(\d+)\b',
                r'(?i)\b(\d+)\s*(?:pack|set|pcs?|pieces?)\b',
                r'(?i)\b(\d+)\s*in\s*1\b'
            ]
            
            for pattern in quantity_patterns:
                match = re.search(pattern, title)
                if match:
                    quantity = int(match.group(1))
                    return {
                        'quantity': f"{quantity}pcs" if quantity > 1 else None,
                        'pack_size': quantity if quantity > 1 else None
                    }
            
            return {'quantity': None, 'pack_size': None}
            
        except Exception as e:
            logger.debug(f"Error extracting quantity: {str(e)}")
            return {'quantity': None, 'pack_size': None}

    def _extract_color(self, title: str) -> Optional[str]:
        """Extract color information from title."""
        try:
            colors = [
                'black', 'white', 'red', 'blue', 'green', 'yellow', 'pink', 'purple',
                'brown', 'grey', 'gray', 'orange', 'navy', 'maroon', 'beige', 'cream',
                'gold', 'silver', 'rose', 'mint', 'coral', 'teal', 'olive', 'khaki'
            ]
            
            title_lower = title.lower()
            for color in colors:
                if f' {color} ' in f' {title_lower} ' or title_lower.startswith(f'{color} ') or title_lower.endswith(f' {color}'):
                    return color.title()
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting color: {str(e)}")
            return None

    def _parse_price(self, price_str: str) -> Dict:
        """Parse and format price information."""
        try:
            if not price_str:
                return {'price': None, 'price_numeric': None, 'formatted_price': None}
            
            # Extract numeric price
            price_numeric = None
            for pattern in self.price_patterns:
                match = re.search(pattern, price_str)
                if match:
                    price_text = match.group(1).replace(',', '')
                    try:
                        price_numeric = float(price_text)
                        break
                    except ValueError:
                        continue
            
            if not price_numeric:
                # Fallback: extract any number
                numbers = re.findall(r'\d+(?:\.\d+)?', price_str.replace(',', ''))
                if numbers:
                    price_numeric = float(numbers[0])
            
            formatted_price = f"@{int(price_numeric)} rs" if price_numeric else None
            
            return {
                'price': price_str,
                'price_numeric': price_numeric,
                'formatted_price': formatted_price
            }
            
        except Exception as e:
            logger.error(f"Error parsing price: {str(e)}")
            return {'price': price_str, 'price_numeric': None, 'formatted_price': None}

    def _extract_brand(self, brand_str: str, title: str) -> Dict:
        """Extract and validate brand information."""
        try:
            detected_brand = None
            
            # First try explicit brand field
            if brand_str:
                brand_clean = clean_text(brand_str).lower()
                if brand_clean in self.brands:
                    detected_brand = brand_clean.title()
            
            # If no brand found, search in title
            if not detected_brand:
                title_lower = title.lower()
                for brand in self.brands:
                    if brand in title_lower:
                        detected_brand = brand.title()
                        break
            
            return {
                'brand': detected_brand,
                'has_brand': detected_brand is not None
            }
            
        except Exception as e:
            logger.debug(f"Error extracting brand: {str(e)}")
            return {'brand': None, 'has_brand': False}

    def _detect_category(self, title: str) -> Dict:
        """Detect product category from title."""
        try:
            title_lower = title.lower()
            detected_category = None
            
            for category, keywords in self.category_keywords.items():
                if any(keyword in title_lower for keyword in keywords):
                    detected_category = category
                    break
            
            return {
                'category': detected_category,
                'is_clothing': detected_category in ['clothing', 'footwear'],
                'is_beauty': detected_category == 'beauty',
                'is_accessory': detected_category == 'accessories'
            }
            
        except Exception as e:
            logger.debug(f"Error detecting category: {str(e)}")
            return {'category': None, 'is_clothing': False, 'is_beauty': False, 'is_accessory': False}

    def _format_message_smart(self, data: Dict, template: str) -> str:
        """Format message using selected template with smart fallbacks."""
        try:
            # Prepare template variables
            variables = {
                'brand': data.get('brand', '').strip(),
                'title': data.get('clean_title', '').strip(),
                'price': int(data.get('price_numeric', 0)) if data.get('price_numeric') else '',
                'url': data.get('url', ''),
                'platform': data.get('platform', 'unknown'),
                'size': ', '.join(data.get('sizes', [])[:2]) if data.get('sizes') else '',
                'color': data.get('color', ''),
                'pack': data.get('quantity', '')
            }
            
            # Clean up variables - remove empty ones for cleaner output
            clean_variables = {}
            for key, value in variables.items():
                if value and str(value).strip():
                    clean_variables[key] = str(value).strip()
            
            # Get template
            template_str = self.response_templates.get(template, self.response_templates['error_fallback'])
            
            # Smart formatting with fallbacks
            try:
                # Try to format with all variables
                formatted = template_str.format(**clean_variables)
                
                # Clean up extra spaces and formatting issues
                formatted = re.sub(r'\s+', ' ', formatted)
                formatted = re.sub(r'\s+@\s*rs', ' @0 rs', formatted)  # Handle missing price
                formatted = formatted.replace(' @0 rs', '')  # Remove zero price
                formatted = formatted.strip()
                
                # Ensure minimum quality
                if len(formatted) < 10 or not any(char.isalnum() for char in formatted):
                    raise ValueError("Formatted message too short or invalid")
                
                return formatted
                
            except (KeyError, ValueError) as e:
                # Fallback to minimal template
                logger.warning(f"Template formatting failed: {e}, using fallback")
                
                title = clean_variables.get('title', 'Product')
                url = clean_variables.get('url', '')
                price = clean_variables.get('price', '')
                
                if price:
                    return f"{title} @{price} rs {url}".strip()
                else:
                    return f"{title} {url}".strip()
                    
        except Exception as e:
            logger.error(f"Error in smart formatting: {str(e)}")
            # Ultimate fallback
            return f"Product from {data.get('platform', 'unknown')} {data.get('url', '')}"

    def _generate_wishlink_style(self, data: Dict) -> str:
        """Generate a wishlink-style URL format."""
        try:
            # This is a placeholder - in real implementation, you'd integrate with wishlink API
            # For now, return the original URL
            return data.get('url', '')
            
        except Exception as e:
            logger.debug(f"Error generating wishlink URL: {str(e)}")
            return data.get('url', '')

    def _proper_case(self, text: str) -> str:
        """Convert text to proper case while preserving brand names."""
        try:
            words = text.split()
            result = []
            
            for word in words:
                word_lower = word.lower()
                # Check if it's a known brand (preserve original case)
                if word_lower in self.brands:
                    # Find the original brand name with proper case
                    for brand in BRANDS:
                        if brand.lower() == word_lower:
                            result.append(brand)
                            break
                    else:
                        result.append(word.title())
                else:
                    result.append(word.title())
            
            return ' '.join(result)
            
        except Exception as e:
            logger.debug(f"Error in proper case conversion: {str(e)}")
            return text.title()

    def format_for_telegram(self, parsed_data: Dict) -> str:
        """Format parsed data for Telegram message with smart enhancements."""
        try:
            if not parsed_data:
                return "❌ Unable to extract product info."
            
            base_message = parsed_data.get('formatted_message', '')
            
            # Add quality indicator for debugging (remove in production)
            quality_score = parsed_data.get('quality_score', 0)
            
            # Smart enhancement based on quality and platform
            if quality_score >= 70:
                # High quality - add extra details
                enhancements = []
                
                if parsed_data.get('category') == 'clothing' and parsed_data.get('sizes'):
                    sizes_str = ', '.join(parsed_data['sizes'][:2])
                    if 'Size -' not in base_message:
                        enhancements.append(f"Size - {sizes_str}")
                
                if parsed_data.get('color') and 'Color -' not in base_message:
                    enhancements.append(f"Color - {parsed_data['color']}")
                
                # Add pincode for low-price items (ReviewCheckk style)
                if parsed_data.get('price_numeric') and parsed_data['price_numeric'] < 500:
                    enhancements.append("Pin - 110001")
                
                if enhancements:
                    base_message += f" {' '.join(enhancements)}"
            
            elif quality_score < 50:
                # Low quality - add platform indicator
                platform = parsed_data.get('platform', 'unknown').title()
                if platform not in base_message:
                    base_message = f"[{platform}] {base_message}"
            
            # Final cleanup
            base_message = re.sub(r'\s+', ' ', base_message).strip()
            
            # Ensure message is not empty
            if not base_message or len(base_message) < 5:
                return f"Product from {parsed_data.get('platform', 'unknown')} {parsed_data.get('url', '')}"
            
            return base_message
            
        except Exception as e:
            logger.error(f"Error formatting for Telegram: {str(e)}")
            debug_tracker.log_event(
                DebugLevel.ERROR, 'parser', 'telegram_format_error',
                f'Error formatting for Telegram: {str(e)}',
                {'parsed_data': parsed_data}
            )
            return "❌ Unable to format product info."

    def _assess_quality(self, data: Dict) -> int:
        """Assess the quality of extracted data."""
        score = 0
        
        if data.get('clean_title') and len(data['clean_title']) > 5:
            score += self.quality_weights['has_title']
            
            # Bonus for good title length (not too short, not too long)
            title_len = len(data['clean_title'].split())
            if 3 <= title_len <= 8:
                score += self.quality_weights['title_length_good']
        
        if data.get('price_numeric'):
            score += self.quality_weights['has_price']
        
        if data.get('brand'):
            score += self.quality_weights['has_brand']
        
        if data.get('images'):
            score += self.quality_weights['has_images']
        
        return score

    def _select_template(self, data: Dict) -> str:
        """Select the best template based on available data."""
        # High quality data - use detailed template
        if data.get('quality_score', 0) >= 80:
            if data.get('sizes') and data.get('price_numeric'):
                return 'with_size'
            elif data.get('color') and data.get('price_numeric'):
                return 'with_color'
            elif data.get('pack_size') and data.get('pack_size') > 1:
                return 'with_pack'
            elif data.get('brand') and data.get('price_numeric'):
                return 'standard'
        
        # Medium quality - use simpler templates
        if data.get('price_numeric'):
            if data.get('brand'):
                return 'standard'
            else:
                return 'minimal'
        
        # Low quality - fallback templates
        if data.get('brand'):
            return 'no_price'
        
        return 'error_fallback'

# Global parser instance
smart_parser = SmartProductParser()

def parse_product_data(raw_data: Dict) -> Optional[Dict]:
    """Parse raw product data using the smart parser."""
    return smart_parser.parse_product(raw_data)

def format_product_message(parsed_data: Dict) -> str:
    """Format parsed product data for Telegram."""
    return smart_parser.format_for_telegram(parsed_data)
