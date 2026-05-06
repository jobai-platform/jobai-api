import os

from dotenv import load_dotenv

load_dotenv()

class Settings:
  SECRET_KEY = os.getenv("SECRET_KEY", "secret")
  ALGORITHM = "HS256"
  ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
  REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN", "7"))
  FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
  DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./test.db")
  DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

  # Stripe API
  STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
  STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
  # Lookup keys définis dans le Dashboard Stripe (par environnement via .env)
  STRIPE_PRO_PRICE_LOOKUP_KEY: str = os.getenv("STRIPE_PRO_PRICE_LOOKUP_KEY", "jobai_pro_monthly")
  STRIPE_ENTERPRISE_PRICE_LOOKUP_KEY: str = os.getenv(
      "STRIPE_ENTERPRISE_PRICE_LOOKUP_KEY", "jobai_enterprise_monthly",
  )

  # LinkedIn OAuth
  LINKEDIN_CLIENT_ID: str = os.getenv("LINKEDIN_CLIENT_ID", "")
  LINKEDIN_CLIENT_SECRET: str = os.getenv("LINKEDIN_CLIENT_SECRET", "")
  LINKEDIN_REDIRECT_URI: str = os.getenv("LINKEDIN_REDIRECT_URI", "http://localhost:8000/api/v1/auth/linkedin/callback")

  # LinkedIn scraper proxies — comma-separated list, e.g. "http://user:pass@host:port,http://..."
  # Leave empty in dev. Required in prod to avoid LinkedIn rate-limiting.
  LINKEDIN_PROXIES: list[str] | None = (
      [p.strip() for p in os.getenv("LINKEDIN_PROXIES", "").split(",") if p.strip()]
      or None
  )

  # S3 / MinIO storage
  S3_ENDPOINT_URL: str = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
  S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY", "minioadmin")
  S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY", "minioadmin")
  S3_BUCKET_CVS: str = os.getenv("S3_BUCKET_CVS", "jobai-cvs")
  S3_REGION: str = os.getenv("S3_REGION", "us-east-1")
  S3_PUBLIC_BASE_URL: str = os.getenv("S3_PUBLIC_BASE_URL", "http://localhost:9000")


settings = Settings()
