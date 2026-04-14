import os
import secrets

DATABASE_URL     = os.environ.get("DATABASE_URL", "sqlite:///./ferreteria.db")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
SECRET_KEY       = os.environ.get("SECRET_KEY", secrets.token_hex(32))
ENVIRONMENT      = os.environ.get("ENVIRONMENT", "development")  # "development" | "production"
FRONTEND_URL     = os.environ.get("FRONTEND_URL", "http://localhost:5173")
