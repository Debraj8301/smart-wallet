from typing import Dict, Any
import logging
from services.ai_service import run_agent, run_insights_agent

JOBS: Dict[str, Dict[str, Any]] = {}

def run_agent_job(job_id: str, batch_size: int, threshold: float, supabase_client: Any, user_id: str = None, user_email: str = None):
    logging.info(f"Job {job_id} started: run_agent")
    JOBS[job_id] = {"status": "running", "result": None, "error": None}
    try:
        res = run_agent(supabase_client, batch_size, threshold, user_id, user_email)
        logging.info(f"Job {job_id} completed successfully")
        JOBS[job_id] = {"status": "done", "result": res, "error": None}
    except Exception as e:
        logging.error(f"Job {job_id} failed: {e}")
        JOBS[job_id] = {"status": "error", "result": None, "error": str(e)}

def run_insights_job(job_id: str, supabase_client: Any, user_id: str):
    logging.info(f"Job {job_id} started: run_insights")
    JOBS[job_id] = {"status": "running", "result": None, "error": None}
    try:
        res = run_insights_agent(supabase_client, user_id)
        logging.info(f"Job {job_id} completed successfully")
        JOBS[job_id] = {"status": "done", "result": res, "error": None}
    except Exception as e:
        logging.error(f"Job {job_id} failed: {e}")
        JOBS[job_id] = {"status": "error", "result": None, "error": str(e)}

