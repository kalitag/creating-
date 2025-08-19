import re
import logging
from typing import Dict, Optional, List, Tuple
from config import BRANDS
from utils import clean_text, format_price_number

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

    def parse_product(self, raw_data: Dict) -> Optional[Dict]:
        """Parse raw scraped data into ReviewCheckk format."""
        try:
            if not raw_data or not raw_data.get('title'):
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
            
            # Step 5: Format final message
            formatted_message = self._format_message(parsed_data)
            parsed_data['formatted_message'] = formatted_message
            
            # Step 6: Generate wishlink-style URL (if needed)
            if parsed_data.get('price_numeric'):
                parsed_data['wishlink_url'] = self._generate_wishlink_style(parsed_data)
            
            logger.info(f"Successfully parsed product: {parsed_data.get('display_title', 'Unknown')}")
            return parsed_data
            
        except Exception as e:
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

    def _format_message(self, data: Dict) -> str:
        """Format product data into ReviewCheckk style message."""
        try:
            # Build the display title
            title_parts = []
            
            # Add brand if available
            if data.get('brand'):
                title_parts.append(data['brand'])
            
            # Add main product name
            clean_title = data.get('clean_title', '').strip()
            if clean_title:
                title_parts.append(clean_title)
            
            # Add quantity if it's a pack
            if data.get('quantity'):
                title_parts.append(f"({data['quantity']})")
            
            # Combine title parts
            display_title = ' '.join(title_parts)
            
            # Add price
            if data.get('formatted_price'):
                display_title += f" {data['formatted_price']}"
            
            # Ensure title is not too long (max 8-10 words)
            words = display_title.split()
            if len(words) > 10:
                display_title = ' '.join(words[:10])
            
            # Store display title for reference
            data['display_title'] = display_title
            
            return display_title
            
        except Exception as e:
            logger.error(f"Error formatting message: {str(e)}")
            return data.get('clean_title', 'Product')

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
        """Format parsed data for Telegram message."""
        try:
            if not parsed_data:
                return "❌ Unable to extract product info."
            
            message = parsed_data.get('formatted_message', '')
            
            # Add wishlink URL if available
            if parsed_data.get('url'):
                # For now, use original URL - in production, convert to wishlink
                message += f" {parsed_data['url']}"
            
            # Add additional info if needed
            additional_info = []
            
            if parsed_data.get('sizes'):
                sizes_str = ', '.join(parsed_data['sizes'][:3])
                additional_info.append(f"Size - {sizes_str}")
            
            if parsed_data.get('color'):
                additional_info.append(f"Color - {parsed_data['color']}")
            
            # Add pincode placeholder (common in ReviewCheckk)
            if parsed_data.get('price_numeric') and parsed_data['price_numeric'] < 500:
                additional_info.append("Pin - 110001")
            
            if additional_info:
                message += f" {' '.join(additional_info)}"
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting for Telegram: {str(e)}")
            return "❌ Unable to format product info."

# Global parser instance
smart_parser = SmartProductParser()

def parse_product_data(raw_data: Dict) -> Optional[Dict]:
    """Parse raw product data using the smart parser."""
    return smart_parser.parse_product(raw_data)

def format_product_message(parsed_data: Dict) -> str:
    """Format parsed product data for Telegram."""
    return smart_parser.format_for_telegram(parsed_data)
