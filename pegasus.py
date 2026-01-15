import sys
import os
import re
import ast
import json
import markdown
import trafilatura
from datetime import datetime
from ollama import Client
from ddgs import DDGS

# -------------------------------
# Qt MUST be configured FIRST
# -------------------------------
from PyQt5.QtCore import Qt, QCoreApplication
QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

# -------------------------------
# Matplotlib
# -------------------------------
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# -------------------------------
# Qt Widgets / GUI
# -------------------------------
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLineEdit, QTextEdit,
    QLabel, QProgressBar, QFrame, QSplitter,
    QTabWidget, QTreeWidget, QTreeWidgetItem,
    QFileDialog, QMessageBox, QScrollArea
)
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPixmap
from PyQt5.QtWebEngineWidgets import QWebEngineView


# 1. RECURSIVE SECTIONAL ENGINE (The Worker)
class RecursiveSectionalAgent(QThread):
    log_sig = pyqtSignal(str, str)
    query_sig = pyqtSignal(str)
    url_sig = pyqtSignal(str, str)
    vector_intel_sig = pyqtSignal(str, str)
    master_section_sig = pyqtSignal(str, str)
    progress_sig = pyqtSignal(int)
    finished_sig = pyqtSignal()
    chart_sig = pyqtSignal(dict)
    image_sig = pyqtSignal(str, str)
    analytical_sig = pyqtSignal(str, str)

    def __init__(self, target):
        super().__init__()
        self.target = target
        # ✅ Add timeout and retry settings
        try:
            api_key = os.environ.get('OLLAMA_API_KEY')
            if not api_key:
                raise ValueError("OLLAMA_API_KEY not found in environment variables")
            self.client = Client(
                host='https://ollama.com',
                headers={'Authorization': f"Bearer {os.environ.get('OLLAMA_API_KEY')}"},
                timeout=120.0
            )
            self.model = 'gpt-oss:120b'
            self.vector_summaries = []
        except Exception as e:
            self.log_sig.emit("ERROR", f"Failed to initialize Ollama client: {e}")
            raise


    def chat_with_retry(self, prompt, max_retries=3):
        """Chat with automatic retry on failure"""
        for attempt in range(max_retries):
            try:
                self.log_sig.emit("AI", f"Sending request (attempt {attempt + 1}/{max_retries})...")
                resp = self.client.chat(
                    self.model,
                    messages=[{'role': 'user', 'content': prompt}]
                )
                return resp
            except Exception as e:
                self.log_sig.emit("WARN", f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    import time
                    wait_time = (attempt + 1) * 5 # 5s, 10s, 15s
                    self.log_sig.emit("SYSTEM", f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Failed after {max_retries} attempts: {str(e)}")

    def run(self):
        try:
            self.log_sig.emit("SYSTEM", f"AGENT DEPLOYED: {self.target}")
            # --- PHASE 1: RESEARCH VECTOR GENERATION ---
            v_prompt = (
                "Generate a Python list of exactly 7 distinct market research queries "
                f"for deep due diligence on: {self.target}. Return ONLY the Python list."
            )
            resp = self.chat_with_retry(v_prompt)
            try:
                match = re.search(r'\[.*\]', resp['message']['content'], re.DOTALL)
                queries = ast.literal_eval(match.group(0)) if match else [self.target]
            except:
                self.log_sig.emit("WARN", "Failed to parse queries, using defaults")
                queries = [
                    f"{self.target} market analysis",
                    f"{self.target} competitors",
                    f"{self.target} industry trends",
                    f"{self.target} financial performance",
                    f"{self.target} strategic position"
                ]

            # --- PHASE 2: PER-VECTOR INTELLIGENCE ---
            for idx, q in enumerate(queries):
                self.query_sig.emit(q)
                self.log_sig.emit("AI_THOUGHT", f"Mining Vector: {q}")
                raw_texts = []
                try:
                    results = DDGS().text(q, max_results=3)
                    for r in results:
                        link = r['href']
                        self.url_sig.emit(q, link)

                        try:
                            try:
                                downloaded = trafilatura.fetch_url(link)
                                data = trafilatura.extract(downloaded)
                                if data:
                                    raw_texts.append(data[:2000])
                            except:
                                pass

                            # 🔹 NEW: collect images (lightweight, safe)
                            try:
                                html = trafilatura.fetch_url(link)
                                imgs = re.findall(r'<img[^>]+src=["\'](.*?)["\']', html or "", re.IGNORECASE)
                                for img in imgs[:2]:   # limit per page
                                    self.image_sig.emit(q, img)
                            except:
                                pass

                        except Exception as e:
                            self.log_sig.emit("WARN", f"Failed to fetch {link}: {e}")
                except Exception as e:
                    self.log_sig.emit("WARN", f"Search failed for '{q}': {e}")

                if raw_texts:
                    sub_prompt = f"Summarize verified intelligence for: {q}. Focus only on consensus-backed facts.\n" + "\n".join(raw_texts)
                    try:
                        sub_intel = self.chat_with_retry(sub_prompt)
                        intel_txt = sub_intel['message']['content']
                        self.vector_intel_sig.emit(q, intel_txt)
                        analytical_prompt = (
                            "You must output ONLY a valid Mermaid mindmap.\n"
                            "Always start with 'mindmap'\n"
                            "Use 2 spaces per indent level\n"
                            "Wrap node text in ( )\n\n"
                            + intel_txt
                        )

                        analytical_intel = self.chat_with_retry(analytical_prompt)
                        self.analytical_sig.emit(q, analytical_intel['message']['content'])
                        self.vector_summaries.append(f"RESEARCH DATA FOR {q}: {intel_txt}")
                    except Exception as e:
                        self.log_sig.emit("ERROR", f"Failed to summarize vector '{q}': {e}")
                else:
                    # ✅ ADD: Log when no data was extracted
                    self.log_sig.emit("WARN", f"No text extracted for vector: {q}")
                
                self.progress_sig.emit(int(((idx+1)/len(queries))*50))

            # --- PHASE 3: SECTIONAL MASTER SYNTHESIS ---
            self.log_sig.emit("SYSTEM", "Executing Sectional Master Synthesis...")
            report_sections = [
                ("Executive Summary", "Synthesize a high-level overview and market standing."),
                ("SWOT Analysis", "Provide a detailed Strengths, Weaknesses, Opportunities, and Threats breakdown."),
                ("PESTLE Analysis", "Analyze Political, Economic, Social, Technological, Legal, and Environmental factors."),
                ("Porter's Five Forces", "Industry competitiveness"),
                ("Moat & Defensibility", "Long-term competitive advantage"),
                ("Competitive Landscape", "Analyze market share and direct competitor positioning."),
                ("Strategic Outlook", "Provide 2026-2030 projections and final recommendations.")
            ]
            context_for_master = "\n\n".join(self.vector_summaries)

            for i, (title, instruction) in enumerate(report_sections):
                self.log_sig.emit("AI", f"Streaming Master Section: {title}")
                section_prompt = (
                    f"You are the Pegasus Lead Partner. Using ONLY the following research data, "
                    f"write the '{title}' section of a report for {self.target}. {instruction} "
                    "Be professional, use Markdown headers, and do not truncate. Provide the full text for this section."
                    f"\n\nRESEARCH DATA:\n{context_for_master[:10000]}"
                )
                try:
                    section_resp = self.chat_with_retry(section_prompt)
                    section_content = section_resp['message']['content']
                    self.master_section_sig.emit(title, section_content)
                except Exception as e:
                    self.log_sig.emit("ERROR", f"Failed to generate section '{title}': {e}")
                    self.master_section_sig.emit(title, f"*Section generation failed: {e}*")

                self.progress_sig.emit(50 + int(((i+1)/len(report_sections))*40))

            # --- PHASE 3B: CHART DATA ---
            self.log_sig.emit("AI", "Generating market visualization data...")
            chart_prompt = (
                "From the following research data, generate visualization data.\n\n"
                "Return STRICT JSON ONLY in this exact format:\n\n"
                "{\n"
                ' "market_projection": {\n'
                ' "years": [2024, 2025, 2026, 2027, 2028, 2029, 2030],\n'
                ' "values": [500, 505, 512.6, 522.8, 536.9, 553.0, 575.1]\n'
                " },\n"
                ' "regional_split": {\n'
                ' "USA": 38,\n'
                ' "China": 32,\n'
                ' "EU": 18,\n'
                ' "Rest of World": 12\n'
                " },\n"
                ' "swot": {\n'
                ' "Strengths": 8,\n'
                ' "Weaknesses": 4,\n'
                ' "Opportunities": 9,\n'
                ' "Threats": 6\n'
                " },\n"
                ' "pestle": {\n'
                ' "Political": 6,\n'
                ' "Economic": 8,\n'
                ' "Social": 5,\n'
                ' "Technological": 9,\n'
                ' "Legal": 6,\n'
                ' "Environmental": 4\n'
                " },\n"
                ' "moat": {\n'
                ' "Cost Advantage": 7,\n'
                ' "Switching Costs": 6,\n'
                ' "Network Effects": 5,\n'
                ' "IP / Patents": 8,\n'
                ' "Brand Power": 6\n'
                " }\n"
                "}\n\n"
                "Rules:\n"
                "- All scores must be integers from 1 to 10\n"
                "- Percentages must sum to 100\n"
                "- Use only the provided research data\n"
                "- Do NOT include commentary or markdown\n\n"
                f"RESEARCH DATA:\n{context_for_master[:12000]}"
            )
            try:
                chart_resp = self.chat_with_retry(chart_prompt)
                json_match = re.search(r"\{.*\}", chart_resp["message"]["content"], re.DOTALL)
                if json_match:
                    chart_data = json.loads(json_match.group(0))
                    self.chart_sig.emit(chart_data)
                else:
                    self.log_sig.emit("WARN", "No valid JSON found in chart response")
            except Exception as e:
                self.log_sig.emit("WARN", f"Chart generation failed: {e}")

            self.progress_sig.emit(100)
            self.finished_sig.emit()
            self.log_sig.emit("SUCCESS", "Terminal has vaulted all intelligence sections.")

        except Exception as e:
            self.log_sig.emit("ERROR", f"Agent Error: {str(e)}")
            self.finished_sig.emit()

# 2. TERMINAL UI
class PegasusTerminal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pegasus Apex v1.0 | Recursive Sectional Terminal")
        self.resize(1550, 950)
        self.query_nodes = {}
        self.full_report_accumulator = ""
        self.init_ui()
        self.apply_styles()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # 1. TICKER HUD
        hud = QFrame()
        hud.setFixedHeight(40)
        hud_lyt = QHBoxLayout(hud)
        self.ticker = QLabel("PEGASUS APEX: SECTIONAL SYNTHESIS ACTIVE | VECTOR INTELLIGENCE ONLINE | RECURSIVE AGENT READY")
        self.ticker.setStyleSheet("color: #ffaa00; font-family: 'Consolas'; font-weight: bold; font-size: 11px;")
        hud_lyt.addWidget(self.ticker)
        main_layout.addWidget(hud)

        # 2. COMMAND PANEL
        cmd_panel = QFrame()
        cmd_panel.setFixedHeight(60)
        cmd_lyt = QHBoxLayout(cmd_panel)
        self.input_subject = QLineEdit()
        self.input_subject.setPlaceholderText("ENTER SUBJECT FOR SECTIONAL RECURSIVE ANALYSIS...")
        self.btn_run = QPushButton("DEPLOY AGENT")
        self.btn_run.clicked.connect(self.start_analysis)
        self.btn_save = QPushButton("DOWNLOAD")
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self.save_report)
        cmd_lyt.addWidget(QLabel("<b><font color='#ffaa00' size='4'>> </font></b>"))
        cmd_lyt.addWidget(self.input_subject)
        cmd_lyt.addWidget(self.btn_run)
        cmd_lyt.addWidget(self.btn_save)
        main_layout.addWidget(cmd_panel)

        # 3. WORKSPACE
        splitter = QSplitter(Qt.Horizontal)

        # Left: Discovery Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Research Vectors / Mined Sources"])
        self.tree.setFixedWidth(380)
        splitter.addWidget(self.tree)

        # Right: Tabs
        self.tabs = QTabWidget()
        self.insight_view = QTextEdit()
        self.insight_view.setReadOnly(True)
        self.insight_view.setPlaceholderText(
            "Individual vector intelligence will populate here during the crawl..."
        )
        self.report_view = QTextEdit()
        self.report_view.setReadOnly(True)
        self.report_view.setPlaceholderText(
            "The Master Report will stream here section-by-section..."
        )
        
        # ✅ FIX: Use Matplotlib instead of QWebEngineView
        self.chart_figure = Figure(figsize=(10, 6), facecolor='#0b0e14')
        self.chart_canvas = FigureCanvas(self.chart_figure)
        
        # Create a scroll area for the chart
        chart_scroll = QScrollArea()
        chart_scroll.setWidget(self.chart_canvas)
        chart_scroll.setWidgetResizable(True)
        
        self.tabs.addTab(self.insight_view, "Vector Intelligence")
        self.tabs.addTab(self.report_view, "Strategic Report")
        self.tabs.addTab(chart_scroll, "Market Charts") # ✅ Changed from chart_view

        # 🔹 Reference Images Panel
        self.image_scroll = QScrollArea()
        self.image_container = QWidget()
        self.image_layout = QVBoxLayout(self.image_container)
        self.image_scroll.setWidgetResizable(True)
        self.image_scroll.setWidget(self.image_container)
        self.tabs.addTab(self.image_scroll, "Reference Images")
        
        splitter.addWidget(self.tabs)
        main_layout.addWidget(splitter)

        # 🔹 Analytical Map Panel
        self.kmap_scroll = QScrollArea()
        self.kmap_container = QWidget()
        self.kmap_layout = QVBoxLayout(self.kmap_container)
        self.kmap_scroll.setWidgetResizable(True)
        self.kmap_scroll.setWidget(self.kmap_container)
        self.tabs.addTab(self.kmap_scroll, "Analytical Map")

        # 4. FOOTER
        self.prog = QProgressBar()
        self.prog.hide()
        main_layout.addWidget(self.prog)
        
        self.log_box = QTextEdit()
        self.log_box.setFixedHeight(100)
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("background: #000; color: #00FF41; font-family: 'Consolas'; font-size: 10px;")
        main_layout.addWidget(self.log_box)

    def apply_styles(self):
        self.setStyleSheet("""
            /* Global */
            QMainWindow, QWidget {
                background-color: #0b0e14;
                color: #d1d5db;
                font-family: 'Consolas', monospace;
            }
            /* Inputs */
            QLineEdit {
                background: #0b0e14;
                border: 1px solid #30363d;
                padding: 10px;
                color: white;
                border-radius: 4px;
            }
            QPushButton {
                background: #238636;
                color: white;
                font-weight: bold;
                padding: 10px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: #2ea043;
            }
            QPushButton:disabled {
                background: #1a1f26;
                color: #444;
            }
            /* Tabs */
            QTabWidget::pane {
                border: 1px solid #30363d;
                background: #0b0e14;
            }
            QTabBar::tab {
                background: #161b22;
                padding: 12px 25px;
                border: 1px solid #30363d;
                margin-right: 2px;
                color: #d1d5db;
            }
            QTabBar::tab:selected {
                background: #58a6ff;
                color: black;
                font-weight: bold;
            }
            /* Text areas */
            QTextEdit {
                background-color: #0b0e14;
                color: #d1d5db;
                border: 1px solid #30363d;
            }
            /* Tree */
            QTreeWidget {
                background: #0b0e14;
                border: 1px solid #30363d;
            }
            QHeaderView::section {
                background: #161b22;
                color: #ffaa00;
                padding: 5px;
                border: none;
            }
            /* Splitter */
            QSplitter::handle {
                background-color: #161b22;
            }
            /* Progress bar */
            QProgressBar {
                border: 1px solid #30363d;
                background: #000;
                height: 10px;
            }
            QProgressBar::chunk {
                background: #ffaa00;
            }
        """)

    def log(self, tag, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"<font color='#ffaa00'>[{ts}] <b>{tag}:</b></font> {msg}")

    def start_analysis(self):
        target = self.input_subject.text()
        if not target:
            return
        
        self.tree.clear()
        self.query_nodes = {}
        self.insight_view.clear()
        self.report_view.clear()
        self.full_report_accumulator = ""
        # Clear chart
        self.chart_figure.clear()
        self.chart_canvas.draw()
        
        self.btn_run.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.prog.show()

        # Clear old images
        for i in reversed(range(self.image_layout.count())):
            self.image_layout.itemAt(i).widget().deleteLater()
        
        self.worker = RecursiveSectionalAgent(target)
        self.worker.log_sig.connect(self.log)
        self.worker.query_sig.connect(self.add_query_node)
        self.worker.url_sig.connect(self.add_url_node)
        self.worker.vector_intel_sig.connect(self.stream_vector_insight)
        self.worker.master_section_sig.connect(self.stream_master_section)
        self.worker.finished_sig.connect(self.on_complete)
        self.worker.progress_sig.connect(self.prog.setValue)
        self.worker.chart_sig.connect(self.render_market_chart)
        self.worker.image_sig.connect(self.add_image)
        self.worker.analytical_sig.connect(self.add_analytical_card) 
        self.worker.start()

    def add_query_node(self, q):
        parent = QTreeWidgetItem(self.tree)
        parent.setText(0, f"VEC: {q.upper()}")
        parent.setForeground(0, QColor("#ffaa00"))
        self.query_nodes[q] = parent
        self.tree.expandItem(parent)

    def add_url_node(self, q, url):
        if q in self.query_nodes:
            child = QTreeWidgetItem(self.query_nodes[q])
            child.setText(0, url)
            child.setForeground(0, QColor("#58a6ff"))

    def stream_vector_insight(self, header, content):
        html_content = markdown.markdown(content, extensions=['fenced_code', 'tables'])
        vector_style = """
        <style>
            body { font-family: 'Segoe UI', sans-serif; color: #d1d5db; background-color: transparent; }
            .vector-header { color: #ffaa00; font-size: 14px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; border-left: 3px solid #ffaa00; padding-left: 10px; margin-bottom: 10px; }
            code { background: rgba(255, 255, 255, 0.1); color: #ff79c6; border-radius: 4px; padding: 2px; }
            hr { border: 0; border-top: 1px solid rgba(255, 255, 255, 0.1); margin: 20px 0; }
        </style>
        """
        styled_block = f"""
        {vector_style}
        <div class="vector-header">RECURSIVE VECTOR: {header.upper()}</div>
        <div class="vector-content">{html_content}</div>
        <hr>
        """
        self.insight_view.append(styled_block)

    def stream_master_section(self, title, content):
        self.tabs.setCurrentIndex(1)
        self.full_report_accumulator += f"## {title}\n\n{content}\n\n"
        html_body = markdown.markdown(self.full_report_accumulator, extensions=['fenced_code', 'tables'])
        master_style = """
        <style>
            body { font-family: 'Segoe UI', sans-serif; color: #e0e0e0; background-color: #0b0e14; line-height: 1.6; }
            h1 { color: #ffffff; text-align: center; margin-bottom: 30px; }
            h2 { color: #ffaa00; text-shadow: 0 0 12px rgba(255, 170, 0, 0.4); border-bottom: 1px solid rgba(255, 170, 0, 0.2); padding-bottom: 5px; margin-top: 30px; }
            h3 { color: #58a6ff; }
            strong { color: #ffffff; font-weight: bold; }
            ul { margin-left: 20px; color: #b0b0b0; }
            li { margin-bottom: 8px; }
            table { border-collapse: collapse; width: 100%; margin: 20px 0; background: rgba(255,255,255,0.03); }
            th { background: rgba(255,170,0,0.1); color: #ffaa00; padding: 10px; text-align: left; }
            td { border: 1px solid rgba(255,255,255,0.1); padding: 8px; }
            code { background: #161b22; color: #ff7b72; padding: 3px 6px; border-radius: 4px; }
        </style>
        """
        self.report_view.setHtml(master_style + html_body)

    def on_complete(self):
        self.btn_run.setEnabled(True)
        self.btn_save.setEnabled(True)
        self.prog.hide()
        self.log("SUCCESS", "Master Strategic Report Generation Finalized.")

    def save_report(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Report", "Pegasus_Report.md", "Markdown (*.md)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(f"# DiliGenix Intelligence Report: {self.input_subject.text()}\n\n")
                f.write(self.full_report_accumulator)
            QMessageBox.information(self, "Success", "Report exported to vault.")

    def render_market_chart(self, data):
        try:
            # -----------------------------
            # Helper: Card Styling
            # -----------------------------
            def style_card(ax, title):
                ax.set_facecolor('#11161d')
                ax.set_title(title, color='#ffaa00', fontsize=12, weight='bold', pad=12)
                for spine in ax.spines.values():
                    spine.set_visible(True)
                    spine.set_color('#30363d')
                    spine.set_linewidth(1.2)
                ax.tick_params(colors='#d1d5db', labelsize=9)

            # -----------------------------
            # Extract Data
            # -----------------------------
            mp = data["market_projection"]
            years = mp["years"]
            values = mp["values"]
            regional = data["regional_split"]
            swot = data["swot"]
            pestle = data["pestle"]
            moat = data["moat"]

            # -----------------------------
            # Clear Figure
            # -----------------------------
            self.chart_figure.clear()

            # -----------------------------
            # Create Grid (5 blocks)
            # -----------------------------
            ax_market = self.chart_figure.add_subplot(3, 2, 1)
            ax_region = self.chart_figure.add_subplot(3, 2, 2)
            ax_swot = self.chart_figure.add_subplot(3, 2, 3)
            ax_pestle = self.chart_figure.add_subplot(3, 2, 4, polar=True)
            ax_moat = self.chart_figure.add_subplot(3, 2, 5, polar=True)

            # -----------------------------
            # 1. Market Projection
            # -----------------------------
            ax_market.plot(
                years, values,
                color='#ffaa00', linewidth=3, marker='o', markersize=7,
                markerfacecolor='#ffaa00', markeredgecolor='white'
            )
            ax_market.set_xlabel("Year", color='#d1d5db')
            ax_market.set_ylabel("Market Size (USD Bn)", color='#d1d5db')
            ax_market.grid(True, color='#30363d', alpha=0.4)
            style_card(ax_market, "Market Projection")

            # -----------------------------
            # 2. Regional Split (Pie)
            # -----------------------------
            labels = list(regional.keys())
            sizes = list(regional.values())
            colors = ['#58a6ff', '#ff7b72', '#d29922', '#8b949e']
            ax_region.pie(
                sizes, labels=labels, autopct='%1.0f%%',
                startangle=140, colors=colors,
                textprops={'color': 'white', 'fontsize': 9}
            )
            ax_region.axis('equal')
            style_card(ax_region, "Regional Split")

            # -----------------------------
            # 3. SWOT Index (Bar)
            # -----------------------------
            swot_labels = list(swot.keys())
            swot_values = list(swot.values())
            swot_colors = ['#2ecc71', '#e74c3c', '#3498db', '#f1c40f']
            ax_swot.bar(swot_labels, swot_values, color=swot_colors)
            ax_swot.set_ylim(0, 10)
            style_card(ax_swot, "SWOT Index")

            # -----------------------------
            # 4. PESTLE Radar
            # -----------------------------
            pestle_labels = list(pestle.keys())
            pestle_values = list(pestle.values())
            angles = [n / float(len(pestle_labels)) * 2 * 3.14159 for n in range(len(pestle_labels))]
            angles += angles[:1]
            pestle_values += pestle_values[:1]

            ax_pestle.plot(angles, pestle_values, color='#58a6ff', linewidth=2)
            ax_pestle.fill(angles, pestle_values, color='#58a6ff', alpha=0.3)
            ax_pestle.set_thetagrids(
                [a * 180 / 3.14159 for a in angles[:-1]], pestle_labels
            )
            ax_pestle.set_rlabel_position(0)
            style_card(ax_pestle, "PESTLE Radar")

            # -----------------------------
            # 5. Economic Moat Radar
            # -----------------------------
            moat_labels = list(moat.keys())
            moat_values = list(moat.values())
            angles = [n / float(len(moat_labels)) * 2 * 3.14159 for n in range(len(moat_labels))]
            angles += angles[:1]
            moat_values += moat_values[:1]

            ax_moat.plot(angles, moat_values, color='#ffaa00', linewidth=2)
            ax_moat.fill(angles, moat_values, color='#ffaa00', alpha=0.3)
            ax_moat.set_thetagrids(
                [a * 180 / 3.14159 for a in angles[:-1]], moat_labels
            )
            ax_moat.set_rlabel_position(0)
            style_card(ax_moat, "Economic Moat")

            # -----------------------------
            # Layout & Render
            # -----------------------------
            self.chart_figure.subplots_adjust(
                left=0.04, right=0.98, top=0.95, bottom=0.05,
                hspace=0.45, wspace=0.25
            )
            self.chart_canvas.draw()
            self.tabs.setCurrentIndex(2)
            self.log("SUCCESS", "All charts rendered in 5-block dashboard layout.")

        except Exception as e:
            self.log("ERROR", f"Chart render failed: {e}")
            import traceback
            self.log("DEBUG", traceback.format_exc())

    def add_image(self, title, url):
        lbl = QLabel(title)
        lbl.setStyleSheet("color:#ffaa00;")
        pix = QPixmap()

        try:
            r = requests.get(url, timeout=5)
            if r.status_code != 200:
                return

            if not pix.loadFromData(r.content):
                return  # ❗ prevents null pixmap crash

            lbl.setPixmap(pix.scaledToWidth(250, Qt.SmoothTransformation))
            lbl.mousePressEvent = lambda e, d=r.content: self.popup_image(d)
            self.image_layout.addWidget(lbl)

        except Exception as e:
            self.log("WARN", f"Image skipped: {e}")


    def sanitize_for_graphviz(self, text: str) -> str:
        """ Remove characters that Graphviz (Windows) cannot encode. """
        replacements = {
            "≈": "~",
            "–": "-",
            "—": "-",
            "→": "->",
            "←": "<-",
            "“": '"',
            "”": '"',
            "’": "'",
            "‘": "'",
            "•": "*",
            "…": "...",
        }
        for k, v in replacements.items():
            text = text.replace(k, v)
        # Final hard safety: ASCII only
        return text.encode("ascii", "ignore").decode("ascii")

    def add_analytical_card(self, title, summary):
        import re, pydot
        from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QLabel
        from PyQt5.QtCore import QUrl
        
        match = re.search(r"mindmap.*", summary, re.DOTALL | re.IGNORECASE)
        if not match:
            return
            
        summary = self.sanitize_for_graphviz(summary)
        lines = [l.rstrip() for l in summary.splitlines() if l.strip()]
        
        if len(lines) < 2:
            self.log("WARN", f"Analytical map too short for {title}")
            return

        graph = pydot.Dot(graph_type='graph', bgcolor='transparent')

        root = pydot.Node("root", label=title, shape="ellipse",
                          style="filled", fillcolor="#ffaa0044",
                          fontcolor="white")
        graph.add_node(root)

        parent = root
        for line in lines[1:]:
            label = line.strip(" ()")
            node = pydot.Node(label[:40], label=label,
                              shape="box", style="rounded,filled",
                              fillcolor="#0f1117",
                              fontcolor="#e0e0e0")
            graph.add_node(node)
            graph.add_edge(pydot.Edge(parent, node))

        try:
            svg = graph.create_svg().decode("utf-8")
        except Exception as e:
            self.log("WARN", f"Graphviz unavailable, showing text fallback: {e}")
            lbl = QLabel("<pre>" + summary[:1000] + "</pre>")
            lbl.setWordWrap(True)
            box = QGroupBox(title)
            layout = QVBoxLayout(box)
            layout.addWidget(lbl)
            self.kmap_layout.addWidget(box)
            return

        html = f"<html><body style='background:transparent'>{svg}</body></html>"

        box = QGroupBox(title)
        box.setCheckable(True)
        box.setChecked(False)
        layout = QVBoxLayout(box)

        view = QWebEngineView()
        view.setMinimumHeight(400)
        view.setHtml(html, QUrl("about:blank"))

        layout.addWidget(view)
        self.kmap_layout.addWidget(box)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    terminal = PegasusTerminal()
    terminal.show()
    sys.exit(app.exec_())
