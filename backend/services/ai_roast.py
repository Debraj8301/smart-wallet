import os
import logging
from google.genai import Client

def generate_roast_message(category: str, spent: float, limit: float, user_details: dict = None) -> str:
    """
    Generates a witty, sarcastic roast for exceeding the budget.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "You've exceeded your budget. Try to spend less next time!"

    try:
        client = Client(api_key=api_key)
        # Switching to stable model to avoid RESOURCE_EXHAUSTED errors on experimental models
        model_name = "gemini-2.5-flash-lite" 
    except Exception as e:
        logging.error(f"Failed to initialize Gemini client for roast: {e}")
        return "You've exceeded your budget. Try to spend less next time!"

    name_context = ""
    if user_details:
        if user_details.get("name"):
            name_context += f"The user's name is {user_details.get('name')}."
        if user_details.get("age"):
            name_context += f" The user is {user_details.get('age')} years old."
    
    prompt = f"""
    You are a witty, sarcastic, and slightly mean financial advisor. 
    {name_context}
    The user has exceeded their budget for the category '{category}'. 
    They spent ₹{spent:.2f} but their limit was ₹{limit:.2f}. 
    
    Write a short, personalized, quirky, and roasting message (max 2-3 sentences) scolding them for this financial irresponsibility. 
    Use their name if provided.
    Use Indian currency symbol (₹). Make it memorable, funny, and stinging but not offensive.
    """

    try:
        resp = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        return getattr(resp, "text", "").strip()
    except Exception as e:
        logging.error(f"Gemini API call failed for roast: {e}")
        return "You've exceeded your budget. Serious financial discipline is required!"
    return getattr(resp, "text", "")
