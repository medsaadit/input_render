# Crypto Callback System

A Flask-based webhook system for monitoring Solana blockchain transactions and automatically scraping token information from CoinMarketCap and DexScreener. The system processes new token pool creation events and sends alerts via Telegram.

## Features

- **Webhook Server**: Receives transaction data via HTTP callbacks
- **Token Analysis**: Automatically extracts pool and mint addresses from transaction data
- **Web Scraping**: Gathers token information from CoinMarketCap and DexScreener
- **Telegram Integration**: Sends formatted alerts to Telegram channels
- **Anti-Detection**: Uses undetected Chrome driver to bypass bot detection
- **Token Filtering**: Processes only recent tokens (within 20 seconds)

## Project Structure

```
crypto_calback/
├── server.py              # Flask webhook server
├── scrape.py             # Web scraping and Telegram messaging
├── telgram_setup.py      # Telegram client setup
├── localserver.py        # Local IP detection utility
├── requirements.txt      # Python dependencies
├── sample_response.json  # Example webhook payload
└── .gitignore           # Git ignore file
```

## Prerequisites

- Python 3.8 or higher
- Google Chrome browser installed
- Telegram account and bot credentials
- Mobula API key (for wallet analysis)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd crypto_calback
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file or update the configuration directly in the code:

```python
# Telegram API credentials (get from https://my.telegram.org/)
API_ID = your_api_id
API_HASH = 'your_api_hash'
TARGET_CHAT_ID = your_chat_id  # Telegram channel/group ID

# Mobula API key (get from https://mobula.io/)
MOBULA_API = "your_mobula_api_key"
```

## Configuration

### Telegram Setup

1. **Get Telegram API credentials:**

   - Visit https://my.telegram.org/
   - Create a new application
   - Note down your `API_ID` and `API_HASH`

2. **Get Chat ID:**

   - Add your bot to the target channel/group
   - Get the chat ID (negative number for groups/channels)

3. **Test Telegram connection:**
   ```bash
   python telgram_setup.py
   ```

### Chrome Profile Configuration

The scraper uses your existing Chrome profile to avoid login issues. Update the profile path in `scrape.py` if needed:

```python
# Windows default path
user_data_dir = os.path.join(user_home, "AppData", "Local", "Google", "Chrome", "User Data")

# macOS path
user_data_dir = os.path.join(user_home, "Library", "Application Support", "Google", "Chrome")

# Linux path
user_data_dir = os.path.join(user_home, ".config", "google-chrome")
```

## Deployment

### Local Development

1. **Start the Flask server:**

   ```bash
   python server.py
   ```

   The server will run on `http://127.0.0.1:5000`

2. **Get your local IP (for external access):**

   ```bash
   python localserver.py
   ```

3. **Test the webhook endpoint:**
   ```bash
   curl -X POST http://127.0.0.1:5000/ \
        -H "Content-Type: application/json" \
        -d @sample_response.json
   ```

### Production Deployment

#### Using Gunicorn (Recommended)

```bash
# Install gunicorn (already in requirements.txt)
pip install gunicorn

# Run with gunicorn
gunicorn --bind 0.0.0.0:5000 server:app

# With multiple workers
gunicorn --bind 0.0.0.0:5000 --workers 4 server:app
```

#### Using Docker

Create a `Dockerfile`:

```dockerfile
FROM python:3.9-slim

# Install Chrome dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "server:app"]
```

Build and run:

```bash
docker build -t crypto-callback .
docker run -p 5000:5000 crypto-callback
```

#### Cloud Deployment (Heroku, AWS, etc.)

For cloud deployment, you may need to:

- Use a headless Chrome setup
- Configure buildpacks for Chrome dependencies
- Set environment variables for API keys
- Use a web-accessible URL for webhooks

## API Endpoints

### POST /

**Webhook endpoint for receiving transaction data**

Accepts JSON payload with transaction information and extracts:

- Pool address (`liquidity_pool_address`)
- Token mint address (`token_mint_two` or `token_mint_one`)

### GET /get_crypto_tokens

**Retrieve processed tokens**

Returns all tokens received in the last 20 seconds and clears the storage.

Response format:

```json
{
  "status": "success",
  "count": 1,
  "tokens": [
    {
      "timestamp": 1719792000,
      "pool_address": "F86Rm73qaX7S38ZoocjzTZkLzQe6a1X575BcnjUtQzor",
      "mint_address": "2uhxAa6yag3zHtahLj4Cqn23fu9giheWj9c7DMwRjFvq",
      "received_at": "2025-06-30T12:00:00.000000Z"
    }
  ]
}
```

## Usage

### Basic Workflow

1. **Start the server** to listen for webhook callbacks
2. **Configure your blockchain monitor** to send POST requests to your server
3. **The system automatically:**
   - Extracts pool and mint addresses
   - Scrapes token information from CoinMarketCap and DexScreener
   - Analyzes creator wallet using Mobula API
   - Sends formatted alerts to Telegram

### Manual Testing

You can test the scraping functionality directly:

```python
from scrape import main

# Test with sample addresses
pool_address = "F86Rm73qaX7S38ZoocjzTZkLzQe6a1X575BcnjUtQzor"
mint_address = "2uhxAa6yag3zHtahLj4Cqn23fu9giheWj9c7DMwRjFvq"

main(pool_address, mint_address)
```

### Monitoring

- Check `scrape.log` for scraping activities
- Monitor Flask server logs for webhook requests
- Use `existing_urls.txt` to track processed tokens

## Troubleshooting

### Common Issues

1. **Chrome Driver Issues:**

   - Ensure Chrome is installed and up to date
   - Check Chrome profile path configuration
   - Try running in headless mode for server environments

2. **Telegram Connection Failed:**

   - Verify API credentials
   - Check chat ID format (negative for groups)
   - Ensure bot has permission to send messages

3. **Scraping Failures:**

   - CoinMarketCap/DexScreener may have changed their HTML structure
   - Update XPath selectors in `extract_info_from_cmc()`
   - Check for rate limiting or IP blocking

4. **Memory Issues:**
   - Close browser instances properly
   - Consider using headless mode
   - Restart the service periodically

### Debug Mode

Enable debug mode for detailed logging:

```python
# In server.py
app.run(debug=True)

# For scraping, add print statements or use logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Security Considerations

- **API Keys**: Never commit API keys to version control
- **Webhook Security**: Consider adding authentication to webhook endpoints
- **Rate Limiting**: Implement rate limiting for webhook endpoints
- **Input Validation**: Validate incoming webhook data
- **Error Handling**: Implement proper error handling and logging

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license information here]

## Support

For issues and questions:

- Check the troubleshooting section
- Review server and scraping logs
- Open an issue on the repository

---

**Note**: This system is designed for educational and research purposes. Ensure compliance with terms of service of all third-party APIs and websites used.
