import os
import json
import uuid
import re
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, Header, BackgroundTasks, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import JWTError, jwt
import stripe

# ---------------------------------------------------------------------------
# Lightweight startup – no heavy imports until needed
# ---------------------------------------------------------------------------
app = FastAPI(title="AutoSec AI – Autonomous Security API")

SECRET_KEY = os.getenv("SECRET_KEY", "autosec-super-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7

ADMIN_API_KEY = "autosec-secret-2026"

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Database
DB_PATH = "autosec.db"
db_lock = threading.Lock()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db_lock:
        conn = get_db()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                api_key TEXT UNIQUE NOT NULL,
                plan TEXT DEFAULT 'free',
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                user_id INTEGER,
                status TEXT DEFAULT 'processing',
                result_json TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS subscriptions (
                customer_id TEXT PRIMARY KEY,
                user_id INTEGER,
                status TEXT DEFAULT 'active',
                plan TEXT DEFAULT 'pro',
                subscription_id TEXT,
                started_at TEXT
            );
        """)
        conn.commit()
        conn.close()

init_db()

# ---------------------------------------------------------------------------
# Password & JWT helpers
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode.update({"exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_user_by_email(email: str) -> Optional[dict]:
    with db_lock:
        conn = get_db()
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()
    return dict(row) if row else None

def get_user_by_api_key(api_key: str) -> Optional[dict]:
    with db_lock:
        conn = get_db()
        row = conn.execute("SELECT * FROM users WHERE api_key = ?", (api_key,)).fetchone()
        conn.close()
    return dict(row) if row else None

def authenticate_user(email: str, password: str) -> Optional[dict]:
    user = get_user_by_email(email)
    if not user or not verify_password(password, user["hashed_password"]):
        return None
    return user

# ---------------------------------------------------------------------------
# Lazy imports for heavy tools (only loaded when scan endpoints are called)
# ---------------------------------------------------------------------------
_scan_deps_loaded = False
_groq_client = None

def _ensure_scan_deps():
    global _scan_deps_loaded, _groq_client
    if not _scan_deps_loaded:
        from tools.scanner_direct import scan_website_direct, generate_scan_summary
        from tools.qa_tools import visual_regression_test_tool
        from tools.deployer_tools import deploy_to_production_tool
        from groq import Groq
        _groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        _scan_deps_loaded = True

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class ScanRequest(BaseModel):
    url: str
    auto_approve: bool = True

class ScanResponse(BaseModel):
    job_id: str
    status: str
    message: str

# ---------------------------------------------------------------------------
# Background scan runner
# ---------------------------------------------------------------------------
def save_job(job_id: str, user_id: int, status: str, result_json: Optional[str] = None):
    with db_lock:
        conn = get_db()
        conn.execute(
            "INSERT OR REPLACE INTO jobs (job_id, user_id, status, result_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (job_id, user_id, status, result_json, datetime.utcnow().isoformat())
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
    result = {"job_id": row["job_id"], "user_id": row["user_id"], "status": row["status"]}
    if row["result_json"]:
        result.update(json.loads(row["result_json"]))
    return result

def get_user_jobs(user_id: int, limit: int = 20) -> list:
    with db_lock:
        conn = get_db()
        rows = conn.execute(
            "SELECT job_id, status, created_at FROM jobs WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        conn.close()
    return [dict(r) for r in rows]

def run_scan_background(job_id: str, user_id: int, request: ScanRequest):
    _ensure_scan_deps()
    from tools.scanner_direct import scan_website_direct, generate_scan_summary
    from tools.qa_tools import visual_regression_test_tool
    from tools.deployer_tools import deploy_to_production_tool

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
            llm_response = _groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1024
            )
            llm_text = llm_response.choices[0].message.content
            json_match = re.search(r'\{.*\}', llm_text, re.DOTALL)
            if json_match:
                fix_plan = json.loads(json_match.group(0))
            else:
                fix_plan = {"error": "LLM returned non‑JSON", "raw": llm_text[:200]}
        except Exception as e:
            fix_plan = {"error": str(e)}

        qa_result = visual_regression_test_tool.run(
            client_id=str(user_id),
            urls_to_test=[request.url]
        )
        try:
            qa_data = json.loads(qa_result)
            qa_status = qa_data.get("overall_status", "fail")
        except Exception:
            qa_status = "fail"

        if qa_status == "pass" and request.auto_approve:
            deploy_to_production_tool.run(
                client_id=str(user_id),
                deployment_package="api_fix_package"
            )
            deploy_status = "deployed"
        elif qa_status == "pass":
            deploy_status = "pending_approval"
        else:
            deploy_status = "skipped_due_to_qa_fail"

        result_data = {
            "scan_id": f"scan_{datetime.utcnow().timestamp()}",
            "url": request.url,
            "timestamp": datetime.utcnow().isoformat(),
            "issues_found": len(scan_result.get("issues", [])),
            "fix_plan": fix_plan,
            "qa_status": qa_status,
            "deployment_status": deploy_status,
            "message": f"Scan completed. QA: {qa_status}. Deployment: {deploy_status}."
        }
        save_job(job_id, user_id, "completed", json.dumps(result_data))
    except Exception as e:
        save_job(job_id, user_id, "failed", json.dumps({"error": str(e)}))

# ---------------------------------------------------------------------------
# Authentication endpoints
# ---------------------------------------------------------------------------
@app.post("/signup")
def signup(email: str = Form(...), password: str = Form(...)):
    if get_user_by_email(email):
        raise HTTPException(status_code=400, detail="Email already registered")
    api_key = f"as-{uuid.uuid4().hex[:24]}"
    hashed_pw = hash_password(password)
    with db_lock:
        conn = get_db()
        conn.execute(
            "INSERT INTO users (email, hashed_password, api_key, plan, created_at) VALUES (?, ?, ?, 'free', ?)",
            (email, hashed_pw, api_key, datetime.utcnow().isoformat())
        )
        conn.commit()
        conn.close()
    return {"message": "Account created", "api_key": api_key}

@app.post("/login")
def login(email: str = Form(...), password: str = Form(...)):
    user = authenticate_user(email, password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": str(user["id"])})
    return {"access_token": access_token, "token_type": "bearer", "api_key": user["api_key"]}

def get_current_user(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    with db_lock:
        conn = get_db()
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()
    if not row:
        raise HTTPException(status_code=401, detail="User not found")
    return dict(row)

# ---------------------------------------------------------------------------
# Scan endpoints (user‑specific)
# ---------------------------------------------------------------------------
@app.post("/scan", response_model=ScanResponse)
def run_scan(request: ScanRequest, background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    job_id = str(uuid.uuid4())
    save_job(job_id, user["id"], "processing")
    background_tasks.add_task(run_scan_background, job_id, user["id"], request)
    return ScanResponse(
        job_id=job_id,
        status="processing",
        message="Scan started. Poll /results/{job_id} for the result."
    )

@app.get("/results/{job_id}")
def get_results(job_id: str, user: dict = Depends(get_current_user)):
    job = load_job(job_id)
    if not job or job["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@app.get("/recent-scans")
def recent_scans(user: dict = Depends(get_current_user)):
    return get_user_jobs(user["id"])

# ---------------------------------------------------------------------------
# Admin / test endpoints
# ---------------------------------------------------------------------------
@app.post("/test-scan")
def test_scan(request: ScanRequest, x_api_key: str = Header(...)):
    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    _ensure_scan_deps()
    from tools.scanner_direct import scan_website_direct
    try:
        scan_result = scan_website_direct(request.url)
        return {"success": True, "issues_found": len(scan_result.get("issues", []))}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/")
def root():
    return {"service": "AutoSec AI", "status": "running"}

# ---------------------------------------------------------------------------
# Stripe
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
        success_url="https://autonomous-website-security.onrender.com/dashboard",
        cancel_url="https://autonomous-website-security.onrender.com/dashboard",
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
        plan = session.get("metadata", {}).get("plan", "pro")
        subscription_id = session.get("subscription")
        with db_lock:
            conn = get_db()
            conn.execute(
                "INSERT OR REPLACE INTO subscriptions (customer_id, status, plan, subscription_id, started_at) VALUES (?, 'active', ?, ?, ?)",
                (customer_id, plan, subscription_id, datetime.utcnow().isoformat())
            )
            conn.commit()
            conn.close()
    return {"status": "received"}

# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard():
    with open("dashboard.html", "r", encoding="utf-8") as f:
        return f.read()