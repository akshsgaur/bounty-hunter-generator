import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration settings"""
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    REPLICATE_API_KEY = os.getenv("REPLICATE_API_KEY")
    CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    CLOUDFLARE_GATEWAY_ID = os.getenv("CLOUDFLARE_GATEWAY_ID")
    SMTP_SERVER = 'smtp.gmail.com'  # Use Gmail SMTP
    SMTP_PORT = 587
    SENDER_EMAIL = os.getenv('SENDER_EMAIL')
    SENDER_PASSWORD = os.getenv('SENDER_PASSWORD')  # App password for Gmail
    # Stytch Authentication Settings
    STYTCH_PROJECT_ID = os.getenv("STYTCH_PROJECT_ID")
    STYTCH_SECRET = os.getenv("STYTCH_SECRET")
    STYTCH_ENV = os.getenv("STYTCH_ENV", "test")  # 'test' or
    MONGO_USERNAME = os.getenv("MONGO_USERNAME", "goduser")
    MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "bunny123")
    MONGO_CLUSTER = os.getenv("MONGO_CLUSTER", "cluster0.r50y3sr.mongodb.net")
    MONGO_DBNAME = os.getenv("MONGO_DBNAME", "bounty_hunter")
    
    # Construct the MongoDB URI
    MONGO_URI = f"mongodb+srv://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_CLUSTER}/{MONGO_DBNAME}?retryWrites=true&w=majority"
    