from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List, Optional
from pydantic import BaseModel
from core.config import get_supabase_client
from core.deps import get_current_user
from core.ratelimit import RateLimiter
from services.budget_monitor import check_budget_and_notify

router = APIRouter(prefix="/categories", tags=["categories"])

class CategoryBase(BaseModel):
    name: str
    max_budget: float = 0.0

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    max_budget: Optional[float] = None

class CategoryResponse(CategoryBase):
    id: str
    user_id: str

DEFAULT_CATEGORIES = [
    "Groceries", "Restaurants", "Transport", "Utilities", "Rent",
    "Entertainment", "Shopping", "Medical", "Fees", "Subscriptions",
    "Transfer", "Income", "Other"
]

@router.get("/", response_model=List[CategoryResponse])
async def get_categories(user: dict = Depends(get_current_user)):
    client = get_supabase_client()
    if not client:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
    
    try:
        res = client.table("categories").select("*").eq("user_id", user.id).execute()
        categories = res.data
        
        # If no categories found, seed them
        if not categories:
            seed_data = [
                {"user_id": user.id, "name": cat, "max_budget": 0}
                for cat in DEFAULT_CATEGORIES
            ]
            res = client.table("categories").insert(seed_data).execute()
            categories = res.data
            
        return categories
    except Exception as e:
        # Fallback if table doesn't exist or other error
        print(f"Error fetching categories: {e}")
        # Return default structure if DB fails (though this might not match Response model if ID is missing)
        # Better to raise error or return empty list, but let's try to be helpful
        raise HTTPException(status_code=500, detail=f"Failed to fetch categories: {str(e)}")

@router.post("/", response_model=CategoryResponse)
async def create_category(category: CategoryCreate, user: dict = Depends(get_current_user)):
    client = get_supabase_client()
    if not client:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
    
    try:
        data = category.dict()
        data["user_id"] = user.id
        res = client.table("categories").insert(data).execute()
        return res.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create category: {str(e)}")

@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str, 
    category: CategoryUpdate, 
    user: dict = Depends(get_current_user),
    _: None = Depends(RateLimiter(times=10, seconds=3600))
):
    client = get_supabase_client()
    if not client:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
    
    try:
        data = {k: v for k, v in category.dict().items() if v is not None}
        res = client.table("categories").update(data).eq("id", category_id).eq("user_id", user.id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Category not found")
        
        updated_cat = res.data[0]
        # Check if new budget is already exceeded
        if "max_budget" in data and user.email:
            check_budget_and_notify(user.id, user.email, updated_cat["name"])
            
        return updated_cat
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update category: {str(e)}")
