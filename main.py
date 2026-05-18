import os
from fastapi import FastAPI, HTTPException, Header, Query
from pydantic import BaseModel
from typing import Optional
import json
from datetime import datetime

# Import your existing modules
from tools.scanner_direct import scan_website_direct, generate_scan_summary, create_issue_summary
from memory.vector_store import get_memory_store
from tools.qa_tools import visual_regression_test_tool
from tools.deployer_tools import deploy_to_production_tool
from agents.llm_factory import get_llm

app = FastAPI(title="AutoSec AI – Autonomous Security API")
@app.get("/health")
def health():
    return {"status": "ok"}
@app.get("/debug")
def debug(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    groq_key = os.getenv("GROQ_API_KEY")
    return {
        "groq_key_set": groq_key is not None,
        "groq_key_preview": (groq_key[:10] + "...") if groq_key else "NOT SET"
    }

# Simple API key – replace with a real secret in production
API_KEY = "autosec-secret-2026"

class ScanRequest(BaseModel):
    url: str
    client_id: str = "api-client"
    auto_approve: bool = True   # if True, auto‑deploy on QA pass; else returns pending

class ScanResponse(BaseModel):
    scan_id: str
    client_id: str
    url: str
    timestamp: str
    issues_found: int
    fix_plan: dict
    qa_status: str
    deployment_status: str
    message: str

@app.get("/")
def root():
    return {"service": "AutoSec AI", "status": "running"}

@app.post("/scan", response_model=ScanResponse)
def run_scan(request: ScanRequest, x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
    # Step 1: Scan
    scan_result = scan_website_direct(request.url)
    scan_summary = generate_scan_summary(scan_result)
    issue_summary = create_issue_summary(scan_result)
    
    # Step 2: Memory context
    memory = get_memory_store()
    similar_fixes = memory.find_similar_fixes(issue_summary, n_results=2)
    context_text = ""
    if similar_fixes:
        for fix in similar_fixes:
            plan = fix['fix_plan']
            context_text += f"Past fix: {plan.get('recommended_action')}\n"
    
    # Step 3: Generate fix plan using LLM (simpler, reliable call)
    llm = get_llm()
    prompt = f"""
A security scan of {request.url} found these issues:
{scan_summary}

Memory context (past fixes):
{context_text}

Generate a concise fix plan in JSON with fields: issue_type, recommended_action, steps (list), and estimated_time.
Return ONLY the JSON object, no other text.
"""
    try:
        llm_response = llm.call(prompt)
        # Try to extract JSON from response (it may contain markdown)
        import re
        json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
        if json_match:
            fix_plan = json.loads(json_match.group(0))
        else:
            fix_plan = {"error": "LLM returned non-JSON", "raw": llm_response[:200]}
    except Exception as e:
        fix_plan = {"error": str(e)}
    
    # Step 4: QA (simulated visual test)
    qa_result = visual_regression_test_tool.run(
        client_id=request.client_id,
        urls_to_test=[request.url]
    )
    try:
        qa_data = json.loads(qa_result)
        qa_status = qa_data.get("overall_status", "fail")
    except:
        qa_status = "fail"
    
    # Step 5: Deployment
    if qa_status == "pass":
        if request.auto_approve:
            deploy_result = deploy_to_production_tool.run(
                client_id=request.client_id,
                deployment_package="api_fix_package"
            )
            deploy_status = "deployed"
        else:
            deploy_status = "pending_approval"
    else:
        deploy_status = "skipped_due_to_qa_fail"
    
    # Step 6: Store in memory
    memory.store_fix(
        issue_summary=issue_summary,
        fix_plan=fix_plan,
        metadata={"client_id": request.client_id, "url": request.url, "timestamp": datetime.now().isoformat()}
    )
    
    return {
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

@app.get("/status")
def get_status(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    memory = get_memory_store()
    return {
        "memory_documents": memory.collection.count(),
        "uptime": "running"
    }