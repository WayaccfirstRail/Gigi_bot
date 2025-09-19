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

# Helper functions for VIP and content access control
def is_vip_active(user_id):
    """Check if user has active VIP subscription"""
    with app.app_context():
        vip = VipSubscription.query.filter_by(user_id=user_id, is_active=True).first()
        if not vip:
            return False
        # Check if subscription is expired
        return vip.expiry_date > datetime.datetime.now()

def check_user_owns_content(user_id, content_name):
    """Check if user has purchased specific content"""
    with app.app_context():
        purchase = UserPurchase.query.filter_by(user_id=user_id, content_name=content_name).first()
        return purchase is not None

def get_vip_price():
    """Get VIP subscription price from settings"""
    with app.app_context():
        setting = VipSetting.query.filter_by(key='vip_price_stars').first()
        return int(setting.value) if setting else 399

def get_vip_duration():
    """Get VIP subscription duration from settings"""
    with app.app_context():
        setting = VipSetting.query.filter_by(key='vip_duration_days').first()
        return int(setting.value) if setting else 30

# Bot command handlers
@bot.message_handler(commands=['start'])
def start_command(message):
    """Handle /start command"""
    user = message.from_user
    add_or_update_user(user)
    
    welcome_text = f"""
👋 Hey {user.first_name}! Welcome to my exclusive content bot!

🌟 Here's what you can do:
• 🎬 /teaser - View free preview content
• 💎 /vip_access - Get VIP subscription for exclusive content
• 🛒 /browse - Browse purchasable content
• ❓ /help - See all available commands

💕 I love connecting with my fans! Feel free to chat with me anytime.

✨ Ready to explore? Start with /teaser to see what I'm all about!
"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎬 View Teasers", callback_data="teasers"))
    markup.add(types.InlineKeyboardButton("💎 VIP Access", callback_data="vip_access"))
    markup.add(types.InlineKeyboardButton("🛒 Browse Content", callback_data="browse_content"))
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

@bot.message_handler(commands=['vip_access'])
def vip_access_command(message):
    """Handle VIP subscription access"""
    user_id = message.from_user.id
    
    # Check if user already has active VIP
    if is_vip_active(user_id):
        with app.app_context():
            vip = VipSubscription.query.filter_by(user_id=user_id).first()
            expiry_str = vip.expiry_date.strftime("%Y-%m-%d") if vip else "Unknown"
        
        vip_text = f"""
💎 <b>VIP STATUS: ACTIVE</b> ✅

🗓 <b>Expires:</b> {expiry_str}
🎬 <b>Access:</b> All exclusive VIP content
💬 <b>Priority:</b> Direct chat access

🔥 <b>Enjoy your VIP benefits!</b>
"""
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🎬 VIP Content", callback_data="vip_content"))
        bot.send_message(message.chat.id, vip_text, reply_markup=markup, parse_mode='HTML')
        return
    
    # Show VIP subscription options
    vip_price = get_vip_price()
    vip_duration = get_vip_duration()
    
    vip_text = f"""
💎 <b>VIP MEMBERSHIP AVAILABLE</b>

🌟 <b>Price:</b> {vip_price} Telegram Stars
⏰ <b>Duration:</b> {vip_duration} days
🎁 <b>Benefits:</b>
  • Exclusive VIP-only content
  • Priority direct chat access
  • Special VIP teasers
  • Unlimited content access

💳 <b>Ready to upgrade?</b> Click below to purchase!
"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f"💎 Buy VIP ({vip_price} ⭐)", callback_data=f"buy_vip_{vip_price}"))
    bot.send_message(message.chat.id, vip_text, reply_markup=markup, parse_mode='HTML')

@bot.message_handler(commands=['browse'])
def browse_content_command(message):
    """Handle content browsing"""
    with app.app_context():
        content_items = ContentItem.query.filter_by(content_type='browse').all()
        
        if not content_items:
            bot.send_message(message.chat.id, "📭 No content available right now. Check back soon!")
            return
        
        browse_text = "🛒 <b>AVAILABLE CONTENT</b>\n\n"
        markup = types.InlineKeyboardMarkup()
        
        for item in content_items:
            user_owns = check_user_owns_content(message.from_user.id, item.name)
            status = "✅ OWNED" if user_owns else f"{item.price_stars} ⭐"
            
            browse_text += f"🎬 <b>{item.name}</b>\n"
            browse_text += f"💰 {status}\n"
            browse_text += f"📝 {item.description or 'Exclusive content'}\n\n"
            
            if user_owns:
                markup.add(types.InlineKeyboardButton(f"📥 Access: {item.name}", callback_data=f"access_{item.name}"))
            else:
                markup.add(types.InlineKeyboardButton(f"💳 Buy: {item.name} ({item.price_stars} ⭐)", callback_data=f"buy_content_{item.name}"))
        
        bot.send_message(message.chat.id, browse_text, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_vip_'))
def handle_vip_purchase(call):
    """Handle VIP subscription purchase"""
    price = int(call.data.split('_')[2])
    user_id = call.from_user.id
    
    # Create invoice for VIP subscription
    bot.send_invoice(
        chat_id=call.message.chat.id,
        title="💎 VIP Membership",
        description=f"Premium VIP access for {get_vip_duration()} days with exclusive content and direct chat",
        invoice_payload=f"vip_subscription_{user_id}",
        provider_token="",  # Telegram Stars doesn't need provider token
        currency="XTR",  # Telegram Stars currency
        prices=[types.LabeledPrice(label="VIP Membership", amount=price)],
        start_parameter="vip_subscription"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_content_'))
def handle_content_purchase(call):
    """Handle content purchase"""
    content_name = call.data.replace('buy_content_', '')
    user_id = call.from_user.id
    
    with app.app_context():
        content = ContentItem.query.filter_by(name=content_name).first()
        if not content:
            bot.answer_callback_query(call.id, "❌ Content not found")
            return
        
        if check_user_owns_content(user_id, content_name):
            bot.answer_callback_query(call.id, "✅ You already own this content")
            return
    
    # Create invoice for content purchase
    bot.send_invoice(
        chat_id=call.message.chat.id,
        title=f"🎬 {content.name}",
        description=content.description or "Exclusive content",
        invoice_payload=f"content_{content_name}_{user_id}",
        provider_token="",
        currency="XTR",
        prices=[types.LabeledPrice(label=content.name, amount=content.price_stars)],
        start_parameter="content_purchase"
    )

@bot.pre_checkout_query_handler(func=lambda query: True)
def pre_checkout_handler(pre_checkout_query):
    """Handle pre-checkout validation with proper price checking"""
    payload = pre_checkout_query.invoice_payload
    total_amount = pre_checkout_query.total_amount
    currency = pre_checkout_query.currency
    
    # Validate currency is Telegram Stars
    if currency != 'XTR':
        bot.answer_pre_checkout_query(pre_checkout_query.id, ok=False, error_message="Invalid currency. Only Telegram Stars accepted.")
        return
    
    # Validate payment amount against expected price
    if payload.startswith('vip_subscription_'):
        expected_price = get_vip_price()
        if total_amount != expected_price:
            bot.answer_pre_checkout_query(pre_checkout_query.id, ok=False, error_message=f"Invalid amount. VIP costs {expected_price} Telegram Stars.")
            return
    elif payload.startswith('content_'):
        parts = payload.split('_')
        content_name = '_'.join(parts[1:-1])
        with app.app_context():
            content = ContentItem.query.filter_by(name=content_name).first()
            if not content:
                bot.answer_pre_checkout_query(pre_checkout_query.id, ok=False, error_message="Content not found.")
                return
            if total_amount != content.price_stars:
                bot.answer_pre_checkout_query(pre_checkout_query.id, ok=False, error_message=f"Invalid amount. This content costs {content.price_stars} Telegram Stars.")
                return
    
    # Payment is valid
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def successful_payment_handler(message):
    """Handle successful payment"""
    payment = message.successful_payment
    payload = payment.invoice_payload
    user_id = message.from_user.id
    amount = payment.total_amount
    
    # Validate payment details
    if payment.currency != 'XTR':
        logger.error(f"Invalid currency in payment: {payment.currency}")
        bot.send_message(message.chat.id, "❌ Payment error: Invalid currency")
        return
    
    # Extract and validate user_id from payload
    payload_user_id = None
    if payload.startswith('vip_subscription_'):
        payload_user_id = int(payload.split('_')[2])
    elif payload.startswith('content_'):
        payload_user_id = int(payload.split('_')[-1])
    
    if payload_user_id != user_id:
        logger.error(f"User ID mismatch: payload={payload_user_id}, actual={user_id}")
        bot.send_message(message.chat.id, "❌ Payment error: User verification failed")
        return
    
    with app.app_context():
        if payload.startswith('vip_subscription_'):
            # Validate VIP payment amount
            expected_vip_price = get_vip_price()
            if amount != expected_vip_price:
                logger.error(f"VIP payment amount mismatch: expected={expected_vip_price}, received={amount}")
                bot.send_message(message.chat.id, f"❌ Payment error: Expected {expected_vip_price} stars, received {amount}")
                return
            
            # Handle VIP subscription payment
            expiry_date = datetime.datetime.now() + datetime.timedelta(days=get_vip_duration())
            
            # Check if user already has VIP subscription
            existing_vip = VipSubscription.query.filter_by(user_id=user_id).first()
            if existing_vip:
                # Extend existing subscription
                existing_vip.expiry_date = expiry_date
                existing_vip.is_active = True
                existing_vip.total_payments += amount
            else:
                # Create new VIP subscription
                vip_sub = VipSubscription()
                vip_sub.user_id = user_id
                vip_sub.start_date = datetime.datetime.now()
                vip_sub.expiry_date = expiry_date
                vip_sub.is_active = True
                vip_sub.total_payments = amount
                db.session.add(vip_sub)
            
            # Update user's total stars spent
            user = User.query.filter_by(user_id=user_id).first()
            if user:
                user.total_stars_spent += amount
            
            db.session.commit()
            
            success_text = f"""
💎 <b>VIP MEMBERSHIP ACTIVATED!</b> ✅

🎉 Welcome to VIP status!
⏰ <b>Valid until:</b> {expiry_date.strftime("%Y-%m-%d")}
💰 <b>Paid:</b> {amount} Telegram Stars

🔥 <b>You now have access to:</b>
• All exclusive VIP content
• Priority direct chat
• Special VIP teasers

💕 Thank you for your support!
"""
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🎬 Access VIP Content", callback_data="vip_content"))
            bot.send_message(message.chat.id, success_text, reply_markup=markup, parse_mode='HTML')
            
        elif payload.startswith('content_'):
            # Handle content purchase payment
            parts = payload.split('_')
            content_name = '_'.join(parts[1:-1])  # Handle content names with underscores
            
            # Validate content exists and price matches
            content = ContentItem.query.filter_by(name=content_name).first()
            if not content:
                logger.error(f"Content not found for purchase: {content_name}")
                bot.send_message(message.chat.id, "❌ Payment error: Content not found")
                return
            
            if amount != content.price_stars:
                logger.error(f"Content payment amount mismatch: expected={content.price_stars}, received={amount}")
                bot.send_message(message.chat.id, f"❌ Payment error: Expected {content.price_stars} stars, received {amount}")
                return
            
            # Check if user already owns this content
            if not check_user_owns_content(user_id, content_name):
                # Add purchase record
                purchase = UserPurchase()
                purchase.user_id = user_id
                purchase.content_name = content_name
                purchase.purchase_date = datetime.datetime.now()
                purchase.price_paid = amount
                db.session.add(purchase)
                
                # Update user's total stars spent
                user = User.query.filter_by(user_id=user_id).first()
                if user:
                    user.total_stars_spent += amount
                
                db.session.commit()
            
            # Deliver content
            content = ContentItem.query.filter_by(name=content_name).first()
            if content and content.file_path:
                success_text = f"""
✅ <b>PURCHASE SUCCESSFUL!</b>

🎬 <b>Content:</b> {content_name}
💰 <b>Paid:</b> {amount} Telegram Stars

📥 <b>Your content is ready!</b>
"""
                bot.send_message(message.chat.id, success_text, parse_mode='HTML')
                
                # Send the actual content
                try:
                    if content.file_path.startswith('http'):
                        # URL-based content
                        bot.send_message(message.chat.id, f"🔗 Access your content: {content.file_path}")
                    else:
                        # Local file content
                        with open(content.file_path, 'rb') as content_file:
                            bot.send_document(message.chat.id, content_file)
                except Exception as e:
                    logger.error(f"Failed to deliver content {content_name}: {e}")
                    bot.send_message(message.chat.id, "❌ Error delivering content. Please contact support.")
            else:
                bot.send_message(message.chat.id, f"✅ Purchase successful! Content: {content_name}")

# Callback handlers for inline buttons
@bot.callback_query_handler(func=lambda call: call.data == "vip_access")
def callback_vip_access(call):
    """Handle VIP access button"""
    vip_access_command(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "browse_content")
def callback_browse_content(call):
    """Handle browse content button"""
    browse_content_command(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "vip_content")
def callback_vip_content(call):
    """Handle VIP content access - REQUIRES ACTIVE VIP SUBSCRIPTION"""
    user_id = call.from_user.id
    
    # CRITICAL: Check VIP access before allowing any content
    if not is_vip_active(user_id):
        bot.answer_callback_query(call.id, "❌ VIP subscription required!")
        vip_access_command(call.message)  # Redirect to VIP purchase
        return
    
    # VIP user confirmed - show VIP content
    vip_content_text = """
💎 <b>EXCLUSIVE VIP CONTENT</b> ✨

🔥 <b>Welcome to your VIP area!</b>

🎬 <b>Available VIP Content:</b>
• Premium behind-the-scenes videos
• Exclusive photo collections
• Personal messages and updates
• Live chat priority access

📅 <b>New VIP content added regularly!</b>

💕 Thank you for being a VIP supporter!
"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💎 VIP Status", callback_data="vip_status"))
    markup.add(types.InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu"))
    
    bot.send_message(call.message.chat.id, vip_content_text, reply_markup=markup, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data == "vip_status")
def callback_vip_status(call):
    """Show VIP subscription status"""
    user_id = call.from_user.id
    
    if not is_vip_active(user_id):
        bot.answer_callback_query(call.id, "❌ No active VIP subscription")
        return
    
    with app.app_context():
        vip = VipSubscription.query.filter_by(user_id=user_id).first()
        if vip:
            expiry_str = vip.expiry_date.strftime("%Y-%m-%d %H:%M")
            days_left = (vip.expiry_date - datetime.datetime.now()).days
            
            status_text = f"""
💎 <b>VIP SUBSCRIPTION STATUS</b>

✅ <b>Status:</b> ACTIVE
🗓 <b>Expires:</b> {expiry_str}
⏰ <b>Days Remaining:</b> {days_left} days
💰 <b>Total Spent:</b> {vip.total_payments} ⭐

🔥 <b>Benefits Active:</b>
• Exclusive VIP content access
• Priority direct chat
• Special VIP teasers
• No ads or limits

💕 Thank you for your continued support!
"""
            bot.send_message(call.message.chat.id, status_text, parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: call.data.startswith('access_'))
def callback_access_content(call):
    """Handle content access for owned content"""
    content_name = call.data.replace('access_', '')
    user_id = call.from_user.id
    
    if not check_user_owns_content(user_id, content_name):
        bot.answer_callback_query(call.id, "❌ You don't own this content")
        return
    
    with app.app_context():
        content = ContentItem.query.filter_by(name=content_name).first()
        if not content:
            bot.answer_callback_query(call.id, "❌ Content not found")
            return
        
        # Deliver content
        try:
            if content.file_path:
                if content.file_path.startswith('http'):
                    bot.send_message(call.message.chat.id, f"🔗 Access your content: {content.file_path}")
                else:
                    with open(content.file_path, 'rb') as content_file:
                        bot.send_document(call.message.chat.id, content_file)
            else:
                bot.send_message(call.message.chat.id, f"📥 Content: {content_name} - Access granted!")
        except Exception as e:
            logger.error(f"Failed to deliver content {content_name}: {e}")
            bot.send_message(call.message.chat.id, "❌ Error accessing content. Please contact support.")

@bot.message_handler(commands=['help'])
def help_command(message):
    """Handle /help command"""
    help_text = """
🤖 <b>AVAILABLE COMMANDS</b>

👥 <b>User Commands:</b>
• /start - Welcome message and main menu
• /vip_access - VIP subscription info and purchase
• /browse - Browse and purchase content
• /help - Show this help message

💎 <b>VIP Benefits:</b>
• Exclusive VIP-only content
• Priority direct chat access
• Special VIP teasers

💳 <b>Payment:</b>
All purchases use Telegram Stars for secure payments

💬 <b>Chat:</b>
Feel free to send me messages anytime!
"""
    
    bot.send_message(message.chat.id, help_text, parse_mode='HTML')

# Owner commands (simplified for now)
@bot.message_handler(commands=['owner_help'])
def owner_help_command(message):
    """Show owner commands"""
    if not is_owner(message.from_user.id):
        return
    
    help_text = """
👑 <b>OWNER COMMANDS</b>

📊 /owner_stats - View user and payment statistics
👥 /owner_users - List all users
💰 /owner_earnings - View earnings summary

🛠 <b>Content Management:</b>
• Use the database or web interface to manage content
• VIP subscriptions are handled automatically

💡 <b>Note:</b> Full admin functionality available via database
"""
    bot.send_message(message.chat.id, help_text, parse_mode='HTML')

@bot.message_handler(commands=['owner_stats'])
def owner_stats_command(message):
    """Show owner statistics"""
    if not is_owner(message.from_user.id):
        return
    
    with app.app_context():
        total_users = User.query.count()
        active_vips = VipSubscription.query.filter(
            VipSubscription.is_active == True,
            VipSubscription.expiry_date > datetime.datetime.now()
        ).count()
        total_earnings = db.session.query(db.func.sum(User.total_stars_spent)).scalar() or 0
        
        stats_text = f"""
📊 <b>BOT STATISTICS</b>

👥 <b>Total Users:</b> {total_users}
💎 <b>Active VIPs:</b> {active_vips}
💰 <b>Total Earnings:</b> {total_earnings} ⭐

📈 <b>System Status:</b> ✅ Running
💡 <b>Database:</b> PostgreSQL Connected
"""
    
    bot.send_message(message.chat.id, stats_text, parse_mode='HTML')

# Run bot functions
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