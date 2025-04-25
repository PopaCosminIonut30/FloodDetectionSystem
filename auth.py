from pymongo import MongoClient
import datetime
import hashlib

# MongoDB Atlas URI (înlocuiește <db_password> cu parola ta reală)
MONGO_URI = "mongodb+srv://cosminionutpopa30:LordulCOVRIGEL30@cluster0.pfxrhcv.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["satellite_app"]
users_collection = db["users"]


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def register_user(username, password, tier="basic"):
    if users_collection.find_one({"username": username}):
        return False, "Username already exists"

    user = {
        "username": username,
        "password": hash_password(password),
        "tier": tier,
        "subscription_end": str(datetime.date.today() + datetime.timedelta(days=30)),
        "last_login": str(datetime.date.today()),
        "usage_count": 1
    }
    users_collection.insert_one(user)
    return True, "User registered successfully"


def login_user(username, password):
    user = users_collection.find_one({
        "username": username,
        "password": hash_password(password)
    })

    if user:
        users_collection.update_one(
            {"username": username},
            {"$set": {"last_login": str(datetime.date.today())},
             "$inc": {"usage_count": 1}}
        )
        return user
    return None


def update_user_tier(username, new_tier):
    result = users_collection.update_one(
        {"username": username},
        {"$set": {"tier": new_tier}}
    )
    return result.modified_count > 0
