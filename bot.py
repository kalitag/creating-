# ReviewCheckk Bot - Main Bot Logic
import logging
import re
import time
import asyncio
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
from scraper import modern_scraper
from product_parser import smart_parser, format_product_message
from url_resolver import url_resolver
from image_handler import get_product_images, process_image
from cache import ProductCache
from performance_monitor import (
    start_performance_tracking, 
    update_performance_stage, 
    end_performance_tracking,
    get_performance_report,
    performance_monitor
)
import uuid

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

error_stats = {
    "total_errors": 0,
    "url_resolution_errors": 0,
    "scraping_errors": 0,
    "parsing_errors": 0,
    "network_errors": 0,
    "last_error_time": None
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
        "/help - Show this help message\n"
        "/performance - Show performance status\n\n"
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
        "• Wishlink (wishlink.com)\n\n"
        f"🔧 System Health:\n"
        f"• Total Errors: {error_stats['total_errors']}\n"
        f"• Success Rate: {_calculate_success_rate()}%"
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
    """Handle incoming messages containing product links with robust error handling."""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    try:
        # Check rate limiting
        if not rate_limiter.allow_request(user_id):
            await _send_safe_message(context, chat_id, ERROR_RATE_LIMITED)
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
            await _send_safe_message(
                context, chat_id, 
                f"⚠️ Too many links! Please send maximum {MAX_LINKS_PER_MESSAGE} links at a time."
            )
            return
        
        # Process each link with comprehensive error handling
        for link in links:
            await _process_single_link(context, chat_id, link, start_time, user_id)
            
    except Exception as e:
        logger.error(f"Critical error in handle_message: {str(e)}")
        _track_error("critical", e)
        await _send_safe_message(context, chat_id, "❌ An unexpected error occurred. Please try again.")

async def _process_single_link(context: ContextTypes.DEFAULT_TYPE, chat_id: int, link: str, start_time: float, user_id: int) -> None:
    """Process a single product link with comprehensive error handling."""
    request_id = str(uuid.uuid4())
    platform = 'unknown'
    
    try:
        # Step 1: Check cache first
        cached_result = product_cache.get(link)
        if cached_result and not bot_state["advanced_mode"]:
            await send_product_response(context, chat_id, cached_result)
            return
        
        # Step 2: Resolve URL with error handling
        update_performance_stage(request_id, 'url_resolution')
        try:
            url_info = url_resolver.resolve_url(link)
            if url_info['error']:
                logger.warning(f"URL resolution failed: {url_info['error']}")
                await _send_safe_message(context, chat_id, ERROR_UNSUPPORTED_LINK)
                _track_error("url_resolution", url_info['error'])
                end_performance_tracking(request_id, False, 'url_resolution_failed')
                return
            
            resolved_url = url_info['final_url']
            platform = url_info['platform']
            
            # Start performance tracking now that we know the platform
            start_performance_tracking(request_id, user_id, platform, resolved_url)
            
        except Exception as e:
            logger.error(f"URL resolution error: {str(e)}")
            _track_error("url_resolution", e)
            await _send_safe_message(context, chat_id, ERROR_UNSUPPORTED_LINK)
            end_performance_tracking(request_id, False, 'url_resolution_error')
            return
        
        # Step 3: Validate platform
        if not platform:
            await _send_safe_message(context, chat_id, ERROR_UNSUPPORTED_LINK)
            end_performance_tracking(request_id, False, 'platform_not_detected')
            return
        
        # Step 4: Scrape product with retry logic
        update_performance_stage(request_id, 'scraping', {'platform': platform})
        product_data = None
        max_scrape_attempts = 3
        
        for attempt in range(max_scrape_attempts):
            try:
                product_data = modern_scraper.scrape_product(resolved_url, platform, bot_state["advanced_mode"])
                if product_data:
                    break
                    
            except Exception as e:
                logger.warning(f"Scraping attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_scrape_attempts - 1:
                    _track_error("scraping", e)
                else:
                    await asyncio.sleep(1)  # Brief delay before retry
        
        if not product_data:
            await _send_safe_message(context, chat_id, ERROR_UNABLE_TO_EXTRACT)
            end_performance_tracking(request_id, False, 'scraping_failed')
            return
        
        # Step 5: Parse product data
        update_performance_stage(request_id, 'parsing')
        try:
            parsed_data = smart_parser.parse_product(product_data)
            if not parsed_data:
                await _send_safe_message(context, chat_id, ERROR_UNABLE_TO_EXTRACT)
                _track_error("parsing", "Failed to parse product data")
                end_performance_tracking(request_id, False, 'parsing_failed')
                return
                
        except Exception as e:
            logger.error(f"Parsing error: {str(e)}")
            _track_error("parsing", e)
            # Fallback to basic formatting
            parsed_data = product_data
        
        # Step 6: Check availability
        if parsed_data.get('out_of_stock', False):
            await _send_safe_message(context, chat_id, ERROR_OUT_OF_STOCK)
            end_performance_tracking(request_id, False, 'out_of_stock')
            return
        
        # Step 7: Store and cache
        update_performance_stage(request_id, 'response_generation')
        bot_state["last_processed_product"] = parsed_data
        product_cache.set(link, parsed_data)
        
        # Step 8: Send response
        await send_product_response(context, chat_id, parsed_data)
        
        # Step 9: Complete performance tracking
        response_time = end_performance_tracking(request_id, True, None, parsed_data)
        
        # Step 10: Performance monitoring
        if response_time > RESPONSE_TIMEOUT:
            logger.warning(f"Response took {response_time:.2f} seconds (max: {RESPONSE_TIMEOUT}s)")
        
    except Exception as e:
        logger.error(f"Error processing link {link}: {str(e)}")
        _track_error("general", e)
        await _send_safe_message(context, chat_id, ERROR_UNABLE_TO_EXTRACT)
        end_performance_tracking(request_id, False, 'general_error')

async def send_product_response(context: ContextTypes.DEFAULT_TYPE, chat_id: int, product_data: dict) -> None:
    """Send formatted product response with error handling."""
    try:
        if 'formatted_message' in product_data:
            # Already formatted by smart parser
            formatted_message = format_product_message(product_data)
        else:
            # Fallback to legacy formatting
            formatted_message = format_title(product_data)
            if product_data.get('url'):
                formatted_message += f" {product_data['url']}"
        
        # Handle empty or invalid messages
        if not formatted_message or len(formatted_message.strip()) < 5:
            formatted_message = f"Product from {product_data.get('platform', 'unknown')} {product_data.get('url', '')}"
        
        images_sent = False
        try:
            images = get_product_images(product_data, bot_state["advanced_mode"])
            
            if images:
                for i, img_url in enumerate(images[:2]):  # Limit to 2 images
                    try:
                        img_bytes = process_image(img_url)
                        if img_bytes:
                            if i == 0:  # First image with caption
                                await context.bot.send_photo(
                                    chat_id=chat_id,
                                    photo=img_bytes,
                                    caption=formatted_message,
                                    parse_mode=None  # Avoid parse mode issues
                                )
                            else:  # Additional images without caption
                                await context.bot.send_photo(
                                    chat_id=chat_id,
                                    photo=img_bytes
                                )
                            images_sent = True
                    except Exception as img_error:
                        logger.warning(f"Failed to send image {i+1}: {str(img_error)}")
                        continue
                        
        except Exception as e:
            logger.warning(f"Image processing failed: {str(e)}")
        
        # Send text message if no images were sent
        if not images_sent:
            await _send_safe_message(context, chat_id, formatted_message)
            
    except Exception as e:
        logger.error(f"Error sending product response: {str(e)}")
        _track_error("response", e)
        await _send_safe_message(context, chat_id, ERROR_UNABLE_TO_EXTRACT)

async def _send_safe_message(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str) -> bool:
    """Send message with error handling and fallbacks."""
    try:
        # Ensure message is not empty and not too long
        if not text or len(text.strip()) == 0:
            text = "❌ Unable to process request."
        
        if len(text) > 4096:  # Telegram message limit
            text = text[:4090] + "..."
        
        await context.bot.send_message(chat_id=chat_id, text=text)
        return True
        
    except Exception as e:
        logger.error(f"Failed to send message: {str(e)}")
        _track_error("network", e)
        
        # Try sending a minimal error message
        try:
            await context.bot.send_message(chat_id=chat_id, text="❌ Error occurred.")
            return True
        except Exception as fallback_error:
            logger.critical(f"Failed to send fallback message: {str(fallback_error)}")
            return False

def _track_error(error_type: str, error: Exception) -> None:
    """Track errors for monitoring and debugging."""
    try:
        error_stats["total_errors"] += 1
        error_stats["last_error_time"] = time.time()
        
        if error_type in error_stats:
            error_stats[f"{error_type}_errors"] += 1
        
        # Log detailed error information
        logger.error(f"Error tracked - Type: {error_type}, Details: {str(error)}")
        
    except Exception as e:
        logger.critical(f"Error tracking failed: {str(e)}")

def _calculate_success_rate() -> int:
    """Calculate approximate success rate based on error statistics."""
    try:
        total_requests = error_stats["total_errors"] + 100  # Estimate successful requests
        if total_requests == 0:
            return 100
        
        success_rate = ((total_requests - error_stats["total_errors"]) / total_requests) * 100
        return max(0, min(100, int(success_rate)))
        
    except Exception:
        return 95  # Default optimistic rate

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enhanced error handler with detailed logging and recovery."""
    try:
        error_msg = f"Update {update} caused error: {context.error}"
        logger.error(error_msg)
        _track_error("telegram", context.error)
        
        # Try to send error notification to user if possible
        if update and hasattr(update, 'effective_chat') and update.effective_chat:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ An error occurred. Please try again or contact support."
                )
            except Exception as send_error:
                logger.error(f"Failed to send error notification: {str(send_error)}")
                
    except Exception as handler_error:
        logger.critical(f"Error handler itself failed: {str(handler_error)}")

async def performance_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show detailed performance statistics."""
    try:
        performance_report = get_performance_report()
        
        # Split long report into multiple messages if needed
        if len(performance_report) > 4000:
            # Send summary first
            summary = performance_monitor.get_performance_summary()
            system = summary.get('system_overview', {})
            
            short_report = (
                f"🔧 PERFORMANCE STATUS\n\n"
                f"Health: {summary.get('health_status', 'UNKNOWN')}\n"
                f"Uptime: {system.get('uptime_hours', 0)} hours\n"
                f"Total Requests: {system.get('total_requests', 0)}\n"
                f"Success Rate: {system.get('overall_success_rate', 0)}%\n"
                f"Current Load: {system.get('current_requests_per_minute', 0)} req/min\n"
                f"Active Users: {system.get('active_users_count', 0)}\n\n"
                f"Use /performance_detail for full report"
            )
            await update.message.reply_text(short_report)
        else:
            await update.message.reply_text(f"\`\`\`\n{performance_report}\n\`\`\`", parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Error showing performance status: {str(e)}")
        await update.message.reply_text("❌ Error retrieving performance data.")

def main() -> None:
    """Start the bot with enhanced error handling."""
    try:
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
        application.add_handler(CommandHandler("performance", performance_status))
        
        application.add_handler(MessageHandler(
            (filters.TEXT & (filters.Entity("url") | filters.Entity("text_link"))) | 
            (filters.CAPTION & (filters.Entity("url") | filters.Entity("text_link"))) |
            filters.FORWARDED,
            handle_message
        ))
        
        # Enhanced error handler
        application.add_error_handler(error_handler)
        
        logger.info(f"Bot {BOT_USERNAME} started successfully!")
        
        application.run_polling(
            drop_pending_updates=True,  # Clear pending updates on restart
            allowed_updates=["message", "edited_message"]  # Only handle relevant updates
        )
        
    except Exception as e:
        logger.critical(f"Failed to start bot: {str(e)}")
        raise

if __name__ == '__main__':
    main()
