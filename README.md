# 🚀 GitAtlas

> **Understand any GitHub repository instantly using AI-powered multi-agent analysis.**

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square\&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?style=flat-square\&logo=fastapi)
![GitHub Copilot](https://img.shields.io/badge/GitHub-Copilot-black?style=flat-square\&logo=github)
![GitHub Models](https://img.shields.io/badge/GitHub-Models-black?style=flat-square\&logo=github)
![Groq](https://img.shields.io/badge/AI-Groq-orange?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)

---

## 🌟 Overview

GitAtlas is an **AI-powered developer platform** that analyzes GitHub repositories using a collaborative **multi-agent architecture**.

Simply paste any public GitHub repository URL and GitAtlas automatically:

* 🧠 Understands the architecture
* 📊 Measures software complexity
* 🗺️ Generates dependency graphs
* 🔒 Detects potential risks
* 📚 Creates documentation
* 💬 Answers repository questions
* 📝 Generates AI-powered Pull Request drafts
* ⚖️ Compares repositories
* 🚀 Suggests modernization strategies

Built for the **Microsoft AI Agents League Hackathon 2026**.

---

# ✨ Features

### 🧠 Multi-Agent Repository Analysis

A collaborative AI pipeline inspired by the **Perception → Reasoning → Action** model.

### 🏛️ Architecture Detection

Automatically identifies software architecture including:

* MVC
* Layered Architecture
* Microservices
* Monolith
* Event Driven Systems

with confidence scoring.

---

### 📊 Dependency Graph Generation

Visualizes relationships between modules and identifies critical dependencies.

---

### 📈 Complexity Analysis

Provides:

* Overall complexity score
* Module complexity
* Maintainability insights

---

### 🔒 Security & Risk Detection

Detects:

* Security risks
* Architectural bottlenecks
* Code quality issues
* Maintainability concerns

---

### 💬 AI Repository Chat

Ask natural language questions about any analyzed repository.

Examples:

* Explain authentication flow.
* Where is routing implemented?
* Which modules are tightly coupled?

---

### 📝 AI Pull Request Draft Generation

Automatically generates professional Pull Request drafts including:

* PR Title
* Branch Name
* Implementation Summary
* Affected Modules
* Testing Checklist
* Risk Assessment
* Review Notes

---

### 📚 Documentation Generator

Automatically generates:

* Repository overview
* Architecture explanation
* Onboarding documentation

---

### ⚖️ Repository Comparison

Compare two repositories side-by-side to understand architectural and implementation differences.

---

### 🚀 Modernization Recommendations

Produces prioritized recommendations with estimated implementation effort.

---

# 🤖 AI Agent Pipeline

GitAtlas follows a collaborative multi-agent workflow.

```
GitHub Repository
        │
        ▼
Perception Agent
(Language • Framework • Metadata)
        │
        ▼
Reasoning Agent
(Architecture • Complexity • Security)
        │
        ▼
Action Agent
(Docs • PR Drafts • Recommendations)
        │
        ▼
Interactive Dashboard
```

---

# 🏗️ Architecture

<img width="1536" height="1024" alt="image" src="https://github.com/user-attachments/assets/553873a1-4254-453d-9ebf-f749ca44c298" />

---

# 🪟 Microsoft Technologies Used

GitAtlas combines Microsoft's developer ecosystem with high-performance AI inference.

| Technology        | Purpose                                                                                               |
| ----------------- | ----------------------------------------------------------------------------------------------------- |
| GitHub Copilot    | Assisted development, backend refactoring, prompt engineering, and AI Pull Request Draft improvements |
| GitHub Models API | AI-assisted repository interactions                                                                   |
| GitHub REST API   | Repository retrieval and metadata analysis                                                            |
| Groq Llama Models | Multi-agent reasoning, documentation generation, architecture analysis                                |

### GitHub Copilot Usage

GitHub Copilot was actively used during development to:

* Improve backend implementation
* Refactor existing logic
* Enhance prompt engineering
* Improve AI Pull Request Draft generation
* Accelerate development

---

# ⚙️ Tech Stack

## Backend

* Python
* FastAPI
* Uvicorn

## AI

* Groq API
* Llama 3.1 8B
* Llama 3.3 70B
* GitHub Models API

## Developer Tools

* GitHub Copilot
* GitHub REST API

## Visualization

* Matplotlib
* NetworkX

## Frontend

* HTML
* CSS
* JavaScript

---

# 🚀 Installation

```bash
git clone https://github.com/priyamanna13/GitAtlas-Hackathon.git

cd GitAtlas

python -m venv venv

venv\Scripts\activate

pip install -r requirements.txt
```

---

# 🔑 Environment Variables

Create a `.env`

```env
GROQ_API_KEY=your_groq_api_key
GITHUB_TOKEN=your_github_token
```

---

# ▶️ Run

```bash
python server.py
```

Open:

```
http://localhost:8000
```

---

# 📡 API Endpoints

| Method | Endpoint       | Purpose                  |
| ------ | -------------- | ------------------------ |
| GET    | `/api/analyze` | Analyze repository       |
| POST   | `/api/chat`    | Repository Chat          |
| POST   | `/api/docs`    | Documentation Generation |
| POST   | `/api/pr`      | AI Pull Request Draft    |
| POST   | `/api/compare` | Repository Comparison    |
| GET    | `/api/health`  | Health Check             |

---

# 🎯 Why GitAtlas?

Modern repositories are becoming increasingly difficult to understand.

GitAtlas helps developers:

* Reduce onboarding time
* Understand unfamiliar codebases
* Detect architectural issues
* Improve software quality
* Generate documentation automatically
* Accelerate repository exploration

Instead of manually reading hundreds of files, developers receive AI-powered insights within seconds.

---

# 🚀 Future Roadmap

* Real GitHub Pull Request creation
* AI Code Review Agent
* VS Code Extension
* Docker deployment
* Multi-language repository support
* Local repository analysis
* Team collaboration
* Enterprise repository analytics

---

# 👥 Team
**Priya Manna**|| 
**Ashish Maurya**|| 
**Adarsh Maurya**

---

# 📄 License

MIT License

---

## ⭐ If you like GitAtlas

If this project helped you, consider giving it a ⭐ on GitHub.
