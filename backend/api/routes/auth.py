from fastapi import APIRouter, HTTPException, Body, Depends
from pydantic import BaseModel
from core.config import get_supabase_client
from core.deps import get_current_user
from datetime import datetime, timedelta
import calendar

router = APIRouter(prefix="/auth", tags=["auth"])

class LoginRequest(BaseModel):
    email: str
    password: str

class SignupRequest(BaseModel):
    name: str
    email: str
    password: str
    age: int
    occupation: str
    yearly_income: float
    country: str

class ProfileUpdateRequest(BaseModel):
    name: str
    age: int
    occupation: str
    yearly_income: float
    country: str

@router.post("/signup")
async def signup(request: SignupRequest):
    """
    Register a new user with email, password, and extended profile details.
    """
    if len(request.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")

    client = get_supabase_client()
    if not client:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
    
    try:
        # Sign up with email and password
        auth_response = client.auth.sign_up({
            "email": request.email,
            "password": request.password,
            "options": {
                "data": {
                    "name": request.name,
                    "age": request.age,
                    "occupation": request.occupation,
                    "yearly_income": request.yearly_income,
                    "country": request.country
                }
            }
        })
        
        if not auth_response.user:
             raise HTTPException(status_code=400, detail="Signup failed. User not created.")

        user_id = auth_response.user.id
        
        # Insert profile data into 'users' table
        try:
            profile_data = {
                "id": user_id,
                "name": request.name,
                "email": request.email,
                "age": request.age,
                "occupation": request.occupation,
                "yearly_income": request.yearly_income,
                "country": request.country
            }
            client.table("users").upsert(profile_data).execute()
        except Exception as e:
            # If inserting profile fails, we might want to warn, but we'll return success with warning or error
            # For strict consistency, we should probably fail, but user creation in auth worked.
            # We'll rely on complete-profile to fix if needed.
            print(f"Warning: Profile creation failed: {e}")
            raise HTTPException(status_code=500, detail=f"User created, but profile failed: {e}. Please fix database schema.")

        return {
            "message": "Signup successful", 
            "user": {
                "id": user_id,
                "email": request.email
            }
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Signup failed: {str(e)}")

@router.post("/login")
async def login(request: LoginRequest):
    """
    Login with email and password.
    """
    client = get_supabase_client()
    if not client:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
        
    try:
        response = client.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        
        if not response.session:
             raise HTTPException(status_code=401, detail="Invalid credentials or login failed")

        return {
            "message": "Login successful",
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "user": {
                "id": response.user.id,
                "email": response.user.email,
                "role": response.user.role
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Login failed: {str(e)}")

@router.post("/complete-profile")
async def complete_profile(
    request: ProfileUpdateRequest,
    user: dict = Depends(get_current_user)
):
    """
    Save or update user profile details.
    Requires authentication token.
    """
    client = get_supabase_client()
    if not client:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
        
    try:
        data = {
            "id": user.id,
            "name": request.name,
            "age": request.age,
            "occupation": request.occupation,
            "yearly_income": request.yearly_income,
            "country": request.country
        }
        
        client.table("users").upsert(data).execute()
        
        return {"message": "Profile updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to save profile: {str(e)}")

@router.get("/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    """
    Get current user profile details with financial scores.
    """
    client = get_supabase_client()
    if not client:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
    
    try:
        response = client.table("users").select("*").eq("id", user.id).single().execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        profile_data = response.data

        # --- Calculate Scores (Budget Adherence & Impulse Buy) ---
        try:
            # Date Range: Current Month
            now = datetime.now()
            start_date = now.replace(day=1).strftime("%Y-%m-%d")
            # Last day of month
            _, last_day = calendar.monthrange(now.year, now.month)
            end_date = now.replace(day=last_day).strftime("%Y-%m-%d")

            # 1. Fetch Categories with Budget
            cats_res = client.table("categories").select("name,max_budget").eq("user_id", user.id).gt("max_budget", 0).execute()
            categories = cats_res.data or []

            # 2. Fetch Debit Transactions for Current Month
            tx_res = client.table("transactions") \
                .select("amount,category,tags") \
                .eq("user_id", user.id) \
                .eq("transaction_type", "Debit") \
                .gte("date", start_date) \
                .lte("date", end_date) \
                .execute()
            transactions = tx_res.data or []

            # --- Budget Adherence Score ---
            budget_adherence_score = 100.0 # Default if no budgets
            
            if categories:
                # Aggregate spend by category
                cat_spend = {}
                for t in transactions:
                    c = t.get("category")
                    if c:
                        cat_spend[c] = cat_spend.get(c, 0) + (t.get("amount") or 0)
                
                total_overspend = 0.0
                total_budget_limit = 0.0
                
                for cat in categories:
                    name = cat["name"]
                    limit = float(cat["max_budget"])
                    spent = cat_spend.get(name, 0)
                    
                    if spent > limit:
                        total_overspend += (spent - limit)
                    total_budget_limit += limit
                
                if total_budget_limit > 0:
                    # Score drops as overspend increases relative to total budget
                    # 0 overspend = 100
                    # Overspend = Total Budget -> 0
                    raw_score = 100.0 - (total_overspend / total_budget_limit * 100.0)
                    budget_adherence_score = max(0.0, min(100.0, raw_score))
            
            # --- Impulse Buy Score ---
            # Impulse tags
            impulse_tags = ["impulse", "DopamineHit", "RetailTherapy", "BoredomBuy", "PaydaySplurge"]
            
            total_spend = sum((t.get("amount") or 0) for t in transactions)
            impulse_spend = 0.0
            
            for t in transactions:
                tags = t.get("tags") or []
                # Check intersection
                if any(tag in impulse_tags for tag in tags):
                     impulse_spend += (t.get("amount") or 0)
            
            impulse_buy_score = 0.0
            if total_spend > 0:
                impulse_buy_score = (impulse_spend / total_spend) * 100.0

            profile_data["budget_adherence_score"] = round(budget_adherence_score, 1)
            profile_data["impulse_buy_score"] = round(impulse_buy_score, 1)

        except Exception as e:
            print(f"Error calculating profile scores: {e}")
            profile_data["budget_adherence_score"] = None
            profile_data["impulse_buy_score"] = None

        return profile_data
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch profile: {str(e)}")
