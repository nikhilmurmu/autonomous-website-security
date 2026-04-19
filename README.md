# AutoSec AI – Autonomous Website Security Agent

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://python.org)
[![CrewAI](https://img.shields.io/badge/CrewAI-1.14.2-orange.svg)](https://crewai.com)
[![Groq](https://img.shields.io/badge/LLM-Groq%20Llama%203.3-brightgreen.svg)](https://groq.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A **zero-human intervention** multi-agent system that autonomously scans websites for security vulnerabilities, generates fix plans, creates backups, applies updates in staging, and validates changes via visual regression testing.

## 🚀 Features

- **Scanner Agent** – Identifies missing security headers, outdated software, and exposed files.
- **Developer Agent** – Generates fix plans, creates simulated backups, and applies updates.
- **QA Agent** – Runs visual regression tests and provides PASS/FAIL recommendations.
- **Human-in-the-Loop Ready** – Architecture supports an approval gateway for production deployments.

## 🧠 Tech Stack

| Layer | Technology |
|:---|:---|
| Agent Framework | CrewAI |
| LLM Provider | Groq (Llama 3.3 70B) – *Free tier* |
| Local Tools | Python (requests, JSON, file I/O) |
| Visual Testing | Playwright (simulated) |
| Environment | Conda on Windows |

## 📁 Project Structure
