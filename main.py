from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel
from typing import Dict
import json
import uuid
import threading
from datetime import datetime

from tools.scanner_direct import scan_website_direct, generate_scan_summary, create_issue_summary
from tools.qa_tools import visual_regression_test_tool
from tools.deployer_tools import deploy_to_production_tool
from agents.llm_factory import get_llm

app = FastAPI(title="AutoSec AI – Autonomous Security API")

API_KEY = "autosec-secret-2026"

# In‑memory job store (lighter without ChromaDB)
jobs: Dict[str, dict] = {}
job_lock = threading.Lock()

class ScanRequest(BaseModel):
    url: str
    client_id: str = "api-client"
    auto_approve: bool = True

class ScanResponse(BaseModel):
    job_id: str
    status: str
    message: str

def run_scan_background(job_id: str, request: ScanRequest):
    """Process a scan in the background – no ChromaDB memory to save RAM."""
    try:
        scan_result = scan_website_direct(request.url)
        scan_summary = generate_scan_summary(scan_result)
        # No memory lookup – keep it simple for free tier

        llm = get_llm()
        prompt = f"""
A security scan of {request.url} found these issues:
{scan_summary}

Generate a concise fix plan in JSON with fields: issue_type, recommended_action, steps (list), and estimated_time.
Return ONLY the JSON object, no other text.
"""
        try:
            llm_response = llm.call(prompt)
            import re
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                fix_plan = json.loads(json_match.group(0))
            else:
                fix_plan = {"error": "LLM returned non‑JSON", "raw": llm_response[:200]}
        except Exception as e:
            fix_plan = {"error": str(e)}

        qa_result = visual_regression_test_tool.run(
            client_id=request.client_id,
            urls_to_test=[request.url]
        )
        try:
            qa_data = json.loads(qa_result)
            qa_status = qa_data.get("overall_status", "fail")
        except:
            qa_status = "fail"

        if qa_status == "pass" and request.auto_approve:
            deploy_to_production_tool.run(
                client_id=request.client_id,
                deployment_package="api_fix_package"
            )
            deploy_status = "deployed"
        elif qa_status == "pass":
            deploy_status = "pending_approval"
        else:
            deploy_status = "skipped_due_to_qa_fail"

        result = {
            "status": "completed",
            "scan_id": f"scan_{datetime.now().timestamp()}",
            "client_id": request.client_id,
            "url": request.url,
            "timestamp": datetime.now().isoformat(),
            "issues_found": len(scan_result.get("issues", [])),
            "fix_plan": fix_plan,
            "qa_status": qa_status,
            "deployment_status": deploy_status,
            "message": f"Scan completed. QA: {qa_status}. Deployment: {deploy_status}."
        }
    except Exception as e:
        result = {"status": "failed", "error": str(e)}

    with job_lock:
        jobs[job_id] = result

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"service": "AutoSec AI", "status": "running"}

@app.post("/scan", response_model=ScanResponse)
def run_scan(request: ScanRequest, background_tasks: BackgroundTasks, x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    job_id = str(uuid.uuid4())
    with job_lock:
        jobs[job_id] = {"status": "processing"}
    background_tasks.add_task(run_scan_background, job_id, request)
    return ScanResponse(job_id=job_id, status="processing", message="Scan started. Poll /results/{job_id} for the result.")

@app.get("/results/{job_id}")
def get_results(job_id: str, x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    with job_lock:
        job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.get("/debug")
def debug(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    groq_key = __import__('os').getenv("GROQ_API_KEY")
    return {
        "groq_key_set": groq_key is not None,
        "groq_key_preview": (groq_key[:10] + "...") if groq_key else "NOT SET"
    }
@app.post("/test-scan")
def test_scan(request: ScanRequest, x_api_key: str = Header(...)):
    """Synchronous test endpoint – returns result or error immediately."""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    try:
        scan_result = scan_website_direct(request.url)
        return {"success": True, "issues_found": len(scan_result.get("issues", []))}
    except Exception as e:
        return {"success": False, "error": str(e)}