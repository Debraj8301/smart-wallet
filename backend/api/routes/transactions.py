from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, List, Dict, Any
from core.config import get_supabase_client, TABLE_NAME
from core.deps import get_current_user
import calendar
from datetime import datetime, timedelta

router = APIRouter(prefix="/transactions", tags=["transactions"])

@router.get("/")
async def get_transactions(
    start_date: Optional[str] = Query(None, description="Filter by start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter by end date (YYYY-MM-DD)"),
    min_amount: Optional[float] = Query(None, description="Minimum amount"),
    max_amount: Optional[float] = Query(None, description="Maximum amount"),
    category: Optional[str] = Query(None, description="Filter by category"),
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type (Credit/Debit)"),
    statement_type: Optional[str] = Query(None, description="Filter by statement type (UPI, Bank, Credit Card)"),
    verification_status: Optional[str] = Query(None, description="Filter by verification status (unverified, ai_verified, required_human_verification)"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags (one or more)"),
    search: Optional[str] = Query(None, description="Search in transaction details"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user)
):
    client = get_supabase_client()
    if not client:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")

    query = client.table(TABLE_NAME).select("*", count="exact").eq("user_id", user.id)

    # Apply filters
    if start_date:
        query = query.gte("date", start_date)
    if end_date:
        query = query.lte("date", end_date)
    
    if min_amount is not None:
        query = query.gte("amount", min_amount)
    if max_amount is not None:
        query = query.lte("amount", max_amount)
        
    if category:
        query = query.eq("category", category)
        
    if transaction_type:
        query = query.eq("transaction_type", transaction_type)
        
    if statement_type:
        query = query.eq("statement_type", statement_type)
        
    if verification_status:
        query = query.eq("verification_status", verification_status)
        
    if tags:
        # Supabase 'cs' operator for array containment: tags @> {tag1, tag2}
        # But python client syntax might be .cs("tags", list)
        # Assuming tags is text[] in DB
        query = query.cs("tags", tags)

    if search:
        query = query.ilike("transaction_details", f"%{search}%")

    # Pagination
    query = query.order("date", desc=True).range(offset, offset + limit - 1)

    try:
        result = query.execute()
        return {
            "data": result.data,
            "count": result.count,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching transactions: {str(e)}")

@router.get("/stats")
async def get_transaction_stats(
    month: Optional[str] = Query(None, description="Month to filter stats (YYYY-MM)"),
    user: dict = Depends(get_current_user)
):
    client = get_supabase_client()
    if not client:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
        
    try:
        # Date filtering logic
        start_date = None
        end_date = None
        
        if month:
            try:
                # Parse YYYY-MM
                date_obj = datetime.strptime(month, "%Y-%m")
                start_date = date_obj.strftime("%Y-%m-01")
                # Get last day of month
                _, last_day = calendar.monthrange(date_obj.year, date_obj.month)
                end_date = date_obj.replace(day=last_day).strftime("%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM")

        # 1. Fetch raw transactions for aggregation
        query = client.table(TABLE_NAME).select("*").eq("user_id", user.id)
        
        if start_date:
            query = query.gte("date", start_date)
        if end_date:
            query = query.lte("date", end_date)
            
        # Execute query
        res = query.execute()
        transactions = res.data if res.data else []
        
        # 2. Aggregates
        total_count = len(transactions)
        unverified_count = 0
        flagged_count = 0
        
        # Chart Data Containers
        category_debits = {} # Pie Chart 1
        tag_counts = {}      # Bar Chart 2 (using count or sum? User asked for "debit transactions with these tags", usually sum of amount is more useful, or count. Let's do Amount for impact)
                             # User said "Bar chart showing debit transactions with these tags". I'll assume Amount.
        payment_type_dist = {} # Chart 3
        
        # Initialize specific tags to 0 to ensure they appear in chart even if empty? 
        # Or just show what's there. User gave specific list. Let's initialize.
        target_tags = [
            "DopamineHit", "RetailTherapy", "VampireSpend", "BoredomBuy", 
            "PaydaySplurge", "WeekendWarrior", "SurvivalMode", "SubscriptionTrap", 
            "MinimumDueTrap", "InterestLeak", "UtilizationSpike", "CreditRotation"
        ]
        for t in target_tags:
            tag_counts[t] = 0.0
            
        for tx in transactions:
            # Basic stats
            status = tx.get("verification_status", "unverified")
            if status == "unverified":
                unverified_count += 1
            elif status == "required_human_verification":
                flagged_count += 1
                
            # Chart Aggregations
            amount = float(tx.get("amount", 0.0))
            t_type = tx.get("transaction_type", "Debit") # Default to Debit if missing? Or check.
            category = tx.get("category", "Uncategorized")
            tags = tx.get("tags", [])
            statement_type = tx.get("statement_type", "Unknown")
            
            # 1. Category Pie (Debit only usually, or all? User said "Pie chart showing debit scattered")
            if t_type == "Debit":
                if category not in category_debits:
                    category_debits[category] = 0.0
                category_debits[category] += amount
                
                # 2. Behavioral Tags (Debit only)
                if tags and isinstance(tags, list):
                    for tag in tags:
                        if tag in tag_counts:
                            tag_counts[tag] += amount
                            
            # 3. Payment Type Distribution (All transactions or just Debit? Usually all activity)
            if statement_type not in payment_type_dist:
                payment_type_dist[statement_type] = 0.0
            payment_type_dist[statement_type] += amount

        return {
            "overview": {
                "total_transactions": total_count,
                "unverified": unverified_count,
                "flagged": flagged_count
            },
            "charts": {
                "category_debits": category_debits,
                "tag_spending": tag_counts,
                "payment_type_distribution": payment_type_dist
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating stats: {str(e)}")
