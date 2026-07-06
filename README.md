# AutoSec AI – Autonomous Website Security

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com)
[![Groq](https://img.shields.io/badge/LLM-Groq%20Llama%203.1-orange)](https://groq.com)
[![Stripe](https://img.shields.io/badge/Payments-Stripe-blueviolet)](https://stripe.com)
[![Render](https://img.shields.io/badge/Deployed-Render-46E3B7)](https://render.com)

A zero‑human‑intervention multi‑agent system that autonomously scans websites for security vulnerabilities, generates fix plans, runs QA tests, and deploys patches to production. Includes Stripe subscription billing and a Streamlit client dashboard.

## 🚀 Features

- **Scanner Agent** – Identifies missing security headers, outdated software, and exposed files
- **Developer Agent** – Generates fix plans using LLM reasoning (Groq)
- **QA Agent** – Runs visual regression tests and provides PASS/FAIL recommendations
- **Deployer Agent** – Deploys fixes to production with human‑approval gate
- **Memory System** – ChromaDB vector store that remembers past fixes (RAG)
- **Stripe Subscriptions** – Accepts real payments (test mode)
- **Streamlit Dashboard** – Client‑facing UI for scan monitoring
- **24/7 Cloud Deployment** – Live API on Render

## 🧠 Tech Stack

| Layer | Technology |
|:---|:---|
| Agent Framework | CrewAI |
| LLM Provider | Groq (Llama 3.1 8B Instant) |
| Memory / RAG | ChromaDB + Sentence Transformers |
| Backend API | FastAPI + Uvicorn |
| Payments | Stripe Checkout + Webhooks |
| Dashboard | Streamlit |
| Deployment | Render (Docker) |
| Real Tools | WP‑CLI (WordPress security headers) |

## 📁 Project Structure
