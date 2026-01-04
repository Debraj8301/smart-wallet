import os
from dotenv import load_dotenv
import httpx
from utils.helpers import create_supabase_client
import redis.asyncio as redis

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
REDIS_URL = os.environ.get("REDIS_URL")

# Email Configuration
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.environ.get("SMTP_FROM_EMAIL", SMTP_USERNAME)

TABLE_NAME = "transactions"
supabase_client = None
redis_client = None

def get_supabase_client():
    global supabase_client
    if supabase_client:
        return supabase_client
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    supabase_client = create_supabase_client(SUPABASE_URL, SUPABASE_KEY)
    return supabase_client

def get_redis_client():
    global redis_client
    if redis_client:
        return redis_client
    if not REDIS_URL:
        return None
    redis_client = redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    return redis_client

async def startup_initialize():
    global supabase_client
    global redis_client
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Supabase URL/Key not configured. Set SUPABASE_URL and SUPABASE_KEY.")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{SUPABASE_URL}/rest/v1/", headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"})
            if r.status_code >= 500:
                raise RuntimeError(f"Supabase REST not reachable: {r.status_code}")
    except Exception as e:
        raise RuntimeError(f"Supabase connectivity check failed: {e}")
    supabase_client = create_supabase_client(SUPABASE_URL, SUPABASE_KEY)
    if not supabase_client:
        raise RuntimeError("Failed to create Supabase client.")

    # Initialize Redis
    if REDIS_URL:
        try:
            get_redis_client()
            await redis_client.ping()
            print("Redis connection established.")
        except Exception as e:
            print(f"Warning: Redis connection failed: {e}. Rate limiting may not work.")

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            check = await client.get(
                f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}?select=count&limit=1",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Prefer": "count=exact"
                }
            )
            if check.status_code >= 400:
                raise RuntimeError(f"Supabase table '{TABLE_NAME}' not found or inaccessible (HTTP {check.status_code}). Create the table before starting the API.")
            
            # Check for user_insights table
            check_insights = await client.get(
                f"{SUPABASE_URL}/rest/v1/user_insights?select=count&limit=1",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Prefer": "count=exact"
                }
            )
            if check_insights.status_code >= 400:
                 print("Warning: 'user_insights' table not found. Please create it to save insights.")
    except Exception as e:
        raise RuntimeError(f"Supabase table check failed: {e}")
