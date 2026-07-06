import streamlit as st
import requests
import json
import time

API_BASE = "https://autonomous-website-security.onrender.com"
API_KEY = "autosec-secret-2026"

st.set_page_config(page_title="AutoSec Dashboard", layout="wide")
st.title("AutoSec AI – Security Dashboard")
st.markdown("Monitor and manage your autonomous security scans.")

# Sidebar
st.sidebar.header("Run a Security Scan")
url = st.sidebar.text_input("Website URL", "https://example.com")
auto_approve = st.sidebar.checkbox("Auto‑approve deployment", value=True)

if st.sidebar.button("Start Scan"):
    with st.spinner("Starting scan..."):
        try:
            resp = requests.post(
                f"{API_BASE}/scan",
                json={"url": url, "auto_approve": auto_approve},
                headers={"x-api-key": API_KEY},
                timeout=30
            )
            if resp.status_code == 200:
                data = resp.json()
                st.session_state["job_id"] = data["job_id"]
                st.sidebar.success(f"Scan started! Job ID: {data['job_id']}")
            else:
                st.sidebar.error(f"Error: {resp.status_code}")
        except Exception as e:
            st.sidebar.error(f"Connection error: {e}")

# Main area
if "job_id" in st.session_state:
    job_id = st.session_state["job_id"]
    st.header(f"Scan Job: {job_id}")

    col1, col2 = st.columns([1, 1])
    if col1.button("Refresh Results"):
        with st.spinner("Fetching results..."):
            try:
                resp = requests.get(
                    f"{API_BASE}/results/{job_id}",
                    headers={"x-api-key": API_KEY},
                    timeout=30
                )
                if resp.status_code == 200:
                    data = resp.json()
                    st.session_state["result"] = data
                    if data.get("status") == "completed":
                        st.success("Scan complete!")
                    elif data.get("status") == "failed":
                        st.error(f"Scan failed: {data.get('error', 'Unknown error')}")
                    else:
                        st.info(f"Status: {data.get('status', 'processing')}")
                else:
                    st.warning("Job still processing. Wait a bit and try again.")
            except Exception as e:
                st.error(f"Connection error: {e}")

    if col2.button("Clear Job"):
        st.session_state.pop("job_id", None)
        st.session_state.pop("result", None)
        st.rerun()

    if "result" in st.session_state:
        result = st.session_state["result"]
        if result.get("status") == "completed":
            st.success("Scan completed successfully")
            col1, col2, col3 = st.columns(3)
            col1.metric("Issues Found", result.get("issues_found", 0))
            col2.metric("QA Status", result.get("qa_status", "N/A").upper())
            col3.metric("Deployment", result.get("deployment_status", "N/A").upper())

            st.subheader("Fix Plan")
            fix_plan = result.get("fix_plan", {})
            if isinstance(fix_plan, dict):
                st.json(fix_plan)
            else:
                st.write(fix_plan)

            st.subheader("Raw Response")
            st.json(result)
else:
    st.info("Enter a URL in the sidebar and click 'Start Scan' to begin.")

# Footer
st.markdown("---")
st.caption("AutoSec AI – Autonomous Security System")