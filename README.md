<img width="1470" height="956" alt="Screenshot 2026-01-11 at 8 41 40 PM" src="https://github.com/user-attachments/assets/c0ef0173-7c76-4b5c-b870-9825a6779e87" />
# Pegasus — Autonomous AI Market Research Agent

Pegasus is a **desktop-based autonomous AI market research and strategic analysis system**. It performs multi-vector web research, synthesizes real-world intelligence using Large Language Models (LLMs), and generates **consulting-grade strategic reports** (Executive Summary, SWOT, PESTLE, Competitive Landscape, and multi-year Outlook) through a recursive, agent-driven pipeline.

Unlike simple chat-based tools, Pegasus is designed as a **research agent**, not a chatbot.

---

## 🚀 Key Capabilities

* **Autonomous Research Decomposition**
  Automatically breaks a topic into multiple high-impact research vectors.

* **Web-Grounded Intelligence**
  Searches the open web, extracts clean content from real sources, and avoids hallucinated analysis.

* **Recursive LLM Synthesis**
  Summarizes each research vector independently, then synthesizes them into a coherent strategic report.

* **Consulting-Grade Outputs**
  Produces structured sections such as:

  * Executive Summary
  * SWOT Analysis
  * PESTLE Analysis
  * Competitive Landscape
  * Strategic Outlook (multi-year)

* **Interactive Desktop UI**
  Built with PyQt5 for real-time streaming of insights, logs, and progress.

* **Exportable Reports**
  Final reports can be downloaded as Markdown for further conversion to PDF, DOCX, or slides.

---

## 🧠 How Pegasus Works (Architecture Overview)

Pegasus follows a **three-phase autonomous research pipeline**:

### 1. Research Vector Generation

The system uses an LLM to generate multiple, distinct research questions ("vectors") for a given topic. These vectors define the scope of the investigation.

### 2. Vector Intelligence Mining

For each research vector:

* DuckDuckGo search is performed
* Top sources are fetched
* Clean textual content is extracted using Trafilatura
* The LLM summarizes core intelligence from the sources

Each vector is treated independently to avoid early bias.

### 3. Master Strategic Synthesis

All vector summaries are combined and passed back to the LLM, which:

* Produces structured strategic sections
* Uses only the gathered research context
* Streams each section live into the UI

This results in a **grounded, explainable, and auditable analysis**.

---

## 🖥 User Interface Overview

The Pegasus UI consists of:

* **Command Panel** — Enter a research topic and deploy the agent
* **Research Tree** — Displays research vectors and mined source URLs
* **Vector Intelligence Tab** — Shows per-vector summarized insights
* **Master Strategic Analysis Tab** — Streams the final report section-by-section
* **System Log Console** — Displays agent actions and execution status

---

## 🛠 Technology Stack

* **Language:** Python 3
* **UI Framework:** PyQt5
* **LLM Provider:** Ollama Cloud
* **Search:** DuckDuckGo (ddgs)
* **Content Extraction:** Trafilatura
* **Rendering:** Markdown → HTML

---

## ⚙️ Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/Pegasus---A-market-researcher.git
cd Pegasus---A-market-researcher
```

### 2. Create & Activate Virtual Environment

**Windows (PowerShell):**

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Set Ollama API Key

```powershell
$env:OLLAMA_API_KEY="your_api_key_here"
```

### 5. Run Pegasus

```powershell
python pegasus.py
```

---

## 📄 Example Use Cases

* Market & industry analysis
* Competitive intelligence
* Technology landscape studies
* Investment & due-diligence briefs
* Internal strategy research
* Academic or capstone projects

---

## ⚠️ Disclaimer

Pegasus provides **AI-assisted research and synthesis** based on publicly available information. Outputs should be reviewed and validated before making business, financial, or policy decisions.

---

## 📌 Roadmap

* Source-level citations per insight
* Modular codebase refactor
* PDF & DOCX export
* Multi-model support (Gemini / OpenAI)
* CLI mode for automation


## ⭐ Why Pegasus Is Different

Pegasus is not a prompt wrapper.

It is a **system-level AI research agent** designed to:

* Decompose problems
* Ground analysis in real data
* Produce decision-ready intelligence

This makes it suitable for **professional, academic, and enterprise environments**.
