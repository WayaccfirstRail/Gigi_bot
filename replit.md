# Overview

This is a professional Telegram bot designed for content creators who monetize their content through Telegram Stars. The bot serves as a complete fan engagement and content management platform, allowing creators to sell media content, interact with fans through AI-style responses, and manage their community directly through Telegram chat without needing external tools or interfaces.

The bot provides a dual interface: fans can browse teasers, purchase content with Telegram Stars, and have natural conversations, while content creators get comprehensive admin controls for content management, user analytics, and automated interactions.

# Recent Changes

**September 19, 2025 - Fresh GitHub Import Successfully Completed ✅ (FINAL)**
- ✅ **PROJECT IMPORT**: Fresh GitHub clone successfully imported and configured for Replit environment
- ✅ **DEPENDENCIES**: All Python dependencies installed from pyproject.toml using uv sync (pytelegrambotapi, flask, sqlalchemy, etc.)
- ✅ **DATABASE**: PostgreSQL database created, connected, and all 10 tables initialized successfully
  - Tables: users, content_items, user_purchases, vip_subscriptions, vip_settings, responses, scheduled_posts, teasers, loyal_fans, user_backups
  - Database connection verified and all tables created automatically
- ✅ **WEB SERVER**: Flask application running on 0.0.0.0:5000 with webview output for user preview
- ✅ **WORKFLOW**: "Flask Web Server" workflow properly configured with webview output type and port 5000
- ✅ **ENDPOINTS**: Both homepage (/) and health (/health) endpoints working and tested (HTTP 200)
  - Health endpoint returns JSON: {"bot_mode":"web-only","database":"connected","status":"healthy","user_count":0}
  - Homepage displays professional HTML interface for Content Creator Bot with setup instructions
- ✅ **DEPLOYMENT**: Production deployment configured for VM target for persistent bot operation (required for Telegram bot)
- ✅ **BOT FUNCTIONALITY**: Bot is fully operational in web-only mode and ready for Telegram credentials
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

# Security Requirements

## Authentication and Authorization
- **Owner Authentication**: Multi-layer verification using OWNER_ID environment variable
  - Owner commands protected by `is_owner()` validation checks
  - Automatic detection and tracking of authorized content creator accounts
  - Prevention of privilege escalation through user ID verification

## Content Access Security  
- **Secure Content Tokens**: HMAC-SHA256 token generation for content preview access
  - Dedicated HMAC secret separate from bot token for better security isolation
  - Short-lived token expiration (1-hour maximum) with nonce validation
  - One-time use tokens with replay attack prevention
  - Content name, timestamp, user_id, chat_id, and cryptographic nonce inclusion
  - User binding: tokens only valid for the specific purchaser's Telegram user_id
  - Content sharing prevention through user-specific token generation
- **Content Preview Protection**: Owner-only access to content preview endpoints
  - Token validation on all content access attempts with timing attack protection
  - Logging of unauthorized access attempts with anonymized IP tracking
  - Automatic access denial for invalid, expired, or reused tokens
  - Rate limiting on content preview endpoints to prevent abuse

## Payment Security
- **Telegram Stars Integration**: Leverages Telegram's native payment security
  - No direct credit card processing or sensitive financial data storage
  - Payment verification through Telegram's secure pre-checkout system
  - Webhook authenticity verification using X-Telegram-Bot-Api-Secret-Token
  - IP allowlisting for Telegram webhook endpoints (149.154.160.0/20, 91.108.4.0/22)
  - Pre-checkout price and currency validation against content catalog
  - Automatic content delivery only after successful payment confirmation
- **Purchase Validation**: Multi-step verification for all content purchases
  - Idempotency keys for all purchase transactions to prevent duplicate charges
  - Idempotency state storage in database with 24-hour TTL
  - User ownership verification before content delivery
  - Purchase transaction logging with fraud detection patterns
  - VIP subscription status validation for exclusive content access
  - Payment replay attack prevention with transaction deduplication
- **Fraud Prevention**: Anti-abuse controls for payment processing
  - Rate limiting on purchase attempts per user
  - Monitoring for suspicious payment patterns
  - Automatic blocking of users exhibiting fraudulent behavior

## User Data Protection
- **User Blocking System**: Protection against malicious or inappropriate users
  - Owner-controlled user blocking with reason tracking
  - Blocked user prevention from accessing bot features
  - Automatic blocking detection on all command handlers
- **Data Sanitization**: HTML entity escaping for all user-generated content
  - Safe rendering of usernames, descriptions, and messages
  - Prevention of XSS attacks through proper escaping
  - Safe handling of special characters in user input

## Input Validation and Sanitization
- **URL Security Validation**: SSRF protection for external content downloads
  - URL format validation with proper parsing
  - Security checks for malicious URLs and local network access prevention
  - File type and size validation for downloaded content
- **Content Upload Security**: Secure handling of user-uploaded media
  - File type validation and content-type verification
  - Size limitations to prevent storage abuse
  - Safe file naming and path handling

## Transport and Storage Security
- **Encryption in Transit**: Secure communication protocols
  - HTTPS enforced with HSTS headers for all web endpoints
  - TLS 1.2+ for all external API communications
  - Secure WebSocket connections for real-time features (if implemented)
- **Encryption at Rest**: Data protection in storage
  - Database encryption using platform disk encryption or SQLCipher for SQLite
  - Encrypted backups with separate key management and secure key storage
  - Secure file storage with appropriate permissions (644 for files, 755 for directories)
  - Database connection encryption for PostgreSQL production deployments

## Environment and Secrets Management
- **Secure Configuration**: Environment-based secret management
  - BOT_TOKEN and OWNER_ID stored in Replit Secrets
  - Dedicated HMAC signing keys separate from bot tokens
  - No hardcoded credentials in source code
  - Graceful degradation when credentials are missing
- **Secret Rotation**: Regular credential updates
  - Quarterly bot token rotation procedures
  - Monthly HMAC key rotation with backward compatibility
  - Automated secret expiration monitoring
- **Production Security**: Separation of development and production environments
  - Database isolation between development and production
  - Secure deployment configuration for production use
  - Environment-specific configuration validation

## Error Handling and Information Disclosure
- **Safe Error Messages**: User-friendly error messages without sensitive information
  - Generic error responses that don't reveal system details
  - Detailed error logging for administrators without user exposure
  - Graceful handling of all exception scenarios

## Rate Limiting and Abuse Prevention
- **Command Rate Limiting**: Protection against spam and abuse
  - Per-user command throttling (10 commands per minute)
  - Global rate limiting on expensive operations (content uploads, payments)
  - Progressive backoff for repeated violations
- **Resource Protection**: Bandwidth and storage abuse prevention
  - File download size limits (50MB maximum)
  - Daily bandwidth limits per user for content access
  - Storage quota enforcement for uploaded content
- **Anti-DoS Measures**: System availability protection
  - Request rate limiting on Flask endpoints
  - Connection limits and timeout configurations
  - Automated temporary bans for excessive requests

## Enhanced Administrative Security
- **Role-Based Access Control**: Granular permission system
  - Multiple admin levels with specific permissions
  - Admin action auditing with full command logging
  - Separate admin authentication for sensitive operations
- **Admin Operation Constraints**: Security boundaries for administrators
  - Restriction of admin commands to private chats only
  - Multi-factor verification for destructive operations
  - Admin session timeout and re-authentication requirements
- **Admin Monitoring**: Oversight of administrative activities
  - Real-time alerts for admin actions
  - Admin behavior pattern analysis
  - Separation of duties for critical operations

## Session and State Management  
- **Secure Conversation State**: Safe management of user interaction states
  - Conversation state validation and cleanup
  - Prevention of state manipulation or injection attacks
  - Automatic conversation state expiration (24 hours)
  - Secure storage of temporary user data during multi-step processes

## Media Storage Security
- **File Storage Hardening**: Secure handling of uploaded media content
  - OS-level file permissions enforcement (644 for files, 755 for directories)
  - Path traversal attack prevention with input sanitization
  - File quarantine and malware scanning for uploads (when accepting user uploads)
  - Secure temporary file handling with automatic cleanup
- **Content Delivery Security**: Protected access to stored media
  - Hotlink prevention for delivered content
  - Expiring signed URLs for content access (maximum 24 hours)
  - Content type validation to prevent executable file distribution
  - Watermarking and digital rights management for premium content

## Privacy and Compliance
- **Data Protection**: User privacy and regulatory compliance
  - Data retention policies with automatic deletion after 2 years of inactivity
  - Secure data deletion procedures for user account removal
  - Purpose limitation for collected data (monetization platform only)
  - User consent mechanisms for data collection and processing
- **Privacy-Preserving Logging**: Minimal data exposure in logs
  - IP address anonymization (last octet masking) in security logs
  - PII redaction from error messages and debug information
  - Log retention limits (maximum 90 days for security logs)
  - Separate audit trail for admin actions with extended retention (1 year)
- **User Rights**: Data subject rights implementation
  - User data export capabilities for transparency
  - Right to deletion implementation with complete data removal
  - Data portability features for user content

## Vulnerability Management
- **Dependency Security**: Third-party component safety
  - Dependency version pinning with security update monitoring
  - Monthly security vulnerability scanning of dependencies
  - Automated alerts for critical security updates (CVSS 7.0+)
  - Regular dependency updates with testing procedures
- **Security Update Process**: Systematic security maintenance
  - Quarterly security assessments and penetration testing
  - CVE response procedures with 48-hour critical patch timeline
  - Security incident response plan with escalation procedures
  - Regular security training for administrators
- **Code Security**: Application-level protection
  - Static code analysis for security vulnerabilities
  - Input validation and output encoding standards
  - Regular security code reviews for sensitive components

## Monitoring and Logging Security
- **Security Event Logging**: Comprehensive logging of security-relevant events
  - Failed authentication attempts and access violations
  - Unusual user behavior patterns and potential abuse
  - System health and security status monitoring
  - Real-time alerting for critical security events
- **Log Data Protection**: Secure handling of log information
  - Encrypted log storage with secure access controls
  - Log integrity verification with checksums
  - Proper log rotation and retention policies
  - Centralized logging with tamper-evident storage
  - Automatic redaction of secrets, tokens, and signed URLs from all log files
  - Sensitive data masking in error messages and debug information

# External Dependencies

## Telegram API
- **Telegram Bot API**: Core messaging and bot functionality through official API
- **Telegram Stars**: Native payment processing system for content monetization
- **Webhook/Polling**: Bot communication method with Telegram servers

## Python Libraries
- **pyTelegramBotAPI (telebot)**: Primary bot framework for Telegram integration
- **Flask**: Web server framework for Replit hosting compatibility
- **PostgreSQL**: Production-ready relational database with Flask-SQLAlchemy ORM
- **threading**: Standard library for concurrent operation management
- **datetime**: Time handling for scheduling and analytics
- **logging**: Error tracking and debugging information
- **os**: Environment variable access for secure configuration
- **hmac/hashlib**: Cryptographic libraries for secure token generation

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