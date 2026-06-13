# GitAtlas 🗺️

> **An agentic AI system that analyzes any GitHub repository — mapping its architecture, detecting complexity, and generating actionable improvement recommendations.**

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?style=flat-square&logo=fastapi)
![LLM](https://img.shields.io/badge/LLM-Groq%20%7C%20Llama3-orange?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)

---

## What is GitAtlas?

GitAtlas is a **multi-agent AI pipeline** that takes any public GitHub repository URL and produces a deep technical analysis — without the user reading a single line of code.

It uses a **3-stage agentic architecture** inspired by perception-reasoning-action loops in autonomous systems:

```
GitHub URL → [Perception Agent] → [Reasoning Agent] → [Action Agent] → Report + Graph
```

Results stream live to a browser UI via **Server-Sent Events (SSE)**, with a dependency graph rendered using matplotlib and an interactive chat interface to ask follow-up questions about the repo.

---

## Architecture

### Agent Pipeline

| Agent | Model | Role |
|-------|-------|------|
| **Perception** | Llama 3.1 8B (Groq) | Fetches repo via GitHub API, selects top files, detects languages & frameworks |
| **Reasoning** | Llama 3.3 70B (Groq) | Builds module map, detects architecture pattern, scores complexity |
| **Action** | Llama 3.3 70B (Groq) | Generates improvements, modernization plan, onboarding guide, quality score |

### Tech Stack

- **Backend:** FastAPI + uvicorn, SSE streaming
- **AI Inference:** Groq API (Llama 3.1 8B, Llama 3.3 70B)
- **Graph Generation:** matplotlib + networkx
- **Frontend:** Vanilla JS + HTML (single-file, no build step)
- **Deployment:** Heroku (Procfile included)

---

## Features

- 🔍 **Repo Fetching** — Pulls files intelligently via GitHub API, prioritizing important files
- 🧠 **Architecture Detection** — Identifies MVC, microservices, monolith, etc. with confidence score
- 📊 **Complexity Scoring** — 0–100 score with breakdown by module
- 🗺️ **Dependency Graph** — Visual graph of module relationships, highlights critical nodes
- 💡 **Actionable Improvements** — Top 5 prioritized suggestions with effort estimates
- 🚀 **Modernization Plan** — Step-by-step upgrade roadmap
- 💬 **Repo Chat** — Ask questions about any repo in natural language
- ⚡ **Live Streaming** — Results appear in real-time via SSE, no waiting for full response
- 🔄 **Repo Comparison** — Compare two repos side by side

---

## Getting Started

### Prerequisites
- Python 3.10+
- Groq API key (free at [console.groq.com](https://console.groq.com))
- GitHub Personal Access Token (for higher API rate limits)

### Installation

```bash
git clone https://github.com/Systembugg/gitatlas.git
cd gitatlas
pip install -r requirements.txt
```

### Configuration

Create a `.env` file:

```env
GROQ_API_KEY=your_groq_api_key
GITHUB_TOKEN=your_github_token  # optional but recommended
```

### Run

```bash
python server.py
# Open http://localhost:8000
```

---

## Project Structure

```
gitatlas/
├── server.py           # FastAPI backend, SSE streaming, all API routes
├── github_fetcher.py   # GitHub API client, intelligent file selection
├── perception.py       # Perception Agent — language/framework detection
├── reasoning.py        # Reasoning Agent — architecture analysis, module mapping
├── action.py           # Action Agent — improvements, chat, docs generation
├── graph_builder.py    # Dependency graph rendering with matplotlib
├── pocketflow.py       # Lightweight agent orchestration framework
├── index.html          # Full frontend (single file, no build step)
├── requirements.txt
└── Procfile            # Heroku deployment
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/analyze?url=<repo_url>` | Stream full analysis via SSE |
| `POST` | `/api/chat` | Chat with the analyzed repo |
| `POST` | `/api/docs` | Generate documentation |
| `POST` | `/api/compare` | Compare two repositories |
| `GET` | `/api/health` | Health check |

---

## Motivation

Most code intelligence tools require installing plugins, setting up local environments, or are locked behind expensive enterprise plans. GitAtlas makes deep repo analysis **zero-friction** — paste a URL, get a full architectural report in under 60 seconds.

The agentic design (perception → reasoning → action) mirrors how an experienced developer actually reads a codebase: first scan the structure, then understand the relationships, then decide what to improve.

---

## Contributing

PRs and issues welcome. If you're working on LLM-based code analysis, developer tooling, or agentic systems — feel free to reach out.

---

## License

MIT
