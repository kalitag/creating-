# ReviewCheckk Bot - Image Processing Module
import logging
import requests
from io import BytesIO
from typing import List, Optional
from PIL import Image, ImageDraw, ImageFont
from config import REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

def get_product_images(product_data: dict, advanced_mode: bool = False, force_refresh: bool = False) -> List[str]:
    """Get product images from scraped data."""
    try:
        images = product_data.get('images', [])
        
        if not images:
            logger.warning("No images found in product data")
            return []
        
        # In advanced mode or force refresh, we might want to process images differently
        if advanced_mode or force_refresh:
            # Could implement screenshot capture here
            logger.info("Advanced mode image processing")
        
        # Return up to 2 images
        return images[:2]
        
    except Exception as e:
        logger.error(f"Error getting product images: {str(e)}")
        return []

def process_image(image_url: str) -> Optional[BytesIO]:
    """Process and optimize image for Telegram."""
    try:
        # Download image
        response = requests.get(image_url, timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            logger.error(f"Failed to download image: {response.status_code}")
            return None
        
        # Open image with PIL
        image = Image.open(BytesIO(response.content))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize if too large (Telegram limits)
        max_size = (1280, 1280)
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Save to BytesIO
        output = BytesIO()
        image.save(output, format='JPEG', quality=85, optimize=True)
        output.seek(0)
        
        return output
        
    except Exception as e:
        logger.error(f"Error processing image {image_url}: {str(e)}")
        return None

def remove_watermark(image: Image.Image) -> Image.Image:
    """Remove watermarks from product images (basic implementation)."""
    try:
        # This is a placeholder for watermark removal logic
        # In a real implementation, you might use more sophisticated techniques
        
        # For now, just return the original image
        return image
        
    except Exception as e:
        logger.error(f"Error removing watermark: {str(e)}")
        return image

def add_deal_overlay(image: Image.Image, deal_text: str) -> Image.Image:
    """Add deal overlay to product image."""
    try:
        # Create a copy to avoid modifying original
        img_copy = image.copy()
        draw = ImageDraw.Draw(img_copy)
        
        # Try to use a nice font, fallback to default
        try:
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            font = ImageFont.load_default()
        
        # Add semi-transparent overlay
        overlay = Image.new('RGBA', img_copy.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        # Draw background rectangle for text
        text_bbox = draw.textbbox((0, 0), deal_text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        x = img_copy.width - text_width - 20
        y = 20
        
        overlay_draw.rectangle(
            [x - 10, y - 5, x + text_width + 10, y + text_height + 5],
            fill=(255, 0, 0, 180)
        )
        
        # Composite overlay
        img_copy = Image.alpha_composite(img_copy.convert('RGBA'), overlay)
        
        # Add text
        draw = ImageDraw.Draw(img_copy)
        draw.text((x, y), deal_text, fill=(255, 255, 255), font=font)
        
        return img_copy.convert('RGB')
        
    except Exception as e:
        logger.error(f"Error adding deal overlay: {str(e)}")
        return image
