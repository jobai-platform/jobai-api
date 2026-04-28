import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
  SECRET_KEY = os.getenv('SECRET_KEY', 'secret')
  ALGORITHM = "HS256"
  ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES'))
  REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv('REFRESH_TOKEN', 7))
  FRONTEND_ORIGIN = os.getenv('FRONTEND_ORIGIN')
  DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./test.db')
  DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')

  # Stripe API
  STRIPE_SECRET_KEY: str = os.getenv('STRIPE_SECRET_KEY')
  STRIPE_WEBHOOK_SECRET: str = os.getenv('STRIPE_WEBHOOK_SECRET')
  STRIPE_PRO_PRICE_LOOCKUP_KEY: str = os.getenv('STRIPE_PRO_PRICE_LOOCKUP_KEY')
  STRIPE_ENTERPRISE_PRICE__LOOCKUP_KEY: str = os.getenv('STRIPE_ENTERPRISE_PRICE_LOOCKUP_KEY')


settings = Settings()
