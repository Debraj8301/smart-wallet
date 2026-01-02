from fastapi import APIRouter, File, UploadFile, HTTPException, status, BackgroundTasks, Form, Depends
import os
import shutil
import uuid

from pdf_processor import extract_statement_data
from helper import to_records, insert_supabase, normalize_statement_type
from core.config import TABLE_NAME, get_supabase_client
from core.deps import get_current_user

router = APIRouter()

def process_statement_task(path, job_id, original_filename=None, statement_type=None, user_id=None):
    try:
        client = get_supabase_client()
        data = extract_statement_data(path, original_filename)
        records = to_records(data, statement_type, user_id)
        insert_supabase(client, TABLE_NAME, records)
        print(f"Job {job_id} complete. Extracted {len(data)} rows.")
    except Exception as e:
        print(f"Error processing job {job_id}: {e}")
    finally:
        if os.path.exists(path):
            os.remove(path)
            print(f"Removed temp file: {path}")

@router.post("/upload-statement/", status_code=status.HTTP_202_ACCEPTED)
async def upload_statement(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...), 
    statement_type: str = Form(None), 
    user: dict = Depends(get_current_user)
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF files are allowed.")
    
    file_id = str(uuid.uuid4())
    temp_path = os.path.join("uploads", f"temp_{file_id}.pdf")
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {str(e)}")
    
    stype = normalize_statement_type(statement_type)
    if statement_type and not stype:
        raise HTTPException(status_code=400, detail="Invalid statement_type. Allowed: Credit Card, Bank, UPI")
    
    # Pass user_id from the authenticated user to the background task
    background_tasks.add_task(process_statement_task, temp_path, file_id, file.filename, stype, user.id)
    
    return {"message": "File uploaded successfully", "job_id": file_id}
