# ReviewCheckk Bot - Main Bot Logic
import logging
import re
import time
from typing import List, Optional
from telegram import Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    ContextTypes,
    filters
)
from telegram.constants import ParseMode
from config import (
    BOT_TOKEN, 
    BOT_USERNAME,
    RESPONSE_TIMEOUT,
    MAX_LINKS_PER_MESSAGE,
    ERROR_UNSUPPORTED_LINK,
    ERROR_UNABLE_TO_EXTRACT,
    ERROR_OUT_OF_STOCK,
    ERROR_RATE_LIMITED,
    DEFAULT_PIN
)
from utils import (
    setup_logging, 
    extract_links, 
    unshorten_url, 
    clean_link,
    format_title,
    detect_platform,
    RateLimiter
)
from scraper import scrape_product
from image_handler import get_product_images, process_image
from cache import ProductCache

logger = logging.getLogger(__name__)

# Initialize components
rate_limiter = RateLimiter()
product_cache = ProductCache()

# Bot State
bot_state = {
    "advanced_mode": False,
    "stock_check_enabled": False,
    "last_processed_product": None
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    welcome_message = (
        f"📖 ReviewCheckk Bot Master Rulebook (99+ Rules)\n\n"
        f"🎯 I'm {BOT_USERNAME}, here to automate deal post creation in the same format as @reviewcheckk.\n\n"
        "Send me any e-commerce product link (Amazon, Flipkart, Meesho, Myntra, etc.) "
        "and I'll format it perfectly for you!\n\n"
        "Available commands:\n"
        "/advancing - Enable Advanced Mode (stock check, size-wise pricing)\n"
        "/off_advancing - Disable Advanced Mode\n"
        "/img - Refresh image for the last processed product\n"
        "/curl [channel] [month] - Crawl old deals from a channel\n"
        "/status - Check bot status and settings\n"
        "/help - Show this help message\n\n"
        "All links are automatically cleaned and formatted according to the Rulebook."
    )
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    await start(update, context)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show bot status and current settings."""
    status_message = (
        f"🤖 Bot Status: {BOT_USERNAME}\n\n"
        f"⚙️ Current Settings:\n"
        f"• Advanced Mode: {'✅ Enabled' if bot_state['advanced_mode'] else '❌ Disabled'}\n"
        f"• Stock Check: {'✅ Enabled' if bot_state['stock_check_enabled'] else '❌ Disabled'}\n"
        f"• Cache Size: {product_cache.size()}\n"
        f"• Rate Limiting: Active\n\n"
        f"📊 Supported Platforms:\n"
        "• Amazon (amazon.in, amazon.com)\n"
        "• Flipkart (flipkart.com)\n"
        "• Meesho (meesho.com)\n"
        "• Myntra (myntra.com)\n"
        "• Ajio (ajio.com)\n"
        "• Snapdeal (snapdeal.com)\n"
        "• Wishlink (wishlink.com)"
    )
    await update.message.reply_text(status_message)

async def advancing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enable Advanced Mode."""
    global bot_state
    bot_state["advanced_mode"] = True
    bot_state["stock_check_enabled"] = True
    
    await update.message.reply_text(
        "✅ Advanced Mode enabled!\n\n"
        "• Stock check enabled\n"
        "• Size-wise pricing\n"
        "• Fresh screenshot auto-capture\n"
        "• Watermark auto-replacement\n"
        "• Enhanced product analysis"
    )

async def off_advancing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Disable Advanced Mode."""
    global bot_state
    bot_state["advanced_mode"] = False
    bot_state["stock_check_enabled"] = False
    
    await update.message.reply_text(
        "✅ Advanced Mode disabled. Switched to Standard Mode.\n\n"
        "• Faster response\n"
        "• Simple scrape\n"
        "• No heavy stock-check\n"
        "• Basic product analysis"
    )

async def img(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Refresh image for the last processed product."""
    if not bot_state.get("last_processed_product"):
        await update.message.reply_text("❌ No recent product to refresh image for.")
        return
    
    try:
        product_data = bot_state["last_processed_product"]
        await update.message.reply_text("🔄 Refreshing image...")
        
        # Get fresh images
        images = get_product_images(product_data, force_refresh=True)
        
        if images:
            for img_url in images[:2]:  # Limit to 2 images
                img_bytes = process_image(img_url)
                if img_bytes:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=img_bytes
                    )
            await update.message.reply_text("✅ Image refreshed successfully!")
        else:
            await update.message.reply_text("❌ No images available for this product.")
            
    except Exception as e:
        logger.error(f"Error refreshing image: {str(e)}")
        await update.message.reply_text("❌ Error refreshing image. Please try again.")

async def curl(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Crawl old deals from a channel."""
    if len(context.args) < 2:
        await update.message.reply_text(
            "⚠️ Usage: /curl [channel] [month]\n"
            "Example: /curl @mychannel August\n"
            "Example: /curl @reviewcheckk December"
        )
        return
    
    channel = context.args[0]
    month = " ".join(context.args[1:])
    
    await update.message.reply_text(
        f"🔍 Crawling deals from {channel} for {month}...\n"
        "This feature is currently in development.\n"
        "It will scan historical messages and extract deal patterns."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages containing product links."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    # Check rate limiting
    if not rate_limiter.allow_request(user_id):
        await context.bot.send_message(
            chat_id=chat_id,
            text=ERROR_RATE_LIMITED
        )
        return
    
    start_time = time.time()
    
    # Get message text or caption (for forwarded messages with captions)
    message_text = update.effective_message.text or update.effective_message.caption or ""
    
    # Extract all links from the message
    links = extract_links(message_text)
    
    if not links:
        # No links found, ignore the message
        return
    
    # Limit number of links to prevent spam
    if len(links) > MAX_LINKS_PER_MESSAGE:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ Too many links! Please send maximum {MAX_LINKS_PER_MESSAGE} links at a time."
        )
        return
    
    # Process each link separately
    for link in links:
        try:
            # Check cache first
            cached_result = product_cache.get(link)
            if cached_result and not bot_state["advanced_mode"]:
                await send_product_response(context, chat_id, cached_result)
                continue
            
            # Expand shortened URLs
            resolved_url = unshorten_url(link)
            
            # Clean the link (remove affiliate tags)
            cleaned_url = clean_link(resolved_url)
            
            # Detect platform
            platform = detect_platform(cleaned_url)
            if not platform:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=ERROR_UNSUPPORTED_LINK
                )
                continue
            
            # Scrape product details
            product_data = scrape_product(cleaned_url, platform, bot_state["advanced_mode"])
            if not product_data:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=ERROR_UNABLE_TO_EXTRACT
                )
                continue
            
            # Check if out of stock
            if product_data.get('out_of_stock', False):
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=ERROR_OUT_OF_STOCK
                )
                continue
            
            # Store as last processed product
            bot_state["last_processed_product"] = product_data
            
            # Cache the result
            product_cache.set(link, product_data)
            
            # Send response
            await send_product_response(context, chat_id, product_data)
            
            # Enforce response time limit
            elapsed = time.time() - start_time
            if elapsed > RESPONSE_TIMEOUT:
                logger.warning(f"Response took {elapsed:.2f} seconds (max: {RESPONSE_TIMEOUT}s)")
            
        except Exception as e:
            logger.error(f"Error processing link {link}: {str(e)}")
            await context.bot.send_message(
                chat_id=chat_id,
                text=ERROR_UNABLE_TO_EXTRACT
            )

async def send_product_response(context: ContextTypes.DEFAULT_TYPE, chat_id: int, product_data: dict) -> None:
    """Send formatted product response."""
    try:
        # Format the title
        formatted_title = format_title(product_data)
        
        # Build the response message
        response_lines = [formatted_title]
        
        # Add URL
        response_lines.append(product_data.get('url', ''))
        response_lines.append("")  # Empty line
        
        # Add size information (if available and relevant)
        sizes = product_data.get('sizes')
        platform = product_data.get('platform', '')
        
        if sizes and platform == "meesho":
            size_str = ", ".join(sizes) if isinstance(sizes, list) else sizes
            response_lines.append(f"Size - {size_str}")
        
        # Add pin code (Meesho specific)
        if platform == "meesho":
            pin = DEFAULT_PIN
            response_lines.append(f"Pin - {pin}")
            response_lines.append("")  # Empty line
        
        # Add footer
        response_lines.append("@reviewcheckk")
        
        response = "\n".join(response_lines)
        
        # Get product images
        images = get_product_images(product_data, bot_state["advanced_mode"])
        
        # Send the response
        if images:
            first_image = True
            for img_url in images[:2]:  # Limit to 2 images
                img_bytes = process_image(img_url)
                if img_bytes:
                    if first_image:
                        await context.bot.send_photo(
                            chat_id=chat_id,
                            photo=img_bytes,
                            caption=response,
                            parse_mode=ParseMode.MARKDOWN
                        )
                        first_image = False
                    else:
                        await context.bot.send_photo(
                            chat_id=chat_id,
                            photo=img_bytes
                        )
            
            # If no images were processed, send text only
            if first_image:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=response
                )
        else:
            # No images available, send text only
            await context.bot.send_message(
                chat_id=chat_id,
                text=response
            )
            
    except Exception as e:
        logger.error(f"Error sending product response: {str(e)}")
        await context.bot.send_message(
            chat_id=chat_id,
            text=ERROR_UNABLE_TO_EXTRACT
        )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log Errors caused by Updates."""
    logger.error(f"Update {update} caused error: {context.error}")

def main() -> None:
    """Start the bot."""
    # Set up logging
    setup_logging()
    
    logger.info(f"Starting {BOT_USERNAME}...")
    
    # Validate bot token
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("Bot token not configured! Please set BOT_TOKEN in environment variables.")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("advancing", advancing))
    application.add_handler(CommandHandler("off_advancing", off_advancing))
    application.add_handler(CommandHandler("img", img))
    application.add_handler(CommandHandler("curl", curl))
    
    application.add_handler(MessageHandler(
        (filters.TEXT & (filters.Entity("url") | filters.Entity("text_link"))) | 
        (filters.CAPTION & (filters.Entity("url") | filters.Entity("text_link"))) |
        filters.FORWARDED,
        handle_message
    ))
    
    # Log all errors
    application.add_error_handler(error_handler)
    
    logger.info(f"Bot {BOT_USERNAME} started successfully!")
    
    application.run_polling()

if __name__ == '__main__':
    main()
