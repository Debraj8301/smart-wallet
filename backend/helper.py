import re
from datetime import datetime
from supabase import create_client
import os

def normalize_date(date_str):
    if not date_str:
        return None
    s = str(date_str).strip()
    fmts = ["%d%b,%Y", "%d %b %y", "%d-%m-%Y", "%b %d, %Y", "%d %b %Y"]
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            continue
    try:
        return datetime.fromisoformat(s).date().isoformat()
    except Exception:
        return None

def clean_details(details):
    if not details:
        return ""
    s = str(details)
    s = re.sub(r"^(Paid\\s*to|Paidto|Received\\s*from|Receivedfrom)\\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"^[-–—]+\\s*", "", s)
    s = re.sub(r"\\s+", " ", s).strip()
    return s

def normalize_type(t, details):
    if t in ("Debit", "Credit"):
        return t
    d = (details or "").lower()
    if "received" in d:
        return "Credit"
    if "paid" in d or "debit" in d:
        return "Debit"
    return "Debit" if ("imps" in d or "ecom pur" in d or "pos" in d) else "Debit"

def normalize_amount(a):
    try:
        return round(float(a), 2)
    except Exception:
        return 0.0

def to_records(data, statement_type=None, user_id=None):
    records = []
    for row in data:
        record = {
            "date": normalize_date(row.get("date")),
            "transaction_details": clean_details(row.get("transaction_details")),
            "transaction_type": normalize_type(row.get("type"), row.get("transaction_details")),
            "amount": normalize_amount(row.get("amount")),
            "verification_status": "unverified",
            "statement_type": statement_type,
        }
        if user_id:
            record["user_id"] = user_id
        records.append(record)
    return records

def normalize_statement_type(s):
    if not s:
        return None
    v = str(s).strip().lower()
    if v in ("credit card", "creditcard", "card"):
        return "Credit Card"
    if v in ("bank", "bank account", "account"):
        return "Bank"
    if v in ("upi", "gpay", "phonepe"):
        return "UPI"
    return None

def insert_supabase(client, table_name, records):
    if not client or not records or not table_name:
        return
    try:
        # Use upsert with ignore_duplicates=True to skip existing records
        # This prevents the entire batch from failing due to a single duplicate
        client.table(table_name).upsert(
            records, 
            on_conflict="date,transaction_details,transaction_type,amount", 
            ignore_duplicates=True
        ).execute()
    except Exception as e:
        print(f"Supabase insert error: {e}")

def create_supabase_client(url, key):
    if not url or not key:
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None
