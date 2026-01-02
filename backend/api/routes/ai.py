from fastapi import APIRouter, BackgroundTasks, HTTPException
import os
import uuid
from google.genai import Client

from core.config import get_supabase_client
from core.deps import get_current_user
from core.ratelimit import RateLimiter
from services.jobs import JOBS, run_agent_job, run_insights_job
from services.ai_service import run_agent, run_insights_agent
from fastapi import Depends

router = APIRouter(prefix="/ai")

@router.post("/run-agent")
async def ai_run_agent(
    batch_size: int = 100, 
    threshold: float = 0.85,
    user: dict = Depends(get_current_user),
    _: None = Depends(RateLimiter(times=5, seconds=60)) # 5 requests per minute
):
    client = get_supabase_client()
    if not client:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
    return run_agent(client, batch_size, threshold, user_id=user.id, user_email=user.email)

@router.post("/generate-insights")
async def ai_generate_insights(
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
    _: None = Depends(RateLimiter(times=3, seconds=300)) # 3 requests per 5 minutes
):
    client = get_supabase_client()
    if not client:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
    
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"status": "pending", "result": None, "error": None}
    background_tasks.add_task(run_insights_job, job_id, client, user.id)
    return {"job_id": job_id, "status": "pending", "message": "Insights generation started in background"}

@router.get("/test-gemini")
async def ai_test_gemini(prompt: str = "Say hello from Gemini", model: str = "gemini-2.5-flash-lite"):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not set")
    try:
        client = Client(api_key=api_key)
        model_name = model
        resp = client.models.generate_content(model=model_name, contents=prompt)
        text = getattr(resp, "text", "")
        return {
            "ok": True,
            "model": model_name,
            "prompt": prompt,
            "response_text": text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini error: {e}")

@router.get("/list-models")
async def list_models():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not set")
    client = Client(api_key=api_key)
    try:
        models = [getattr(m, "name", "") for m in client.models.list()]
        return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini list models error: {e}")

@router.post("/run-agent-async")
async def ai_run_agent_async(
    background_tasks: BackgroundTasks, 
    batch_size: int = 100, 
    threshold: float = 0.85,
    user: dict = Depends(get_current_user),
    _: None = Depends(RateLimiter(times=5, seconds=60)) # 5 requests per minute
):
    client = get_supabase_client()
    if not client:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"status": "pending", "result": None, "error": None}
    background_tasks.add_task(run_agent_job, job_id, batch_size, threshold, client, user.id, user.email)
    return {"job_id": job_id, "status": "pending"}

@router.get("/job-status/{job_id}")
async def ai_job_status(job_id: str):
    j = JOBS.get(job_id)
    if not j:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job_id": job_id, **j}

@router.get("/insights")
async def get_user_insights(user: dict = Depends(get_current_user)):
    client = get_supabase_client()
    if not client:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")
    
    # Fetch latest insight
    try:
        res = client.table("user_insights") \
            .select("*") \
            .eq("user_id", user.id) \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()
        
        data = res.data
        if not data:
            return {"insights": None}
        
        return {"insights": data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch insights: {e}")
