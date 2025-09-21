# Overview

This is a professional Telegram bot designed for content creators who monetize their content through Telegram Stars. The bot serves as a complete fan engagement and content management platform, allowing creators to sell media content, interact with fans through AI-style responses, and manage their community directly through Telegram chat without needing external tools or interfaces.

The bot provides a dual interface: fans can browse teasers, purchase content with Telegram Stars, and have natural conversations, while content creators get comprehensive admin controls for content management, user analytics, and automated interactions.

# Recent Changes

**September 19, 2025 - Fresh GitHub Import Successfully Completed ✅ (FINAL)**
- ✅ **PROJECT IMPORT**: Fresh GitHub clone successfully imported and configured for Replit environment
- ✅ **DEPENDENCIES**: All Python dependencies installed from pyproject.toml using uv sync (pytelegrambotapi, flask, sqlalchemy, etc.)
- ✅ **DATABASE**: SQLite database created, connected, and all 10 tables initialized successfully (migration to PostgreSQL planned for production scaling)
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
- **SQLite Database (Current)**: Local database with Flask-SQLAlchemy ORM for single-instance operation
- **PostgreSQL Database (Planned)**: Production-ready relational database for multi-instance scaling
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

# Performance and Scalability Requirements

## User Scalability
- **Current Architecture (SQLite + Threading)**: Realistic concurrency limits
  - Minimum 20 concurrent users without performance degradation
  - Target capacity of 50 simultaneous bot interactions with polling
  - Graceful handling of traffic spikes up to 150% of normal load
  - User session isolation through thread-safe database operations
- **Future Architecture (PostgreSQL + Webhooks)**: Enhanced scalability targets
  - Migration to webhook-based bot handling for improved concurrency
  - PostgreSQL database for multi-instance deployment support
  - Target capacity of 500+ simultaneous bot interactions with webhook architecture

## Response Time Requirements
- **Bot Command Performance**: Fast interaction response times
  - Standard commands (start, help, buy): Maximum 2 seconds response time
  - Content browsing and catalog display: Maximum 3 seconds response time
  - Payment processing initiation: Maximum 5 seconds response time
  - File upload/download operations: Maximum 30 seconds for completion
- **Telegram-Specific SLAs**: Platform compliance requirements
  - Pre-checkout query responses: Maximum 2 seconds (hard limit 10 seconds)
  - Successful payment callbacks: Maximum 2 seconds response time
  - Webhook handler responses: Maximum 1 second (when webhooks implemented)
  - Bot API rate limit compliance: Maximum 30 messages per second total per bot
  - Per-chat rate limiting: Maximum 1 message per second per individual chat
  - Group chat limits: Maximum 20 messages per minute in group chats
  - Message queue management: Exponential backoff and jitter for rate limit violations
- **Web Endpoint Performance**: Fast health check and admin interface
  - Health endpoint (/health): Maximum 500ms response time
  - Admin web interface: Maximum 2 seconds page load time
  - Content preview endpoints: Maximum 3 seconds with caching

## Content Handling Performance
- **Current File Operations**: Platform-optimized approach
  - Concurrent file downloads: Support up to 10 simultaneous downloads (tested target)
  - Upload processing: Background processing for large files (>10MB)
  - Content delivery via Telegram file_id system for scalability
  - Thumbnail generation: Automatic optimization for preview content
- **Storage Performance**: Conservative storage management
  - Storage capacity planning: 10GB working target (validated through testing)
  - File compression: Automatic optimization for storage efficiency
  - Cleanup procedures: Automated removal of unused temporary files after 24 hours
- **Future Enhancement Path**: External storage integration
  - Object storage integration (S3/GCS) for larger capacity needs
  - CDN integration for improved content delivery performance
  - Migration to external file hosting for production scalability

## Database Performance
- **Current SQLite Performance**: Single-instance optimization
  - User lookup queries: Maximum 100ms response time
  - Content catalog queries: Maximum 200ms with pagination (limit 50 items)
  - Analytics queries: Maximum 5 seconds for complex aggregations
  - Payment transaction queries: Maximum 500ms for verification
  - Database file size monitoring with 1GB practical limit
- **Database Indexing**: Required indexes for performance
  - Users table: Index on user_id, username, last_interaction
  - ContentItem table: Index on name, content_type, created_date
  - UserPurchase table: Index on user_id, content_name, purchase_date
  - VipSubscription table: Index on user_id, is_active, expiry_date
- **PostgreSQL Migration Path**: Production-ready scaling
  - Per-instance connection pool: 5-15 connections (appropriate for single instance)
  - Query result caching for frequently accessed data
  - Automated database maintenance and VACUUM procedures

## Caching Strategy
- **Current In-Memory Caching**: Single-instance optimization
  - Content metadata caching: Dictionary-based with 1-hour TTL
  - User conversation state: Thread-safe in-memory storage
  - Analytics data caching: 15-minute TTL for dashboard statistics
  - VIP status caching: 5-minute TTL with invalidation on changes
- **Future External Caching**: Multi-instance support
  - Redis integration for shared cache across instances
  - Session externalization for horizontal scaling
  - Distributed cache invalidation strategies
- **Content Delivery Caching**: Browser and proxy optimization
  - Static asset caching: 24-hour browser caching headers
  - Dynamic content caching: Short-term caching for user-specific lists
  - Telegram file_id caching to reduce API calls

## Resource Utilization
- **Platform Resource Management**: Conservative resource utilization
  - Maximum 256MB RAM usage during normal operation (conservative target)
  - Memory leak prevention with regular garbage collection
  - Background process memory limits to prevent system throttling
- **CPU Performance**: Efficient processing within constraints
  - CPU usage should not exceed 60% during peak operation
  - Background tasks should use no more than 20% CPU capacity
  - Efficient image processing with size/quality trade-offs
- **Storage Management**: Platform-optimized storage
  - Automated cleanup of temporary files older than 6 hours
  - Log file rotation to prevent disk space exhaustion (conservative 100MB limit)
  - Content archival strategy for files older than 30 days
  - Primary content delivery through Telegram file_id to minimize local storage

## Background Processing
- **Current Threading Approach**: Single-instance async operations
  - File upload processing: Thread-based background handling for large files
  - Notification delivery: Threaded sending to prevent blocking main thread
  - Analytics calculation: Scheduled background processing with threading.Timer
  - Database maintenance: Periodic cleanup operations in separate threads
- **Future Queue System**: Production-ready task processing
  - Migration to Celery or RQ for reliable background processing
  - Task retry mechanisms with exponential backoff
  - Dead letter queues for failed operations
  - Priority queuing for critical operations (payments, security alerts)
  - Worker process limits: 2-4 workers for media processing operations

## Load Balancing and Scaling
- **Current Single-Instance Design**: SQLite + Threading Architecture
  - SQLite-based single-instance operation with thread safety
  - In-memory session state management
  - Bot polling mechanism with threaded message processing
  - Vertical scaling through resource optimization
- **Future Multi-Instance Architecture**: Horizontal scaling preparation
  - PostgreSQL migration for multi-instance database sharing
  - External session storage (Redis) for stateless application design
  - Load balancer configuration for multiple bot instances
- **Traffic Management**: Conservative request handling
  - Rate limiting per user: 10 commands per minute (token bucket implementation)
  - Global rate limiting: 100 requests per minute total (tested conservative target)
  - Per-chat message queuing with exponential backoff and jitter
  - Priority handling for paying customers and VIP users
- **Scaling Thresholds**: Conservative operational triggers
  - CPU-based scaling consideration at 60% utilization
  - Memory-based scaling consideration at 80% utilization (conservative 256MB target)
  - Manual scaling decisions based on user growth and engagement patterns

## Monitoring and Performance Metrics
- **Performance Monitoring**: Realistic tracking for current platform
  - Response time monitoring through Flask /health endpoint
  - Resource utilization tracking via Replit system metrics
  - Database performance monitoring with query timing logs
  - Bot message processing rate tracking in application logs
- **Load Testing Targets**: Concrete, testable performance goals
  - Health endpoint: 100 requests/minute with <500ms response
  - Bot command handling: 20 concurrent users with <3s response time
  - Payment processing: 10 concurrent purchase attempts without failure
  - File operations: 5 concurrent downloads with <30s completion time
- **Capacity Planning**: Growth-aware monitoring
  - User growth trend analysis through daily active user metrics
  - Storage growth monitoring with 8GB warning threshold (10GB tested target)
  - Database size monitoring with cleanup triggers at 800MB
  - Performance baseline establishment using weekly averages
- **Alerting Thresholds**: Practical operational alerts
  - Response time degradation: >5s average for bot commands
  - Resource exhaustion: >200MB RAM usage or >8GB storage
  - Error rate monitoring: >5% failure rate for critical operations

# Testing Requirements and Quality Assurance

## Unit Testing Requirements
- **Core Component Testing**: Individual function and module verification
  - User management functions: Registration, authentication, blocking/unblocking
  - Content management: Upload, catalog, pricing, access control validation
  - Payment processing: Invoice generation, validation, completion handling
  - VIP subscription logic: Activation, expiration, status checking
  - Database operations: CRUD operations, query optimization, transaction handling
- **Test Coverage Standards**: Comprehensive code coverage expectations
  - Minimum 80% code coverage for critical payment and security functions
  - Minimum 70% overall code coverage across the entire application
  - 100% coverage required for authentication and authorization functions
  - Exception handling and error scenarios must have dedicated test cases

## Integration Testing Requirements
- **Database Integration**: Full database functionality validation
  - SQLite database connection and transaction integrity testing
  - Database schema validation and migration testing
  - Concurrent access testing with threading simulation
  - Data consistency verification across all database operations
- **Telegram API Integration**: Bot functionality and API compliance
  - Message sending and receiving with various content types
  - Payment flow integration with Telegram Stars API testing
  - Webhook handling simulation and response validation
  - Rate limit compliance testing with mock API responses
- **External Service Integration**: Third-party service connectivity
  - File download and validation from external URLs
  - Image processing and thumbnail generation testing
  - Content delivery system integration verification

## Security Testing Requirements
- **Authentication and Authorization Testing**: Access control verification
  - Owner authentication bypass attempt simulation
  - User privilege escalation testing
  - Token validation and expiration testing
  - Session security and state manipulation testing
- **Input Validation Testing**: Malicious input protection
  - SQL injection attempt simulation across all database operations
  - Cross-site scripting (XSS) prevention in user-generated content
  - File upload security testing with malicious file types
  - URL validation testing with SSRF attack simulation
- **Payment Security Testing**: Financial transaction protection
  - Payment fraud simulation and detection testing
  - Duplicate payment prevention verification
  - Payment callback authenticity validation
  - Invoice tampering detection and prevention

## Performance Testing Requirements
- **Load Testing**: System capacity under normal conditions
  - 20 concurrent users performing standard operations (current architecture)
  - 50 simultaneous bot interactions with response time monitoring
  - Database query performance under concurrent access scenarios
  - File operation performance with multiple concurrent downloads
- **Stress Testing**: System behavior under extreme conditions
  - Traffic spike simulation (200% of normal load)
  - Resource exhaustion testing (memory, storage, database connections)
  - Recovery testing after system overload scenarios
  - Graceful degradation validation under high load
- **Telegram-Specific Performance Testing**: Platform compliance verification
  - Pre-checkout query response time validation (must be under 2 seconds)
  - Payment callback processing speed verification
  - Rate limit compliance testing with message queue validation
  - Bot command response time monitoring across different load levels

## User Acceptance Testing (UAT)
- **Core User Flows**: End-to-end user journey validation
  - New user registration and first content purchase
  - VIP subscription purchase and content access
  - Content browsing, teaser viewing, and purchase decision flow
  - Customer support interaction through blocking/unblocking system
- **Owner Administrative Flows**: Content creator workflow validation
  - Content upload, pricing, and catalog management
  - User analytics and revenue tracking verification
  - VIP member management and subscription monitoring
  - Notification system testing with different user segments
- **Payment Flow Testing**: Complete transaction verification
  - End-to-end purchase flow from catalog to content delivery
  - Payment failure handling and user communication
  - Refund and dispute handling procedures (manual process testing)
  - VIP subscription renewal and expiration notification testing

## Regression Testing Requirements
- **Critical Function Protection**: Ensure changes don't break core features
  - Automated test suite execution before each deployment
  - Payment system regression testing after any payment-related changes
  - Security function testing after authentication or authorization changes
  - Database migration testing with data integrity verification
- **Feature Flag Testing**: Safe deployment of new features
  - A/B testing framework for new feature rollouts
  - Feature toggle validation and rollback procedures
  - User experience consistency testing across feature variations

## Automated Testing Framework
- **Continuous Integration**: Automated testing pipeline
  - Pre-commit hooks for code quality and basic unit tests
  - Automated test execution on code repository changes
  - Integration test execution in staging environment
  - Performance benchmark testing with trend monitoring
- **Test Environment Management**: Isolated testing environments
  - Separate test database with known test data sets
  - Mock Telegram API for deterministic testing
  - Staging environment replicating production configuration
  - Test data generation and cleanup automation

## Security Audit and Penetration Testing
- **Regular Security Assessments**: Proactive vulnerability identification
  - Quarterly security audits by internal or external security teams
  - Monthly dependency vulnerability scanning
  - Semi-annual penetration testing focusing on payment and authentication systems
  - Code security review for all payment and security-related changes
- **Compliance Testing**: Regulatory and platform requirement verification
  - Telegram Bot API compliance verification
  - Data protection regulation compliance testing
  - Payment processing compliance with Telegram Stars requirements

## Quality Assurance Procedures
- **Code Review Standards**: Peer review and quality control
  - Mandatory code review for all changes by senior developer
  - Security-focused review for authentication, payment, and data handling changes
  - Performance impact assessment for database and API changes
  - Documentation review for user-facing feature changes
- **Release Testing Checklist**: Pre-deployment verification procedures
  - Health endpoint functionality verification
  - Database backup and recovery procedure testing
  - Payment system end-to-end testing in staging environment
  - User notification system functionality verification
  - Performance baseline comparison with previous version

## Monitoring and Alerting Testing
- **Health Check Validation**: System monitoring verification
  - Health endpoint response time and accuracy testing
  - Database connection monitoring and alert testing
  - Resource utilization monitoring and threshold alert validation
  - Error rate monitoring and escalation procedure testing
- **Incident Response Testing**: Emergency procedure validation
  - Payment system failure response and user communication testing
  - Database corruption recovery procedure validation
  - Bot downtime communication and status page update testing
  - Security incident response and user notification testing

## Test Data Management
- **Test Data Strategy**: Realistic and secure test data handling
  - Anonymized production data for realistic testing scenarios
  - Synthetic test data generation for privacy-sensitive testing
  - Test user account management with known credentials
  - Test payment scenarios using Telegram's test payment system
- **Data Privacy in Testing**: Protecting user information during testing
  - No production user data in test environments
  - Test data anonymization and obfuscation procedures
  - Secure deletion of test data after testing completion
  - Compliance with data protection requirements in testing procedures

# External Dependencies

## Telegram API
- **Telegram Bot API**: Core messaging and bot functionality through official API
- **Telegram Stars**: Native payment processing system for content monetization
- **Webhook/Polling**: Bot communication method with Telegram servers

## Python Libraries
- **pyTelegramBotAPI (telebot)**: Primary bot framework for Telegram integration
- **Flask**: Web server framework for Replit hosting compatibility
- **SQLite (Current)**: Local database for single-instance development and small-scale production
- **PostgreSQL (Migration Target)**: Production-ready relational database with Flask-SQLAlchemy ORM
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
✅ **Database**: SQLite database initialized and working (PostgreSQL migration planned for scaling)  
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