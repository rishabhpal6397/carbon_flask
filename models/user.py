"""
CarbonIQ – User Model
Wraps the MongoDB 'users' collection for Flask-Login.

MongoDB Schema (users collection):
{
    "_id":      ObjectId,
    "username": str,          # unique, trimmed
    "email":    str,          # unique, lower-cased
    "password": str,          # bcrypt hash
    "created_at": datetime
}
"""

import bcrypt
from bson import ObjectId
from datetime import datetime
from flask_login import UserMixin
from extensions import mongo

class User(UserMixin):
    """Thin wrapper around a MongoDB user document."""

    def __init__(self, user_doc: dict):
        self.id       = str(user_doc["_id"])
        self.username = user_doc["username"]
        self.email    = user_doc["email"]

    # ── Flask-Login interface ─────────────────────────────────────────────────

    def get_id(self) -> str:
        return self.id

    # ── Password helpers ──────────────────────────────────────────────────────

    @staticmethod
    def hash_password(plain: str) -> str:
        return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def check_password(plain: str, hashed: str) -> bool:
        return bcrypt.checkpw(plain.encode(), hashed.encode())

    # ── DB helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def get_by_id(user_id: str):
        doc = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if doc:
            return User(doc)
        return None
        
        

    @staticmethod
    def get_by_email(email: str):
        return mongo.db.users.find_one({"email": email.lower().strip()})

    @staticmethod
    def get_by_username(username: str):
        return mongo.db.users.find_one({"username": username.strip()})

    @staticmethod
    def create(username: str, email: str, password: str) -> "User":
        doc = {
            "username":   username.strip(),
            "email":      email.lower().strip(),
            "password":   User.hash_password(password),
            "created_at": datetime.utcnow(),
        }
        result    = mongo.db.users.insert_one(doc)
        doc["_id"] = result.inserted_id
        return User(doc)
