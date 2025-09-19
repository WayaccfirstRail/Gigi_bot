import os
import threading
import datetime
import telebot
from telebot import types
from app import app, db
from models import *
from flask import jsonify
import logging
import socket
import ipaddress
import requests
import tempfile
from urllib.parse import urlparse
import mimetypes
from sqlalchemy import or_, and_

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot token and owner IDs from environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID', '0'))  # Set this in Replit Secrets

# Multiple owners system - will be initialized after environment validation

# Special logging function for @blahgigi_official detection
def log_special_user_detection(message):
    """Log when @blahgigi_official interacts with the bot to capture her user ID"""
    username = message.from_user.username or "No username"
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "No name"
    
    if username == "blahgigi_official":
        print(f"\n🎯 ===== @blahgigi_official DETECTED! =====")
        print(f"👤 USER ID: {user_id}")
        print(f"📧 First Name: {first_name}")
        print(f"🔑 Username: @{username}")
        print(f"🚨 ADD THIS ID TO OWNERS LIST: {user_id}")
        print(f"============================================\n")
        logger.info(f"OWNER ACCESS DETECTION: @blahgigi_official (ID: {user_id}) interacted with bot")
        
        # Also send notification to current owner
        try:
            if OWNER_ID != user_id:  # Don't send notification to herself
                bot.send_message(OWNER_ID, f"🎯 @blahgigi_official detected!\n\n👤 Name: {first_name}\n🆔 User ID: {user_id}\n🔑 Username: @{username}\n\n📋 Add this ID to OWNERS list for full access")
        except:
            pass
    
    return user_id

# Function to check if user is an owner
def is_owner(user_id):
    """Check if user_id is in the owners list"""
    return user_id in OWNERS

# For development/testing, check if we have the required credentials
missing_credentials = []
if not BOT_TOKEN:
    missing_credentials.append("BOT_TOKEN")
if OWNER_ID == 0:
    missing_credentials.append("OWNER_ID")

if missing_credentials:
    logger.error(f"Missing required environment variables: {', '.join(missing_credentials)}")
    logger.error("Please add these to your Replit Secrets or environment variables")
    logger.info("Starting in web-only mode - Flask server will run for health checks")
    
    # Set dummy values to prevent crashes when initializing bot
    if not BOT_TOKEN:
        BOT_TOKEN = "dummy_token_for_web_mode"
    if OWNER_ID == 0:
        OWNER_ID = 12345  # dummy ID

# Initialize OWNERS list after environment validation
OWNERS = [OWNER_ID]  # Will expand this list when we detect @blahgigi_official's ID

def notify_all_owners(message, parse_mode=None):
    """Send notification to all owners"""
    for owner_id in OWNERS:
        try:
            bot.send_message(owner_id, message, parse_mode=parse_mode)
        except:
            pass

# Initialize bot with proper token handling
if BOT_TOKEN and BOT_TOKEN != "dummy_token_for_web_mode":
    bot = telebot.TeleBot(BOT_TOKEN)
else:
    # Create a dummy bot object for web-only mode - need valid format
    bot = telebot.TeleBot("12345:DUMMY_TOKEN_FOR_WEB_MODE")

# Dictionary to store temporary upload data for guided content creation
upload_sessions = {}

# Dictionary to store notification composition sessions
notification_sessions = {}

def init_database():
    """Initialize database with default data"""
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Insert default AI responses
        default_responses = [
            ('greeting', 'Hey there! 😊 Thanks for reaching out! I love connecting with you baby. What\'s on your mind?'),
            ('question', 'That\'s a great question! I appreciate you asking. Feel free to check out my content or ask me anything else! 💕'),
            ('compliment', 'Aww, you\'re so sweet! Thank you! That really makes my day. You\'re amazing! ✨'),
            ('default', 'Thanks for the message! I love hearing from you. Don\'t forget to check out my exclusive content! 😘')
        ]
        
        for key, text in default_responses:
            existing = Response.query.filter_by(key=key).first()
            if not existing:
                response = Response()
                response.key = key
                response.text = text
                db.session.add(response)
        
        # Insert default VIP settings
        vip_settings = [
            ('vip_price_stars', '399'),
            ('vip_duration_days', '30'),
            ('vip_description', 'Premium VIP access with exclusive content and direct chat')
        ]
        
        for key, value in vip_settings:
            existing = VipSetting.query.filter_by(key=key).first()
            if not existing:
                setting = VipSetting()
                setting.key = key
                setting.value = value
                db.session.add(setting)
        
        db.session.commit()
        logger.info("Database initialized successfully")

def get_user_data(user_id):
    """Get user data from database"""
    return User.query.filter_by(user_id=user_id).first()

def add_or_update_user(user):
    """Add new user or update existing user data"""
    # SPECIAL DETECTION: Check for @blahgigi_official and log her ID
    if hasattr(user, 'username') and user.username == "blahgigi_official":
        print(f"\n🎯 ===== @blahgigi_official DETECTED! =====")
        print(f"👤 USER ID: {user.id}")
        print(f"📧 First Name: {user.first_name}")
        print(f"🔑 Username: @{user.username}")
        print(f"🚨 ADD THIS ID TO OWNERS LIST: {user.id}")
        print(f"============================================\n")
        logger.info(f"OWNER ACCESS DETECTION: @blahgigi_official (ID: {user.id}) interacted with bot")
        
        # AUTOMATICALLY add to OWNERS list if not already there
        if user.id not in OWNERS:
            OWNERS.append(user.id)
            print(f"✅ @blahgigi_official (ID: {user.id}) AUTOMATICALLY ADDED to OWNERS list!")
            logger.info(f"OWNER ADDED: @blahgigi_official (ID: {user.id}) added to OWNERS list automatically")
        
        # Notify all other owners
        try:
            for owner_id in OWNERS:
                if owner_id != user.id:  # Don't send notification to herself
                    try:
                        bot.send_message(owner_id, f"🎯 @blahgigi_official detected and granted owner access!\n\n👤 Name: {user.first_name}\n🆔 User ID: {user.id}\n🔑 Username: @{user.username}\n\n✅ Automatically added to OWNERS list")
                    except:
                        pass
        except:
            pass

    # Prevent owners from being registered as regular users
    if is_owner(user.id):
        return  # Don't register owners
    
    # Prevent bots from being registered as users
    if getattr(user, 'is_bot', False):
        return  # Don't register bot accounts
    
    # Prevent accounts with bot-like usernames from being registered
    if user.username and user.username.lower().endswith('bot'):
        return  # Don't register likely bot accounts
    
    # Prevent bot from registering itself as a user
    try:
        bot_info = bot.get_me()
        if user.id == bot_info.id:
            return  # Don't process bot's own messages
    except Exception as e:
        logger.warning(f"Could not get bot info: {e}")
        # Continue processing if we can't get bot info
    
    with app.app_context():
        # Check if user exists
        existing_user = User.query.filter_by(user_id=user.id).first()
        
        if existing_user:
            # Update interaction count and last interaction
            existing_user.interaction_count += 1
            existing_user.last_interaction = datetime.datetime.now()
            existing_user.username = user.username
            existing_user.first_name = user.first_name
        else:
            # Add new user
            new_user = User()
            new_user.user_id = user.id
            new_user.username = user.username
            new_user.first_name = user.first_name
            new_user.join_date = datetime.datetime.now()
            new_user.last_interaction = datetime.datetime.now()
            new_user.interaction_count = 1
            db.session.add(new_user)
            
            # Send welcome notification to all owners
            try:
                notify_all_owners(f"👋 New user started chatting!\n👤 {user.first_name} (@{user.username})\n🆔 ID: {user.id}")
            except:
                pass
        
        db.session.commit()

# Flask routes for web interface
@app.route('/')
def home():
    """Home page with health status"""
    return jsonify({
        "status": "running", 
        "message": "Content Bot Server is operational",
        "mode": "web-only" if BOT_TOKEN == "dummy_token_for_web_mode" else "full-bot",
        "database": "postgresql",
        "health": "OK"
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        # Test database connection
        with app.app_context():
            db.session.execute(db.text('SELECT 1'))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return jsonify({
        "status": "healthy",
        "database": db_status,
        "timestamp": datetime.datetime.now().isoformat()
    })

# Run bot functions (placeholder for now - will add bot handlers later if needed)
def run_bot():
    """Run the Telegram bot"""
    if BOT_TOKEN == "dummy_token_for_web_mode":
        logger.info("Bot running in dummy mode - no actual polling")
        return
    
    try:
        logger.info("Starting Telegram bot polling...")
        bot.infinity_polling()
    except Exception as e:
        logger.error(f"Bot polling error: {e}")
        logger.info("Flask server will continue running for health checks.")

def main():
    """Main function to initialize and start the bot"""
    logger.info("Initializing Content Creator Bot...")
    
    # Initialize database
    init_database()
    
    # Only start bot if we have valid credentials
    original_bot_token = os.getenv('BOT_TOKEN')
    original_owner_id = int(os.getenv('OWNER_ID', '0'))
    
    if original_bot_token and original_owner_id != 0:
        logger.info("Valid credentials found - starting bot polling...")
        # Start bot in a separate thread
        bot_thread = threading.Thread(target=run_bot)
        bot_thread.daemon = True
        bot_thread.start()
    else:
        logger.info("Missing bot credentials - running in web-only mode")
        logger.info("Add BOT_TOKEN and OWNER_ID to Replit Secrets to enable Telegram bot functionality")
    
    # Start Flask server
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting Flask server on 0.0.0.0:{port}...")
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    main()