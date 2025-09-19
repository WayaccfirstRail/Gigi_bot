# Overview

This is a professional Telegram bot designed for content creators who monetize their content through Telegram Stars. The bot serves as a complete fan engagement and content management platform, allowing creators to sell media content, interact with fans through AI-style responses, and manage their community directly through Telegram chat without needing external tools or interfaces.

The bot provides a dual interface: fans can browse teasers, purchase content with Telegram Stars, and have natural conversations, while content creators get comprehensive admin controls for content management, user analytics, and automated interactions.

# Recent Changes

**September 19, 2025 - Fresh GitHub Import Successfully Completed ✅ (FINAL)**
- ✅ **PROJECT IMPORT**: Fresh GitHub clone successfully imported and configured for Replit environment
- ✅ **DEPENDENCIES**: All Python dependencies installed from pyproject.toml using uv sync (pytelegrambotapi, flask, sqlalchemy, etc.)
- ✅ **DATABASE**: PostgreSQL database created, connected, and all 10 tables initialized successfully
  - Tables: users, content_items, user_purchases, vip_subscriptions, vip_settings, responses, scheduled_posts, teasers, loyal_fans, user_backups
  - Database connection verified with execute_sql_tool
- ✅ **WEB SERVER**: Flask application running on 0.0.0.0:5000 with webview output for user preview
- ✅ **WORKFLOW**: "Flask Web Server" workflow properly configured with webview output type and port 5000
- ✅ **ENDPOINTS**: Both homepage (/) and health (/health) endpoints working and tested (HTTP 200)
  - Health endpoint returns JSON: {"bot_mode":"web-only","database":"connected","status":"healthy","user_count":0}
- ✅ **DEPLOYMENT**: Production deployment configured for VM target for persistent bot operation (required for Telegram bot)
- ✅ **BOT FUNCTIONALITY**: Bot is fully operational and ready for Telegram credentials (running in web-only mode)
- ✅ **TESTING**: All endpoints tested and verified working with proper JSON/HTML responses
- ✅ **IMPORT COMPLETE**: Project fully operational in Replit environment with fresh setup - September 19, 2025
- ⚠️ **OPTIONAL**: Add BOT_TOKEN and OWNER_ID to Replit Secrets for full Telegram bot functionality

**Previous Import History**
- September 18, 2025 - Complete Replit Environment Setup  
- September 17, 2025 - Initial Replit Environment Setup

**September 18, 2025 - Complete Replit Environment Setup**
- ✅ Successfully configured Flask web server to run on 0.0.0.0:5000 with webview output
- ✅ Database initialization working properly with SQLite (content_bot.db) - existing data preserved
- ✅ Health endpoints working at / and /health for monitoring
- ✅ Production deployment configured with Gunicorn for VM target to maintain persistent operation
- ✅ Web-only mode implemented - Flask server runs even without Telegram credentials
- ✅ Error handling improved for graceful degradation when bot tokens are missing
- ⚠️ **REQUIRED SETUP**: Add BOT_TOKEN and OWNER_ID to Replit Secrets to enable full Telegram bot functionality

**September 17, 2025 - Initial Replit Environment Setup**
- Successfully configured the Telegram bot to run in Replit environment
- Set up required secrets: BOT_TOKEN and OWNER_ID through Replit Secrets
- Bot polling and Flask server running concurrently via threading

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Bot Framework and Hosting
- **pyTelegramBotAPI (telebot)**: Core bot framework for handling Telegram API interactions
- **Flask**: Minimal web server to maintain bot presence on Replit hosting platform
- **Threading**: Separates Flask server and bot polling to ensure continuous operation
- **Environment Variables**: Secure storage of BOT_TOKEN and OWNER_ID through Replit Secrets

## Data Layer
- **PostgreSQL Database**: Production-ready relational database with Flask-SQLAlchemy ORM
- **Database Schema Design**:
  - Users table: Tracks fan demographics, spending history, and engagement metrics
  - Content items table: Stores purchasable content with pricing and file references
  - Responses table: Key-value store for AI-style conversational responses
  - Scheduled posts table: Time-based content delivery system
  - Loyal fans table: Creator-defined fan recognition system

## Payment Processing
- **Telegram Stars Integration**: Native Telegram cryptocurrency for seamless in-chat transactions
- **Invoice Generation**: Automated billing system with `bot.send_invoice` using XTR currency
- **Payment Workflow**: Handles pre-checkout validation and successful payment processing
- **Automatic Content Delivery**: Post-payment content distribution with user statistics updates

## User Interface Design
- **Command-Based Interaction**: Structured commands for specific actions (/start, /buy, /teaser)
- **Inline Keyboard Buttons**: Visual interface elements for common actions
- **Natural Language Fallback**: AI-style responses for conversational messages outside command structure
- **Dual Permission System**: Separate command sets for regular users and content creator (owner)

## Content Management System
- **In-Chat Administration**: Complete bot management through Telegram messages, eliminating need for external interfaces
- **Dynamic Content Addition**: Real-time content catalog updates without code modifications
- **File Handling**: Support for various media types through file paths or URLs
- **Scheduled Publishing**: Time-based content release system with datetime parsing

## Analytics and User Management
- **User Activity Tracking**: Comprehensive interaction logging and spending analysis
- **Loyalty System**: Creator-defined fan recognition with custom tagging
- **User Lifecycle Management**: User deletion and recovery with backup functionality
- **Engagement Analytics**: Stars earned tracking, top fan identification, and interaction metrics

# External Dependencies

## Telegram API
- **Telegram Bot API**: Core messaging and bot functionality through official API
- **Telegram Stars**: Native payment processing system for content monetization
- **Webhook/Polling**: Bot communication method with Telegram servers

## Python Libraries
- **pyTelegramBotAPI (telebot)**: Primary bot framework for Telegram integration
- **Flask**: Web server framework for Replit hosting compatibility
- **sqlite3**: Built-in Python library for database operations
- **threading**: Standard library for concurrent operation management
- **datetime**: Time handling for scheduling and analytics
- **logging**: Error tracking and debugging information
- **os**: Environment variable access for secure configuration

## Hosting Platform
- **Replit**: Cloud hosting platform with integrated environment variable management
- **Replit Secrets**: Secure storage system for sensitive configuration data (BOT_TOKEN, OWNER_ID)

## File Storage
- **Local File System**: Media content storage on hosting platform
- **URL References**: Support for external content hosting through direct links

# Setup Instructions

## Current Status
✅ **Web Server**: Ready and running - the Flask application is operational  
✅ **Database**: SQLite database initialized and working  
✅ **Deployment**: Configured for production with Gunicorn  
⚠️ **Telegram Bot**: Requires credentials to be fully functional  

## To Enable Full Telegram Bot Functionality

The application is currently running in **web-only mode**. To enable the complete Telegram bot features, you need to:

### 1. Create a Telegram Bot
- Message @BotFather on Telegram
- Use the `/newbot` command
- Follow the instructions to get your **BOT_TOKEN**

### 2. Get Your Telegram User ID
- Message @userinfobot on Telegram to get your **OWNER_ID** (your Telegram user ID number)

### 3. Add Secrets in Replit
- Go to the "Secrets" tab in your Replit environment (lock icon in sidebar)
- Add these secrets:
  - `BOT_TOKEN`: Your bot token from BotFather
  - `OWNER_ID`: Your Telegram user ID number

### 4. Restart the Application
Once you've added the secrets, the application will automatically restart and detect the new credentials.

## Current Functionality Without Bot Credentials
- ✅ Web server health monitoring at `/` and `/health` endpoints
- ✅ Database operations and content management system
- ✅ All backend logic and data structures
- ❌ Telegram bot commands and messaging (requires credentials)