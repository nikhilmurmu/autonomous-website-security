import os
import json
import uuid
import re
import threading
from datetime import datetime
from typing import Dict

from fastapi import FastAPI, HTTPException, Header, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from groq import Groq
import stripe

from tools.scanner_direct import scan_website_direct, generate_scan_summary
from tools.qa_tools import visual_regression_test_tool
from tools.deployer_tools import deploy_to_production_tool

app = FastAPI(title="AutoSec AI – Autonomous Security API")

API_KEY = "autosec-secret-2026"

# Stripe configuration
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# In‑memory job store for async scan results
jobs: Dict[str, dict] = {}
job_lock = threading.Lock()

# In‑memory subscription store
subscriptions: Dict[str, dict] = {}
subscription_lock = threading.Lock()

# Lightweight Groq client (no CrewAI)
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
GROQ_MODEL = "llama-3.1-8b-instant"

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class ScanRequest(BaseModel):
    url: str
    client_id: str = "api-client"
    auto_approve: bool = True

class ScanResponse(BaseModel):
    job_id: str
    status: str
    message: str

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def call_groq(prompt: str) -> str:
    """Minimal Groq API call – replaces CrewAI LLM."""
    completion = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=1024
    )
    return completion.choices[0].message.content

def run_scan_background(job_id: str, request: ScanRequest):
    """Process a security scan entirely in the background."""
    try:
        # 1. Scan the website
        scan_result = scan_website_direct(request.url)
        scan_summary = generate_scan_summary(scan_result)

        # 2. Generate fix plan via Groq
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

        # 3. Visual regression test (QA)
        qa_result = visual_regression_test_tool.run(
            client_id=request.client_id,
            urls_to_test=[request.url]
        )
        try:
            qa_data = json.loads(qa_result)
            qa_status = qa_data.get("overall_status", "fail")
        except Exception:
            qa_status = "fail"

        # 4. Deploy if QA passes
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

# ---------------------------------------------------------------------------
# Basic endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"service": "AutoSec AI", "status": "running"}

@app.get("/debug")
def debug(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    groq_key = os.getenv("GROQ_API_KEY")
    return {
        "groq_key_set": groq_key is not None,
        "groq_key_preview": (groq_key[:10] + "...") if groq_key else "NOT SET"
    }

# ---------------------------------------------------------------------------
# Scan endpoints (async)
# ---------------------------------------------------------------------------
@app.post("/scan", response_model=ScanResponse)
def run_scan(request: ScanRequest, background_tasks: BackgroundTasks,
             x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    job_id = str(uuid.uuid4())
    with job_lock:
        jobs[job_id] = {"status": "processing"}
    background_tasks.add_task(run_scan_background, job_id, request)
    return ScanResponse(
        job_id=job_id,
        status="processing",
        message="Scan started. Poll /results/{job_id} for the result."
    )

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
    """Synchronous test endpoint – returns result immediately."""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    try:
        scan_result = scan_website_direct(request.url)
        return {"success": True, "issues_found": len(scan_result.get("issues", []))}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ---------------------------------------------------------------------------
# Stripe subscription endpoints
# ---------------------------------------------------------------------------
@app.get("/subscribe")
def create_subscription(plan: str = "pro"):
    """Redirect to Stripe Checkout for the selected plan."""
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="subscription",
        line_items=[{
            "price_data": {
                "currency": "gbp",
                "product_data": {"name": f"AutoSec {plan.capitalize()} Plan"},
                "recurring": {"interval": "month"},
                "unit_amount": 4900 if plan == "pro" else 1900,
            },
            "quantity": 1,
        }],
        success_url="https://autonomous-website-security.onrender.com/success",
        cancel_url="https://autonomous-website-security.onrender.com/cancel",
    )
    return RedirectResponse(session.url)

@app.post("/stripe-webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        client_id = session.get("client_reference_id") or session.get("customer")
        with subscription_lock:
            subscriptions[client_id or "unknown"] = {
                "status": "active",
                "plan": session.get("metadata", {}).get("plan", "pro"),
                "subscription_id": session.get("subscription"),
                "customer_id": session["customer"],
                "started_at": datetime.now().isoformat()
            }
    return {"status": "received"}

@app.get("/success")
def success():
    return {"message": "Subscription activated! Thank you."}

@app.get("/cancel")
def cancel():
    return {"message": "Subscription cancelled."}

# ---------------------------------------------------------------------------
# Professional dashboard
# ---------------------------------------------------------------------------
@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard():
    with open("dashboard.html", "r", encoding="utf-8") as f:
        return f.read()