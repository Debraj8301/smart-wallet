import os
import json
from typing import List, Dict, Any, TypedDict
from google.genai import Client
from google.genai.types import GenerateContentConfig
from langgraph.graph import StateGraph, END
import logging
from services.budget_monitor import check_budget_and_notify

class State(TypedDict):
    supabase: Any
    batch_size: int
    threshold: float
    user_id: str
    transactions: List[Dict[str, Any]]
    results: List[Dict[str, Any]]
    path: str
    insights: str
    user_profile: Dict[str, Any]
    categories: List[str]

DEFAULT_CATEGORIES = [
    "Groceries",
    "Restaurants",
    "Transport",
    "Utilities",
    "Rent",
    "Entertainment",
    "Shopping",
    "Medical",
    "Fees",
    "Subscriptions",
    "Transfer",
    "Income",
    "Other"
]

TAGS = [
    "essential",
    "recurring",
    "subscription",
    "impulse",
    "luxury",
    "late-night",
    "weekend",
    "family",
    "work",
    "refund",
    "one-off",
    "DopamineHit",
    "RetailTherapy",
    "VampireSpend",
    "BoredomBuy",
    "PaydaySplurge",
    "WeekendWarrior",
    "SurvivalMode",
    "SubscriptionTrap",
    "MinimumDueTrap",
    "InterestLeak",
    "UtilizationSpike",
    "CreditRotation"
]

TAG_HEURISTICS = {
    "DopamineHit": "Small, non-essential luxury purchases; frequent; coffee chains or premium snacks.",
    "RetailTherapy": "Large shopping at fashion/electronics after period of no activity.",
    "VampireSpend": "Small recurring leaks like multiple tiny OTT or app store purchases.",
    "BoredomBuy": "Late night non-essential shopping between 23:00 and 04:00.",
    "PaydaySplurge": "Significant discretionary spend within 48-72 hours after salary credit.",
    "WeekendWarrior": "High velocity spend on Fridays/Saturdays compared to other days.",
    "SurvivalMode": "Essential-only spend in last 5 days of month (groceries, fuel, utilities).",
    "SubscriptionTrap": "Monthly recurring debits rarely used; lack of related active spend.",
    "MinimumDueTrap": "Credit card payment equals minimum due rather than total due.",
    "InterestLeak": "Finance charges or late fees appearing on credit card statement.",
    "UtilizationSpike": "Single transaction consumes >30% of total credit limit.",
    "CreditRotation": "Using one card to pay off another or ATM cash withdrawal from a credit card."
}

FEW_SHOT_EXAMPLES = [
    {
        "input": {"date": "01Nov,2025","transaction_details": "PaidtoBlinkit","transaction_type": "Debit","amount": 425.0,"statement_type": "UPI"},
        "output": {"category": "Groceries","tags": ["essential","recurring"],"confidence": 0.93,"requires_human_verification": False,"reasoning": "Grocery purchase via UPI."}
    },
    {
        "input": {"date": "18-10-2025","transaction_details": "POS/NETFLIX/MUMBAI/181025/08:41/481907","transaction_type": "Debit","amount": 649.0,"statement_type": "Bank"},
        "output": {"category": "Subscriptions","tags": ["subscription","recurring"],"confidence": 0.98,"requires_human_verification": False,"reasoning": "Recurring OTT subscription."}
    },
    {
        "input": {"date": "03Nov,2025","transaction_details": "PaidtoUttarGujaratVij(UGVCL)","transaction_type": "Debit","amount": 5873.22,"statement_type": "UPI"},
        "output": {"category": "Utilities","tags": ["essential","recurring"],"confidence": 0.96,"requires_human_verification": False,"reasoning": "Electricity bill."}
    },
    {
        "input": {"date": "29-10-2025","transaction_details": "NEFT/CITIN25645632712/CAPITAL ONE SERVICES (I) PVT/CITI BANK/","transaction_type": "Credit","amount": 165611.0,"statement_type": "Bank"},
        "output": {"category": "Income","tags": ["work","recurring"],"confidence": 0.98,"requires_human_verification": False,"reasoning": "Salary credit via NEFT."}
    },
    {
        "input": {"date": "27-09-2025","transaction_details": "IMPS Chrgs Incl GST","transaction_type": "Debit","amount": 5.9,"statement_type": "Bank"},
        "output": {"category": "Fees","tags": ["one-off"],"confidence": 0.88,"requires_human_verification": False,"reasoning": "Bank fee."}
    }
]

def fetch_unverified(state: State) -> State:
    s = state["supabase"]
    limit = state["batch_size"]
    user_id = state.get("user_id")
    
    # Fetch categories
    try:
        if user_id:
            res = s.table("categories").select("name").eq("user_id", user_id).execute()
            cats = [r["name"] for r in res.data] if res.data else []
            if not cats:
                 state["categories"] = DEFAULT_CATEGORIES
            else:
                 state["categories"] = cats
        else:
            state["categories"] = DEFAULT_CATEGORIES
    except Exception as e:
        logging.error(f"Failed to fetch categories: {e}")
        state["categories"] = DEFAULT_CATEGORIES

    logging.info(f"Fetching unverified transactions for user_id={user_id}, limit={limit}")
    
    query = s.table("transactions").select("id,date,transaction_details,transaction_type,amount,statement_type,verification_status").eq("verification_status", "unverified")
    
    if user_id:
        query = query.eq("user_id", user_id)
        
    r = query.limit(limit).execute()
    data = r.data if hasattr(r, "data") else r.get("data", [])
    logging.info(f"Fetched {len(data)} unverified transactions")
    state["transactions"] = data or []
    return state

def build_prompt(transactions: List[Dict[str, Any]], categories: List[str] = DEFAULT_CATEGORIES) -> str:
    instr = {
        "task": "Categorize and tag transactions. Return JSON array.",
        "categories": categories,
        "tags": TAGS,
        "apply_heuristics_first": True,
        "tag_heuristics": TAG_HEURISTICS,
        "rules": {
            "output_schema": {
                "id": "int",
                "category": "str",
                "tags": "list[str]",
                "confidence": "float[0,1]",
                "requires_human_verification": "bool"
            },
            "confidence_definition": {
                "high": ">= 0.85",
                "doubtful": "< 0.85"
            }
        },
        "few_shot_examples": FEW_SHOT_EXAMPLES,
        "inputs": [
            {
                "id": t.get("id"),
                "date": t.get("date"),
                "transaction_details": t.get("transaction_details"),
                "transaction_type": t.get("transaction_type"),
                "amount": t.get("amount"),
                "statement_type": t.get("statement_type")
            } for t in transactions
        ]
    }
    return json.dumps(instr)

def call_gemini(prompt: str, response_mime_type: str = "application/json") -> Any:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logging.error("GEMINI_API_KEY not found in environment variables")
        return []
        
    try:
        client = Client(api_key=api_key)
        model_name = "gemini-2.5-flash-lite"
    except Exception as e:
        logging.error(f"Failed to initialize Gemini client: {e}")
        return []

    try:
        config = GenerateContentConfig(response_mime_type=response_mime_type)
        logging.info(f"Calling Gemini with model {model_name}, mime_type={response_mime_type}")
        resp = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config
        )
    except Exception as e:
        logging.error(f"Gemini API call failed: {e}")
        return [] if response_mime_type == "application/json" else ""

    if response_mime_type == "application/json":
        try:
            return json.loads(getattr(resp, "text", "") or "[]")
        except Exception as e:
            logging.error(f"Failed to parse JSON response: {e}")
            return []
    
    return getattr(resp, "text", "")

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

def tag_with_gemini(state: State) -> State:
    txs = state["transactions"]
    if not txs:
        logging.info("No transactions to tag")
        state["results"] = []
        return state
    logging.info(f"Tagging {len(txs)} transactions with Gemini")
    prompt = build_prompt(txs, state.get("categories", DEFAULT_CATEGORIES))
    out = call_gemini(prompt)
    results_map = {o.get("id"): o for o in out if isinstance(o, dict) and "id" in o}
    merged: List[Dict[str, Any]] = []
    for t in txs:
        rid = t.get("id")
        o = results_map.get(rid, None)
        if not o:
            merged.append({
                "id": rid,
                "date": t.get("date"),
                "transaction_details": t.get("transaction_details"),
                "amount": t.get("amount"),
                "transaction_type": t.get("transaction_type"),
                "category": "Other",
                "tags": [],
                "confidence": 0.0,
                "verification_status": "required_human_verification",
                "requires_human_verification": True
            })
        else:
            c = float(o.get("confidence", 0.0))
            bt = o.get("behavioral_tags", o.get("tags", []))
            # Determine status
            req_human = bool(o.get("requires_human_verification", False))
            if c >= state["threshold"] and not req_human:
                v_status = "ai_verified"
            else:
                v_status = "required_human_verification"
            
            merged.append({
                "id": rid,
                "date": t.get("date"),
                "transaction_details": t.get("transaction_details"),
                "amount": t.get("amount"),
                "transaction_type": t.get("transaction_type"),
                "category": o.get("category", "Other"),
                "tags": bt if isinstance(bt, list) else [],
                "confidence": c,
                "verification_status": v_status,
                "requires_human_verification": (v_status == "required_human_verification")
            })
            
    state["results"] = merged
    return state

def generate_insights(state: State) -> State:
    # 1. Fetch User Profile
    user_id = state.get("user_id")
    if not user_id:
        # Fallback to fetching from first transaction if not provided in state (legacy support)
        if not state["transactions"]:
            return state
        user_id = state["transactions"][0].get("user_id")
        if not user_id:
            try:
                 first_id = state["transactions"][0].get("id")
                 res = state["supabase"].table("transactions").select("user_id").eq("id", first_id).single().execute()
                 if res.data:
                     user_id = res.data.get("user_id")
            except:
                 pass
        if not user_id:
            return state

    client = state["supabase"]
    
    # Fetch user profile
    try:
        user_res = client.table("users").select("age, yearly_income, country").eq("id", user_id).single().execute()
        user_profile = user_res.data if hasattr(user_res, "data") else {}
    except:
        user_profile = {}
        
    if not user_profile:
        # Defaults if profile missing
        user_profile = {"age": 30, "yearly_income": 50000, "country": "Unknown"}
    
    state["user_profile"] = user_profile
    
    # Fetch Category Budgets
    category_budgets = {}
    try:
        cat_res = client.table("categories").select("name, max_budget").eq("user_id", user_id).execute()
        if cat_res.data:
            for c in cat_res.data:
                category_budgets[c["name"]] = {"max": c["max_budget"]}
    except Exception as e:
        logging.error(f"Failed to fetch category budgets for insights: {e}")

    # 2. Aggregation Logic
    # Fetch all verified transactions for this user
    all_txs = []
    try:
        logging.info(f"Fetching transactions for user_id={user_id}")
        all_tx_res = client.table("transactions")\
            .select("amount, transaction_type, category, tags, date")\
            .eq("user_id", user_id)\
            .in_("verification_status", ["ai_verified", "human_verified"])\
            .execute()
        all_txs = all_tx_res.data if hasattr(all_tx_res, "data") else []
        logging.info(f"Fetched {len(all_txs)} verified transactions")
    except Exception as e:
        logging.exception(f"Failed to fetch verified transactions for insights generation: {e}")
    # Aggregation
    if not all_txs:
        logging.warning("No verified transactions found for insights")
        state["insights"] = "No verified financial data found. Please upload and verify bank statements first."
        return state

    category_stats = {}
    tag_stats = {}
    
    # Helper to aggregate
    def update_agg(agg_dict, key, amount, type_):
        if key not in agg_dict:
            agg_dict[key] = {"Credit": 0.0, "Debit": 0.0}
        agg_dict[key][type_] += amount

    # Process DB transactions
    for t in all_txs:
        amt = t.get("amount", 0.0)
        ttype = t.get("transaction_type", "Debit")
        cat = t.get("category", "Other")
        tags = t.get("tags", [])
        
        update_agg(category_stats, cat, amt, ttype)
        if isinstance(tags, list):
            for tag in tags:
                update_agg(tag_stats, tag, amt, ttype)
                
    # Process current batch results (merged into results)
    for r in state["results"]:
        amt = r.get("amount", 0.0)
        ttype = r.get("transaction_type", "Debit")
        cat = r.get("category", "Other")
        tags = r.get("tags", [])
        
        update_agg(category_stats, cat, amt, ttype)
        if isinstance(tags, list):
            for tag in tags:
                update_agg(tag_stats, tag, amt, ttype)

    # 3. Build Prompt for Insights
    insight_prompt = f"""
### Persona
You are an elite Financial Behavioral Analyst. Your goal is to analyze structured banking data (categorized monthly debits/credits, age, income, and location) to provide deep, actionable psychological and financial insights.

### Inputs Provided
- User Demographics: Age {user_profile.get('age')}, Yearly Income {user_profile.get('yearly_income')}, Country {user_profile.get('country')}.
- Financial Data: 
  - Category Stats: {json.dumps(category_stats, indent=2)}
  - Category Budgets: {json.dumps(category_budgets, indent=2)}
  - Behavioral Tag Stats: {json.dumps(tag_stats, indent=2)}

### Tasks
Please generate a report covering the following five areas:

1. **"Life Stage" Alignment:** Analyze if the spending patterns are typical for the user's age and income in their specific country. Are they over-investing in "Wants" when they should be building "Foundations" (e.g., property, retirement)?
2. **Emotional Spending Triggers:** Correlate behavioral tags (like "Impulse" or "Late Night") with category spikes. Identify what emotional state might be driving "leakage" in the budget.
3. **Peer Benchmarking:** Using your knowledge of financial standards in {user_profile.get('country')}, compare their savings rate and discretionary spending against high-performers in their income bracket.
4. **Burn Rate & Runway:** Calculate the "Core Survival Cost" (Needs only). Determine how many months the user could sustain their lifestyle if income dropped to zero.
5. **Rule-of-Thumb Audit:** Audit the data against the 50/30/20 rule. Provide a specific "Red/Yellow/Green" status for each segment and one "Golden Move" to fix the biggest imbalance.

### Output Style
- Tone: Professional, empathetic, and direct.
- Format: Use Markdown headers and bullet points. Avoid generic advice; use the specific numbers provided.
"""

    # 4. Call Gemini for Insights
    logging.info("Generating insights with Gemini...")
    insights = call_gemini(insight_prompt, response_mime_type="text/plain")
    
    if not insights:
        logging.warning("Gemini returned empty insights")
        insights = "Failed to generate insights. Please try again later."
    else:
        logging.info(f"Insights generated successfully. Length: {len(insights)}")
        
    state["insights"] = insights
    return state

def router(state: State) -> str:
    res = state["results"] or []
    if not res:
        state["path"] = "B"
        return "mark_needs_verification"
    th = state["threshold"]
    all_high = all((r.get("confidence", 0.0) >= th) and (r.get("verification_status") == "ai_verified") for r in res)
    state["path"] = "A" if all_high else "B"
    return "behavioral_analysis" if state["path"] == "A" else "mark_needs_verification"

def behavioral_analysis(state: State) -> State:
    return state

def mark_needs_verification(state: State) -> State:
    return state

def persist_results(supabase, results: List[Dict[str, Any]], user_id: str = None, user_email: str = None) -> None:
    if not supabase or not results:
        return
    logging.info(f"Persisting {len(results)} results to database")
    updated_categories = set()
    try:
        for r in results:
            vs = "ai_verified" if not bool(r.get("requires_human_verification")) else "required_human_verification"
            cat = r.get("category")
            supabase.table("transactions").update({
                "category": cat,
                "tags": r.get("tags") if isinstance(r.get("tags"), list) else [],
                "verification_status": vs
            }).eq("id", r.get("id")).execute()
            
            if cat and cat != "Uncategorized":
                updated_categories.add(cat)
                
        # Check budgets for updated categories
        if user_id and user_email:
            for category in updated_categories:
                check_budget_and_notify(user_id, user_email, category)
                
    except Exception as e:
        logging.error(f"Error persisting results or checking budget: {e}")

def persist_insights(supabase, user_id: str, content: str) -> None:
    if not supabase or not user_id or not content:
        return
    logging.info(f"Persisting insights for user {user_id}")
    try:
        supabase.table("user_insights").insert({
            "user_id": user_id,
            "content": content
        }).execute()
    except Exception as e:
        logging.error(f"Failed to persist insights: {e}")


def build_graph():
    g = StateGraph(State)
    g.add_node("fetch_unverified", fetch_unverified)
    g.add_node("tag_with_gemini", tag_with_gemini)
    g.add_node("behavioral_analysis", behavioral_analysis)
    g.add_node("mark_needs_verification", mark_needs_verification)
    
    g.set_entry_point("fetch_unverified")
    g.add_edge("fetch_unverified", "tag_with_gemini")
    
    # Conditional edge from tag_with_gemini
    # If path A -> behavioral_analysis -> generate_insights -> END
    # If path B -> mark_needs_verification -> generate_insights -> END (or should insights run even for flagged?)
    # Insights should run regardless of path if we want insights on the whole data including what we just processed.
    # The prompt implies comprehensive analysis.
    
    g.add_conditional_edges("tag_with_gemini", router, {"behavioral_analysis": "behavioral_analysis", "mark_needs_verification": "mark_needs_verification"})
    
    g.add_edge("behavioral_analysis", END)
    g.add_edge("mark_needs_verification", END)
    
    return g.compile()

def build_insights_graph():
    g = StateGraph(State)
    g.add_node("generate_insights", generate_insights)
    g.set_entry_point("generate_insights")
    g.add_edge("generate_insights", END)
    return g.compile()

def run_insights_agent(supabase_client: Any, user_id: str) -> Dict[str, Any]:
    app = build_insights_graph()
    init: State = {
        "supabase": supabase_client,
        "batch_size": 0,
        "threshold": 0.0,
        "user_id": user_id,
        "transactions": [],
        "results": [],
        "path": "",
        "insights": "",
        "user_profile": {},
        "categories": []
    }
    final = app.invoke(init)
    insights_text = final.get("insights", "")
    if insights_text:
        persist_insights(supabase_client, user_id, insights_text)
    return {
        "insights": insights_text
    }

def run_agent(supabase_client: Any, batch_size: int = 100, threshold: float = 0.85, user_id: str = None, user_email: str = None) -> Dict[str, Any]:
    logging.info(f"Starting run_agent for user_id={user_id}, batch_size={batch_size}")
    app = build_graph()
    init: State = {
        "supabase": supabase_client,
        "batch_size": batch_size,
        "threshold": threshold,
        "user_id": user_id,
        "transactions": [],
        "results": [],
        "path": "",
        "insights": "",
        "user_profile": {},
        "categories": []
    }
    final = app.invoke(init)
    res_all = final["results"] or []
    path = final["path"]
    
    flagged = [r for r in res_all if r.get("requires_human_verification")]
    persist_results(supabase_client, res_all, user_id, user_email)
    return {
        "count": len(flagged),
        "path": path,
        "flagged_count": len(flagged),
        "results": flagged
    }
