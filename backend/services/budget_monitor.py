from datetime import datetime
import calendar
from core.config import get_supabase_client, TABLE_NAME
from services.email_service import send_budget_alert
import logging

def check_budget_and_notify(user_id: str, user_email: str, category_name: str):
    from services.ai_roast import generate_roast_message
    """
    Checks if the user's spending for the given category in the current month
    exceeds the set budget. If so, sends an email alert.
    """
    if not user_email:
        logging.warning(f"No email provided for user {user_id}. Cannot send budget alert.")
        return

    client = get_supabase_client()
    if not client:
        return

    try:
        # 1. Get Category Budget Limit
        res = client.table("categories").select("max_budget").eq("user_id", user_id).eq("name", category_name).execute()
        if not res.data:
            return # No budget set or category not found
        
        max_budget = float(res.data[0].get("max_budget", 0))
        if max_budget <= 0:
            return # Budget disabled
            
        # 2. Calculate Current Month Spending
        now = datetime.now()
        start_date = now.strftime("%Y-%m-01")
        _, last_day = calendar.monthrange(now.year, now.month)
        end_date = now.replace(day=last_day).strftime("%Y-%m-%d")
        
        # Query transactions (Debit only)
        tx_res = client.table(TABLE_NAME).select("amount")\
            .eq("user_id", user_id)\
            .eq("category", category_name)\
            .eq("transaction_type", "Debit")\
            .gte("date", start_date)\
            .lte("date", end_date)\
            .execute()
            
        total_spent = sum(float(t["amount"]) for t in tx_res.data)
        
        # 3. Check and Notify
        if total_spent > max_budget:
            logging.info(f"Budget exceeded for {category_name} (Spent: {total_spent}, Limit: {max_budget}). Sending alert to {user_email}.")
            
            # Fetch user details
            user_details = {}
            try:
                # Use 'name' instead of 'full_name' as per schema
                user_res = client.table("users").select("name, age").eq("id", user_id).single().execute()
                if user_res.data:
                    user_details["name"] = user_res.data.get("name")
                    user_details["age"] = user_res.data.get("age")
            except Exception as e:
                logging.warning(f"Failed to fetch user details for roast: {e}")
            
            # Generate AI Roast
            roast = generate_roast_message(category_name, total_spent, max_budget, user_details)
            
            send_budget_alert(user_email, category_name, total_spent, max_budget, roast_message=roast)
            
    except Exception as e:
        logging.error(f"Error checking budget for user {user_id}: {e}")
