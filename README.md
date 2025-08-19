# ReviewCheckk Bot

📖 **ReviewCheckk Bot Master Rulebook (99+ Rules)** compliant Telegram bot for automating deal post creation.

## Features

✅ **Full Rulebook Compliance** - Implements all 99+ rules from the Master Rulebook  
✅ **Multi-Platform Support** - Works with Amazon, Flipkart, Meesho, Myntra, Ajio, Snapdeal, Wishlink  
✅ **Advanced Link Handling** - Automatically expands shortened URLs and cleans affiliate tags  
✅ **Perfect Title Formatting** - Creates minimal, clean titles following strict rules  
✅ **Smart Price Handling** - Formats prices correctly and selects lowest available price  
✅ **Meesho Special Handling** - Proper size and pin code formatting for Meesho products  
✅ **Image Processing** - Handles screenshots and removes watermarks  
✅ **Advanced Mode** - Enables stock checking and size-wise pricing  
✅ **Rate Limiting** - Prevents spam and abuse  
✅ **Caching System** - Improves performance with intelligent caching  
✅ **24/7 Operation** - Works in groups, channels, and private chats

## Installation

### Prerequisites

- Python 3.7+
- Telegram Bot Token

### Setup

1. Clone the repository:
\`\`\`bash
git clone https://github.com/kalitag/response-.git
cd response-
\`\`\`

2. Install dependencies:
\`\`\`bash
pip install -r requirements.txt
\`\`\`

3. Configure environment variables:
\`\`\`bash
cp .env.example .env
# Edit .env with your bot token and settings
\`\`\`

4. Run the bot:
\`\`\`bash
python bot.py
\`\`\`

### Docker Setup

1. Build the Docker image:
\`\`\`bash
docker build -t reviewcheckk-bot .
\`\`\`

2. Run with environment variables:
\`\`\`bash
docker run -d \
  --name reviewcheckk-bot \
  -e BOT_TOKEN="8327175937:AAGpC7M85iY-kbMVAcKJTrhXzKokWLGctCo" \
  -e BOT_USERNAME="@Easy_uknowbot" \
  reviewcheckk-bot
\`\`\`

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BOT_TOKEN` | Telegram Bot Token | Required |
| `BOT_USERNAME` | Bot Username | @Easy_uknowbot |
| `BOT_NAME` | Bot Display Name | ReviewCheckk Bot |
| `REQUEST_TIMEOUT` | HTTP request timeout | 10 |
| `MAX_RETRIES` | Maximum retry attempts | 3 |
| `RESPONSE_TIMEOUT` | Bot response timeout | 3 |
| `LOG_LEVEL` | Logging level | INFO |

### Security Features

- **Environment Variables**: Sensitive data stored in environment variables
- **Rate Limiting**: Prevents spam and abuse
- **Input Validation**: Validates URLs and user input
- **Error Handling**: Comprehensive error handling and logging
- **Cache Management**: Automatic cache cleanup and size limits

## Usage

### Commands

- `/start` - Show welcome message and help
- `/help` - Show help information
- `/status` - Check bot status and settings
- `/advancing` - Enable Advanced Mode
- `/off_advancing` - Disable Advanced Mode
- `/img` - Refresh image for last processed product
- `/curl [channel] [month]` - Crawl old deals from channel

### Supported Platforms

- **Amazon** (amazon.in, amazon.com)
- **Flipkart** (flipkart.com)
- **Meesho** (meesho.com)
- **Myntra** (myntra.com)
- **Ajio** (ajio.com)
- **Snapdeal** (snapdeal.com)
- **Wishlink** (wishlink.com)

### Advanced Features

#### Advanced Mode
- Stock checking
- Size-wise pricing
- Fresh screenshot capture
- Watermark replacement
- Enhanced product analysis

#### Caching System
- 5-minute cache TTL
- Maximum 1000 cached items
- Automatic cleanup
- Performance optimization

#### Rate Limiting
- 10 requests per minute per user
- Prevents spam and abuse
- Automatic rate limit enforcement

## Development

### Project Structure

\`\`\`
├── bot.py              # Main bot logic
├── config.py           # Configuration settings
├── utils.py            # Utility functions
├── scraper.py          # Web scraping module
├── image_handler.py    # Image processing
├── cache.py            # Caching system
├── requirements.txt    # Python dependencies
├── Dockerfile          # Docker configuration
├── .env.example        # Environment variables template
└── README.md           # This file
\`\`\`

### Adding New Platforms

1. Add domain to `SUPPORTED_DOMAINS` in `config.py`
2. Implement scraper function in `scraper.py`
3. Add platform-specific logic if needed
4. Test thoroughly with sample URLs

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the [License.txt](License.txt) file for details.

## Support

For support and questions:
- Open an issue on GitHub
- Contact the development team
- Check the documentation

## Changelog

### v2.0.0
- Added secure environment variable configuration
- Implemented rate limiting and caching
- Enhanced error handling and logging
- Added Docker support
- Improved security features
- Added comprehensive documentation

### v1.0.0
- Initial release
- Basic scraping functionality
- Multi-platform support
- Title formatting according to rulebook
