import streamlit as st
import requests
import json

API_BASE = "https://autonomous-website-security.onrender.com"
API_KEY = "autosec-secret-2026"

st.set_page_config(page_title="AutoSec Dashboard", layout="wide")
st.title("🛡️ AutoSec AI – Security Dashboard")

# Sidebar
st.sidebar.header("Run a Security Scan")
url = st.sidebar.text_input("Website URL", "https://example.com")
auto_approve = st.sidebar.checkbox("Auto‑approve deployment", value=True)

if st.sidebar.button("Start Scan"):
    with st.spinner("Scanning..."):
        resp = requests.post(
            f"{API_BASE}/scan",
            json={"url": url, "auto_approve": auto_approve},
            headers={"x-api-key": API_KEY}
        )
        if resp.status_code == 200:
            data = resp.json()
            st.session_state["job_id"] = data["job_id"]
            st.sidebar.success(f"Scan started! Job ID: {data['job_id']}")
        else:
            st.sidebar.error(f"Error: {resp.status_code}")

# Main area
if "job_id" in st.session_state:
    job_id = st.session_state["job_id"]
    st.header(f"Scan Job: {job_id}")

    if st.button("Refresh Results"):
        resp = requests.get(
            f"{API_BASE}/results/{job_id}",
            headers={"x-api-key": API_KEY}
        )
        if resp.status_code == 200:
            data = resp.json()
            st.session_state["result"] = data
        else:
            st.warning("Job still processing or not found. Wait a bit and try again.")

    if "result" in st.session_state:
        result = st.session_state["result"]
        if result["status"] == "completed":
            st.success("✅ Scan complete")
            col1, col2, col3 = st.columns(3)
            col1.metric("Issues Found", result["issues_found"])
            col2.metric("QA Status", result["qa_status"].upper())
            col3.metric("Deployment", result["deployment_status"].upper())

            st.subheader("Fix Plan")
            st.json(result["fix_plan"])
        elif result["status"] == "failed":
            st.error(f"Scan failed: {result.get('error', 'Unknown error')}")
        else:
            st.info(f"Status: {result['status']}")
else:
    st.info("👈 Enter a URL and click 'Start Scan' to begin.")