from pymongo import MongoClient
import datetime
import hashlib
import json
import os
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('auth')

# MongoDB Atlas URI
MONGO_URI = "mongodb+srv://cosminionutpopa30:LordulCOVRIGEL30@cluster0.pfxrhcv.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Local fallback for when MongoDB is unavailable
LOCAL_USERS_FILE = "local_users.json"


# Initialize MongoDB connection with better error handling
def get_mongodb_connection():
    """Try to establish MongoDB connection with retries and timeout"""
    try:
        # Set a shorter server selection timeout to fail faster
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        # Validate connection
        client.admin.command('ping')
        logger.info("MongoDB connection successful")
        return client
    except Exception as e:
        logger.warning(f"MongoDB connection failed: {e}")
        return None


try:
    # Try to establish MongoDB connection
    client = get_mongodb_connection()
    if client:
        db = client["satellite_app"]
        users_collection = db["users"]
        USING_MONGODB = True
        logger.info("Using MongoDB for authentication")
    else:
        USING_MONGODB = False
        logger.warning("Failed to connect to MongoDB, using local storage fallback")
except Exception as e:
    USING_MONGODB = False
    logger.error(f"MongoDB initialization error: {e}")
    logger.info("Using local storage fallback")


def load_local_users():
    """Load user data from local file if it exists"""
    if os.path.exists(LOCAL_USERS_FILE):
        try:
            with open(LOCAL_USERS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading local users file: {e}")
    return {}


def save_local_users(users_data):
    """Save user data to local file"""
    try:
        with open(LOCAL_USERS_FILE, 'w') as f:
            json.dump(users_data, f)
        return True
    except Exception as e:
        logger.error(f"Error saving local users file: {e}")
        return False


def register_user_local(username, password, tier="basic"):
    """Register a user locally when MongoDB is unavailable"""
    users = load_local_users()
    if username in users:
        return False, "Username already exists"

    users[username] = {
        "username": username,
        "password": hash_password(password),
        "tier": tier,
        "subscription_end": str(datetime.date.today() + datetime.timedelta(days=30)),
        "last_login": str(datetime.date.today()),
        "usage_count": 1
    }

    if save_local_users(users):
        logger.info(f"User {username} registered successfully in local storage")
        return True, "User registered successfully"
    return False, "Failed to save user data"


def login_user_local(username, password):
    """Login a user locally when MongoDB is unavailable"""
    users = load_local_users()
    if username in users and users[username]["password"] == hash_password(password):
        users[username]["last_login"] = str(datetime.date.today())
        users[username]["usage_count"] += 1
        save_local_users(users)
        logger.info(f"User {username} logged in successfully using local storage")
        return users[username]
    return None


def update_user_tier_local(username, new_tier):
    """Update user tier locally when MongoDB is unavailable"""
    users = load_local_users()
    if username in users:
        users[username]["tier"] = new_tier
        result = save_local_users(users)
        if result:
            logger.info(f"User {username} tier updated to {new_tier} in local storage")
        return result
    return False


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def register_user(username, password, tier="basic"):
    """Register a user, trying MongoDB first, then falling back to local storage"""
    if not username or not password:
        return False, "Username and password are required"

    # Try MongoDB first if available
    if USING_MONGODB:
        try:
            # Check if MongoDB connection is still active
            client = get_mongodb_connection()
            if client:
                db = client["satellite_app"]
                users = db["users"]

                if users.find_one({"username": username}):
                    return False, "Username already exists"

                user = {
                    "username": username,
                    "password": hash_password(password),
                    "tier": tier,
                    "subscription_end": str(datetime.date.today() + datetime.timedelta(days=30)),
                    "last_login": str(datetime.date.today()),
                    "usage_count": 1
                }
                users.insert_one(user)
                logger.info(f"User {username} registered successfully in MongoDB")
                return True, "User registered successfully"
        except Exception as e:
            logger.error(f"MongoDB registration error: {e}, falling back to local storage")
            # If MongoDB fails, fall back to local storage

    # If we got here, either MongoDB failed or isn't available
    return register_user_local(username, password, tier)


def login_user(username, password):
    """Login a user, trying MongoDB first, then falling back to local storage"""
    if not username or not password:
        return None

    # Try MongoDB first if available
    if USING_MONGODB:
        try:
            # Check if MongoDB connection is still active
            client = get_mongodb_connection()
            if client:
                db = client["satellite_app"]
                users = db["users"]

                user = users.find_one({
                    "username": username,
                    "password": hash_password(password)
                })

                if user:
                    users.update_one(
                        {"username": username},
                        {"$set": {"last_login": str(datetime.date.today())},
                         "$inc": {"usage_count": 1}}
                    )
                    logger.info(f"User {username} logged in successfully using MongoDB")
                    return user
        except Exception as e:
            logger.error(f"MongoDB login error: {e}, falling back to local storage")
            # If MongoDB fails, fall back to local storage

    # If we got here, either MongoDB failed or isn't available
    return login_user_local(username, password)


def update_user_tier(username, new_tier):
    """Update user tier, trying MongoDB first, then falling back to local storage"""
    if not username or not new_tier:
        return False

    # Try MongoDB first if available
    if USING_MONGODB:
        try:
            # Check if MongoDB connection is still active
            client = get_mongodb_connection()
            if client:
                db = client["satellite_app"]
                users = db["users"]

                result = users.update_one(
                    {"username": username},
                    {"$set": {"tier": new_tier}}
                )
                if result.modified_count > 0:
                    logger.info(f"User {username} tier updated to {new_tier} in MongoDB")
                    return True
        except Exception as e:
            logger.error(f"MongoDB tier update error: {e}, falling back to local storage")
            # If MongoDB fails, fall back to local storage

    # If we got here, either MongoDB failed or isn't available
    return update_user_tier_local(username, new_tier)