"""All settings come from environment variables (.env). No secrets live in code."""
import os
from dotenv import load_dotenv

load_dotenv()

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))


def _get(name: str, default: str = "") -> str:
    # An empty value in .env counts as "not set", so the default applies.
    return os.getenv(name) or default


def _bool(name: str, default: str) -> bool:
    return _get(name, default).strip().lower() in ("1", "true", "yes", "on")


class Settings:
    DB_MODE = _get("DB_MODE", "atlas").lower()
    MONGO_URI = _get("MONGO_URI")
    DATABASE_NAME = _get("DATABASE_NAME", "carbon_guard")

    JWT_SECRET_KEY = _get("JWT_SECRET_KEY")
    JWT_ALGORITHM = _get("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES = int(_get("JWT_EXPIRE_MINUTES", "1440"))

    ADMIN_EMAIL = _get("ADMIN_EMAIL", "admin@carbonguard.com").lower()
    ADMIN_PASSWORD = _get("ADMIN_PASSWORD")

    # A relative path is relative to the backend folder, wherever the command is started from.
    UPLOAD_DIR = os.path.join(BACKEND_DIR, _get("UPLOAD_DIR", "uploads"))
    MAX_IMAGE_MB = int(_get("MAX_IMAGE_MB", "8"))
    CORS_ORIGINS = [o.strip() for o in _get("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]

    # Login/register attempts allowed per client IP per minute (simple in-process limit).
    AUTH_RATE_LIMIT_PER_MINUTE = int(_get("AUTH_RATE_LIMIT_PER_MINUTE", "10"))

    # AI model (see ai_model/README.md). If the file is missing, AI reports "unavailable".
    AI_MODEL_PATH = _get("AI_MODEL_PATH", os.path.join(BACKEND_DIR, "..", "ai_model", "weights", "carbon_guard_mobilenetv2.onnx"))

    # Reverse geocoding with OpenStreetMap Nominatim (needs internet; 1 request/second policy).
    GEOCODING_ENABLED = _bool("GEOCODING_ENABLED", "true")
    NOMINATIM_URL = _get("NOMINATIM_URL", "https://nominatim.openstreetmap.org/reverse")
    GEOCODING_CONTACT_EMAIL = _get("GEOCODING_CONTACT_EMAIL", "")

    # Satellite evidence: "none" or "copernicus" (Copernicus Data Space Ecosystem, Sentinel-2).
    SATELLITE_PROVIDER = _get("SATELLITE_PROVIDER", "none").lower()
    CDSE_CLIENT_ID = _get("CDSE_CLIENT_ID")
    CDSE_CLIENT_SECRET = _get("CDSE_CLIENT_SECRET")

    def validate(self):
        problems = []
        if not self.JWT_SECRET_KEY or self.JWT_SECRET_KEY == "change-me":
            problems.append("JWT_SECRET_KEY is missing or still 'change-me' (see .env.example).")
        if self.DB_MODE not in ("atlas", "memory"):
            problems.append("DB_MODE must be 'atlas' or 'memory'.")
        if self.DB_MODE == "atlas" and not self.MONGO_URI:
            problems.append("DB_MODE=atlas needs MONGO_URI in .env.")
        if not self.ADMIN_PASSWORD:
            problems.append("ADMIN_PASSWORD is missing in .env.")
        try:
            # Same check the login form uses; otherwise the admin could never log in.
            from email_validator import validate_email
            validate_email(self.ADMIN_EMAIL, check_deliverability=False)
        except Exception:
            problems.append(f"ADMIN_EMAIL '{self.ADMIN_EMAIL}' is not an accepted email address "
                            "(special domains such as .local or .test are refused).")
        if self.SATELLITE_PROVIDER not in ("none", "copernicus"):
            problems.append("SATELLITE_PROVIDER must be 'none' or 'copernicus'.")
        if self.SATELLITE_PROVIDER == "copernicus" and not (self.CDSE_CLIENT_ID and self.CDSE_CLIENT_SECRET):
            problems.append("SATELLITE_PROVIDER=copernicus needs CDSE_CLIENT_ID and CDSE_CLIENT_SECRET.")
        if problems:
            raise RuntimeError("Configuration problem(s):\n - " + "\n - ".join(problems))


settings = Settings()
