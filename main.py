import os
import json
import uuid
import re
import threading
from datetime import datetime
from typing import Dict

from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel
from groq import Groq

from tools.scanner_direct import scan_website_direct, generate_scan_summary
from tools.qa_tools import visual_regression_test_tool
from tools.deployer_tools import deploy_to_production_tool

app = FastAPI(title="AutoSec AI – Autonomous Security API")
API_KEY = "autosec-secret-2026"

# In‑memory job store
jobs: Dict[str, dict] = {}
job_lock = threading.Lock()

# Lightweight Groq client (no CrewAI)
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
GROQ_MODEL = "llama-3.1-8b-instant"

class ScanRequest(BaseModel):
    url: str
    client_id: str = "api-client"
    auto_approve: bool = True

class ScanResponse(BaseModel):
    job_id: str
    status: str
    message: str

def call_groq(prompt: str) -> str:
    """Minimal Groq API call – replace CrewAI LLM."""
    completion = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=1024
    )
    return completion.choices[0].message.content

def run_scan_background(job_id: str, request: ScanRequest):
    try:
        # 1. Scan
        scan_result = scan_website_direct(request.url)
        scan_summary = generate_scan_summary(scan_result)

        # 2. Generate fix plan via Groq (lightweight)
        prompt = f"""
A security scan of {request.url} found these issues:
{scan_summary}

Generate a concise fix plan in JSON with fields: issue_type, recommended_action, steps (list), and estimated_time.
Return ONLY the JSON object, no other text.
"""
        try:
            llm_response = call_groq(prompt)
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                fix_plan = json.loads(json_match.group(0))
            else:
                fix_plan = {"error": "LLM returned non‑JSON", "raw": llm_response[:200]}
        except Exception as e:
            fix_plan = {"error": str(e)}

        # 3. QA
        qa_result = visual_regression_test_tool.run(
            client_id=request.client_id,
            urls_to_test=[request.url]
        )
        try:
            qa_data = json.loads(qa_result)
            qa_status = qa_data.get("overall_status", "fail")
        except:
            qa_status = "fail"

        # 4. Deploy
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

@app.post("/test-scan")
def test_scan(request: ScanRequest, x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    try:
        scan_result = scan_website_direct(request.url)
        return {"success": True, "issues_found": len(scan_result.get("issues", []))}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/debug")
def debug(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    groq_key = os.getenv("GROQ_API_KEY")
    return {
        "groq_key_set": groq_key is not None,
        "groq_key_preview": (groq_key[:10] + "...") if groq_key else "NOT SET"
    }