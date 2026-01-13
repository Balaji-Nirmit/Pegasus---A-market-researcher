"""
agent.py
---------
Contains the RecursiveSectionalAgent responsible for:
- Generating research vectors
- Mining web intelligence
- Summarizing per-vector insights
- Synthesizing the final strategic report
"""

import ast
import os
import re
from datetime import datetime

import trafilatura
from ddgs import DDGS
from ollama import Client
from PyQt5.QtCore import QThread, pyqtSignal

import config


class RecursiveSectionalAgent(QThread):
    """Background worker thread that performs autonomous market research."""

    # ---------- Qt Signals ----------
    log_sig = pyqtSignal(str, str)
    query_sig = pyqtSignal(str)
    url_sig = pyqtSignal(str, str)
    vector_intel_sig = pyqtSignal(str, str)
    master_section_sig = pyqtSignal(str, str)
    progress_sig = pyqtSignal(int)
    finished_sig = pyqtSignal()

    def __init__(self, target: str):
        super().__init__()
        self.target = target

        self.client = Client(
            host=config.OLLAMA_HOST,
            headers={
                "Authorization": "Bearer " + os.environ.get("OLLAMA_API_KEY", "")
            },
        )

        self.model = config.PRIMARY_MODEL
        self.vector_summaries = []
        self.vector_sources = {}

    
    def safe_chat(self, messages, retries=2):
        """Call Ollama with retries and fallback."""
        last_error = None
        for attempt in range(retries + 1):
            try:
                return self.client.chat(
                    self.model,
                messages=messages,
            )
            except Exception as e:
                last_error = e
                self.log_sig.emit(
                    "WARN",
                    f"LLM call failed (attempt {attempt + 1}/{retries + 1}): {e}"
                )
        # Fallback model
        if self.model != config.FALLBACK_MODEL:
            self.log_sig.emit(
                "WARN",
                f"Switching to fallback model: {config.FALLBACK_MODEL}"
            )
            self.model = config.FALLBACK_MODEL
            return self.client.chat(
                self.model,
                messages=messages,
            )
        raise last_error


    # ---------- Main Execution ----------
    def run(self):
        try:
            self.log_sig.emit("SYSTEM", f"AGENT DEPLOYED: {self.target}")

            # ================================
            # PHASE 1: Research Vector Generation
            # ================================
            vector_prompt = (
                f"Generate a Python list of exactly {config.NUM_RESEARCH_VECTORS} distinct "
                f"market research queries for deep due diligence on: {self.target}. "
                "Return ONLY the Python list."
            )

            response = self.safe_chat(
                messages=[{"role": "user", "content": vector_prompt}]
            )

            try:
                match = re.search(r"\[.*\]", response["message"]["content"], re.DOTALL)
                queries = ast.literal_eval(match.group(0)) if match else [self.target]
            except Exception:
                queries = [
                    f"{self.target} market analysis",
                    f"{self.target} competitors",
                ]

            # ================================
            # PHASE 2: Per-Vector Intelligence Mining
            # ================================
            for idx, query in enumerate(queries):
                self.query_sig.emit(query)
                self.log_sig.emit("AI_THOUGHT", f"Mining Vector: {query}")

                raw_texts = []

                # ---- Search ----
                try:
                    results = DDGS().text(
                        query,
                        max_results=config.MAX_SOURCES_PER_VECTOR
                    ) or []
                except Exception as e:
                    self.log_sig.emit("WARN", f"Search failed: {e}")
                    results = []

                # ---- Fetch URLs safely ----
                for result in results:
                    url = result.get("href")
                    if not url:
                        continue

                    self.url_sig.emit(query, url)

                try:
                    fetched = trafilatura.fetch_url(
                        url,
                        timeout=10,
                        no_ssl=True
                    )

                    if not fetched:
                        raise ValueError("Empty response")

                    extracted = trafilatura.extract(fetched)

                    if extracted:
                        raw_texts.append(
                            extracted[: config.MAX_CHARS_PER_SOURCE]
                        )

                except Exception as e:
                    self.log_sig.emit(
                        "WARN",
                        f"Skipped URL (fetch failed): {url} | {e}"
                    )
                    continue

                # ---- Summarize vector ----
                if raw_texts:
                    summarize_prompt = (
                        f"Summarize the core intelligence for the query '{query}' "
                        "based on the following sources:\n"
                        + "\n".join(raw_texts)
                    )

                    summary_resp = self.safe_chat(
                        messages=[{"role": "user", "content": summarize_prompt}]
                    )

                    intel_text = summary_resp["message"]["content"]
                    self.vector_intel_sig.emit(query, intel_text)
                    self.vector_summaries.append(
                        f"RESEARCH DATA FOR {query}: {intel_text}"
                    )

                progress = int(((idx + 1) / len(queries)) * 50)
                self.progress_sig.emit(progress)

            # ================================
            # PHASE 3: Master Strategic Synthesis
            # ================================
            self.log_sig.emit("SYSTEM", "Executing Sectional Master Synthesis...")

            report_sections = [
                (
                    "Executive Summary",
                    "Synthesize a high-level overview and market standing.",
                ),
                (
                    "SWOT Analysis",
                    "Provide a detailed Strengths, Weaknesses, Opportunities, and Threats breakdown.",
                ),
                (
                    "PESTLE Analysis",
                    "Analyze Political, Economic, Social, Technological, Legal, and Environmental factors.",
                ),
                (
                    "Competitive Landscape",
                    "Analyze market share and direct competitor positioning.",
                ),
                (
                    "Strategic Outlook",
                    "Provide multi-year projections and final recommendations.",
                ),
            ]

            context = "\n\n".join(self.vector_summaries)
            context = context[: config.MAX_MASTER_CONTEXT_CHARS]

            for idx, (title, instruction) in enumerate(report_sections):
                self.log_sig.emit("AI", f"Streaming Master Section: {title}")

                section_prompt = (
                    f"You are the Pegasus Lead Partner. Using ONLY the following research data, "
                    f"write the '{title}' section of a report for {self.target}. {instruction} "
                    "Be professional, use Markdown headers, and do not truncate."
                    f"\n\nRESEARCH DATA:\n{context}"
                )

                section_resp = self.client.chat(
                    self.model,
                    messages=[{"role": "user", "content": section_prompt}],
                )

                self.master_section_sig.emit(
                    title, section_resp["message"]["content"]
                )

                progress = 50 + int(((idx + 1) / len(report_sections)) * 50)
                self.progress_sig.emit(progress)

            self.finished_sig.emit()
            self.log_sig.emit(
                "SUCCESS", "Terminal has vaulted all intelligence sections."
            )

        except Exception as exc:
            self.log_sig.emit("ERROR", f"Agent Error: {exc}")
        
def run_agent_sync(target: str):
    """
    Run Pegasus agent synchronously (for CLI usage).
    Returns the final markdown report.
    """
    agent = RecursiveSectionalAgent(target)

    # Collect outputs
    report_sections = []

    def collect_section(title, content):
        report_sections.append(f"## {title}\n\n{content}\n\n")

    agent.master_section_sig.connect(collect_section)

    # Run directly (no QThread start)
    agent.run()

    return "".join(report_sections)

