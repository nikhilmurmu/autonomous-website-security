import os
import json
import uuid
import re
import sqlite3
import threading
from datetime import datetime
from typing import Dict, Optional

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

# Lightweight Groq client
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
GROQ_MODEL = "llama-3.1-8b-instant"

# ---------------------------------------------------------------------------
# SQLite database setup
# ---------------------------------------------------------------------------
DB_PATH = "autosec.db"
db_lock = threading.Lock()

def get_db() -> sqlite3.Connection:
    """Return a thread‑safe database connection."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Create tables if they don't already exist."""
    with db_lock:
        conn = get_db()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT DEFAULT 'processing',
                result_json TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                customer_id TEXT PRIMARY KEY,
                status TEXT DEFAULT 'active',
                plan TEXT DEFAULT 'pro',
                subscription_id TEXT,
                client_id TEXT,
                api_key TEXT,
                started_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                api_key TEXT PRIMARY KEY,
                client_id TEXT NOT NULL,
                plan TEXT DEFAULT 'pro',
                created_at TEXT
            )
        """)
        conn.commit()
        conn.close()

init_db()

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
    """Minimal Groq API call."""
    completion = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=1024
    )
    return completion.choices[0].message.content

def save_job(job_id: str, status: str, result_json: Optional[str] = None):
    with db_lock:
        conn = get_db()
        conn.execute(
            "INSERT OR REPLACE INTO jobs (job_id, status, result_json) VALUES (?, ?, ?)",
            (job_id, status, result_json)
        )
        conn.commit()
        conn.close()

def load_job(job_id: str) -> Optional[dict]:
    with db_lock:
        conn = get_db()
        row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        conn.close()
    if row is None:
        return None
    result = {"job_id": row["job_id"], "status": row["status"]}
    if row["result_json"]:
        result.update(json.loads(row["result_json"]))
    return result

def run_scan_background(job_id: str, request: ScanRequest):
    """Process a security scan entirely in the background."""
    try:
        scan_result = scan_website_direct(request.url)
        scan_summary = generate_scan_summary(scan_result)

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

        qa_result = visual_regression_test_tool.run(
            client_id=request.client_id,
            urls_to_test=[request.url]
        )
        try:
            qa_data = json.loads(qa_result)
            qa_status = qa_data.get("overall_status", "fail")
        except Exception:
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

        result_data = {
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
        save_job(job_id, "completed", json.dumps(result_data))
    except Exception as e:
        save_job(job_id, "failed", json.dumps({"error": str(e)}))

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
# Scan endpoints (async, persistent)
# ---------------------------------------------------------------------------
@app.post("/scan", response_model=ScanResponse)
def run_scan(request: ScanRequest, background_tasks: BackgroundTasks,
             x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    job_id = str(uuid.uuid4())
    save_job(job_id, "processing")
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
    job = load_job(job_id)
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

# ---------------------------------------------------------------------------
# Stripe subscription endpoints (persistent)
# ---------------------------------------------------------------------------
@app.get("/subscribe")
def create_subscription(plan: str = "pro"):
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
        customer_id = session["customer"]
        client_id = session.get("client_reference_id") or customer_id
        plan = session.get("metadata", {}).get("plan", "pro")
        subscription_id = session.get("subscription")

        # Generate a unique API key for this customer
        user_api_key = f"as-{uuid.uuid4().hex[:24]}"

        with db_lock:
            conn = get_db()
            conn.execute(
                "INSERT OR REPLACE INTO subscriptions (customer_id, status, plan, subscription_id, client_id, api_key, started_at) VALUES (?, 'active', ?, ?, ?, ?, ?)",
                (customer_id, plan, subscription_id, client_id, user_api_key, datetime.now().isoformat())
            )
            conn.execute(
                "INSERT OR REPLACE INTO api_keys (api_key, client_id, plan, created_at) VALUES (?, ?, ?, ?)",
                (user_api_key, client_id, plan, datetime.now().isoformat())
            )
            conn.commit()
            conn.close()

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