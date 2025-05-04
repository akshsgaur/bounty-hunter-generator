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