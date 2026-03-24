# Slacktable

<!-- Test deployment with updated token -->

A Python-based Slack app that automatically sends tagged messages to multiple Airtable bases when users react with specific emojis, with intelligent routing and pain score classification.

## Overview

Slacktable monitors Slack channels for specific emoji reactions and automatically creates records in your Airtable table with the message content and metadata. Perfect for quickly collecting bug reports, feature requests, or any important messages from your team conversations with built-in priority classification.

## Features

- 🚚 React with `:fedex:` emoji to tag messages (legacy support)
- 🔢 Use `:one:`, `:two:`, `:three:` emojis to tag messages with Pain Score classification
- 🪵 React with `:changelog:` emoji to route messages to separate Changelog table
- 📊 **Pain Score Support**: Automatically categorizes issues by severity
  - `:one:` → Small (sm) pain score
  - `:two:` → Medium (md) pain score  
  - `:three:` → Large (lg) pain score
- 🗂️ **Multi-Base Routing**: Different emojis can route to different Airtable bases
- 🖼️ **Image Support**: Automatically captures up to 3 images per message
- 🧵 Works on both main messages and threaded replies
- 📝 Automatically extracts message text
- 🗃️ Creates records in Airtable table with Status = "Intake"
- 🔒 Secure token management via environment variables
- 📊 Comprehensive logging and error handling
- ⚡ Real-time Socket Mode connection to Slack
- 🚀 Easy deployment to Fly.io

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/Casey-00/Slacktable.git
   cd Slacktable
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your tokens (see Configuration section)
   ```

4. **Run locally with Socket Mode**
   ```bash
   python run_socket_mode.py
   ```

## Configuration

Create a `.env` file with the following variables:

```env
# Slack App Tokens
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token

# Airtable Configuration
AIRTABLE_API_TOKEN=your-airtable-token
AIRTABLE_BASE_ID=your-base-id-here
AIRTABLE_TABLE_NAME=your-table-name
AIRTABLE_FIELD_NAME=your-field-name

# App Configuration
# (No app-specific configuration is needed anymore as emoji mapping is in the code)
```

**Note**: Socket Mode doesn't require `SLACK_SIGNING_SECRET` - only the Bot Token and App-Level Token are needed.

## Deployment

This app is designed to run on [Fly.io](https://fly.io) which supports persistent connections required for Socket Mode.

For detailed deployment instructions, see [docs/deployment.md](docs/deployment.md).

### Quick Deploy

1. **Install Fly.io CLI** and authenticate
2. **Initialize your app**: `flyctl launch`
3. **Set secrets**: Use `flyctl secrets set` for all environment variables
4. **Deploy**: `flyctl deploy`

## Project Structure

```
Slacktable/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application (legacy)
│   ├── socket_mode.py       # Socket Mode handler
│   ├── config.py            # Configuration and environment variables
│   ├── slack/
│   │   ├── __init__.py
│   │   ├── client.py        # Slack client initialization
│   │   └── handlers.py      # Event handlers for reactions
│   ├── airtable/
│   │   ├── __init__.py
│   │   └── client.py        # Airtable client and operations
│   └── utils/
│       ├── __init__.py
│       └── logging.py       # Logging configuration
├── docs/
│   ├── slack-app-setup.md   # Slack app configuration guide
│   ├── airtable-setup.md    # Airtable setup instructions
│   └── deployment.md        # Deployment guide
├── tests/
│   └── test_handlers.py     # Unit tests
├── requirements.txt         # Python dependencies
├── run_socket_mode.py      # Socket Mode runner script
├── .env.example            # Environment variables template
└── README.md               # This file
```

## How It Works

1. **User tags a message** by reacting with one of the supported emojis:
   - `:fedex:` - Creates record without pain score (legacy)
   - `:one:` - Creates record with Pain Score = "sm" (small)
   - `:two:` - Creates record with Pain Score = "md" (medium)
   - `:three:` - Creates record with Pain Score = "lg" (large)
   - `:changelog:` - Routes to separate Changelog base without pain score
2. **Slack sends event** to your app via Socket Mode connection
3. **App processes the reaction** and extracts the original message
4. **Images are captured** automatically (up to 3 per message)
5. **Record created in Airtable** with:
   - Message text in your configured field
   - Status = "Intake"
   - Pain Score (if applicable)
   - Image URLs in "Slack Screenshot", "Slack Screenshot 2", "Slack Screenshot 3" fields
6. **Success/error logged** for monitoring

## Setup Guides

- [Slack App Setup](docs/slack-app-setup.md) - Step-by-step Slack app configuration
- [Airtable Setup](docs/airtable-setup.md) - Airtable API token and base setup
- [Deployment Guide](docs/deployment.md) - Fly.io deployment instructions

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

This project follows PEP 8 guidelines. Format code with:

```bash
black app/
```

### Logging

Logs are structured and include:
- Timestamp
- Log level
- Message
- Relevant context (user, channel, etc.)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues or questions:
1. Check the [docs](docs/) directory
2. Search existing [GitHub issues](https://github.com/Casey-00/Slacktable/issues)
3. Create a new issue if needed

---

**Note**: This app requires proper Slack app permissions and Airtable API access. See the setup guides in the `docs/` directory for detailed instructions.
