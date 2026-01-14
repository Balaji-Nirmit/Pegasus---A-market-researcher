import sys
import trafilatura
import ast
import re
import markdown
from datetime import datetime
from ollama import Client
from ddgs import DDGS 
import os

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLineEdit, QTextEdit, 
                             QLabel, QProgressBar, QFrame, QSplitter, 
                             QTabWidget, QTreeWidget, QTreeWidgetItem,
                             QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor


# 1. RECURSIVE SECTIONAL ENGINE (The Worker)

class RecursiveSectionalAgent(QThread):
    log_sig = pyqtSignal(str, str)
    query_sig = pyqtSignal(str)     
    url_sig = pyqtSignal(str, str)  
    vector_intel_sig = pyqtSignal(str, str) # Vector Header, Content
    master_section_sig = pyqtSignal(str, str) # Section Title, Section Content
    progress_sig = pyqtSignal(int)
    finished_sig = pyqtSignal()

    def __init__(self, target):
        super().__init__()
        self.target = target
        self.client = Client(
            host='https://ollama.com',
            headers={'Authorization': 'Bearer ' + os.environ.get('OLLAMA_API_KEY')}
        )
        self.model = 'gpt-oss:120b'
        self.vector_summaries = [] # Stores summarized intel from each query

    def run(self):
        try:
            self.log_sig.emit("SYSTEM", f"AGENT DEPLOYED: {self.target}")
            
            # --- PHASE 1: RESEARCH VECTOR GENERATION ---
            v_prompt = (
                "Generate a Python list of exactly 7 distinct market research queries "
                f"for deep due diligence on: {self.target}. Return ONLY the Python list."
            )
            resp = self.client.chat(self.model, messages=[{'role': 'user', 'content': v_prompt}])
            try:
                match = re.search(r'\[.*\]', resp['message']['content'], re.DOTALL)
                queries = ast.literal_eval(match.group(0)) if match else [self.target]
            except:
                queries = [self.target + " analysis", self.target + " competitors"]

            # --- PHASE 2: PER-VECTOR INTELLIGENCE (Building Blocks) ---
            for idx, q in enumerate(queries):
                self.query_sig.emit(q)
                self.log_sig.emit("AI_THOUGHT", f"Mining Vector: {q}")
                
                raw_texts = []
                try:
                    results = DDGS().text(q, max_results=3)
                    for r in results:
                        link = r['href']
                        self.url_sig.emit(q, link)
                        data = trafilatura.extract(trafilatura.fetch_url(link))
                        if data: raw_texts.append(data[:2000])
                except: pass

                if raw_texts:
                    # sub_prompt = f"Summarize the core intelligence for the query '{q}' based on these sources:\n" + "\n".join(raw_texts)
                    sub_prompt = f"Summarize verified intelligence for: {q}. Focus only on consensus-backed facts.\n" + "\n".join(raw_texts)
                    sub_intel = self.client.chat(self.model, messages=[{'role': 'user', 'content': sub_prompt}])
                    intel_txt = sub_intel['message']['content']
                    
                    self.vector_intel_sig.emit(q, intel_txt)
                    self.vector_summaries.append(f"RESEARCH DATA FOR {q}: {intel_txt}")
                
                self.progress_sig.emit(int(((idx+1)/len(queries))*50))

            # --- PHASE 3: SECTIONAL MASTER SYNTHESIS (Streaming sections) ---
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
                
                section_resp = self.client.chat(self.model, messages=[{'role': 'user', 'content': section_prompt}])
                section_content = section_resp['message']['content']
                
                # Signal the UI to append this section immediately
                self.master_section_sig.emit(title, section_content)
                self.progress_sig.emit(50 + int(((i+1)/len(report_sections))*50))

            self.finished_sig.emit()
            self.log_sig.emit("SUCCESS", "Terminal has vaulted all intelligence sections.")

        except Exception as e:
            self.log_sig.emit("ERROR", f"Agent Error: {str(e)}")


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

        # Center/Right: Multi-Tab Intelligence
        self.tabs = QTabWidget()
        
        # Tab 1: Vector Insights (The blocks)
        self.insight_view = QTextEdit()
        self.insight_view.setReadOnly(True)
        self.insight_view.setPlaceholderText("Individual vector intelligence will populate here during the crawl...")
        
        # Tab 2: Master Strategic Report (The streamed final)
        self.report_view = QTextEdit()
        self.report_view.setReadOnly(True)
        self.report_view.setPlaceholderText("The Master Report will stream here section-by-section...")
        
        self.tabs.addTab(self.insight_view, "Vector Intelligence Blocks")
        self.tabs.addTab(self.report_view, "Master Strategic Analysis")
        splitter.addWidget(self.tabs)
        
        main_layout.addWidget(splitter)

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
            QMainWindow, QWidget { background-color: #0b0e14; color: #d1d5db; font-family: 'Consolas', monospace; }
            QLineEdit { background: #0b0e14; border: 1px solid #30363d; padding: 10px; color: white; border-radius: 4px; }
            QPushButton { background: #238636; color: white; font-weight: bold; padding: 10px 15px; border-radius: 4px; }
            QPushButton:hover { background: #2ea043; }
            QPushButton:disabled { background: #1a1f26; color: #444; }
            QTabWidget::pane { border: 1px solid #30363d; }
            QTabBar::tab { background: #161b22; padding: 12px 25px; border: 1px solid #30363d; margin-right: 2px; }
            QTabBar::tab:selected { background: #58a6ff; color: black; font-weight: bold; }
            QTreeWidget { background: #0b0e14; border: 1px solid #30363d; }
            QHeaderView::section { background: #161b22; color: #ffaa00; padding: 5px; border: none; }
            QProgressBar { border: 1px solid #30363d; background: #000; height: 10px; }
            QProgressBar::chunk { background: #ffaa00; }
        """)

    def log(self, tag, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"<font color='#ffaa00'>[{ts}] <b>{tag}:</b></font> {msg}")

    def start_analysis(self):
        target = self.input_subject.text()
        if not target: return
        
        self.tree.clear()
        self.query_nodes = {}
        self.insight_view.clear()
        self.report_view.clear()
        self.full_report_accumulator = ""
        self.btn_run.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.prog.show()
        
        self.worker = RecursiveSectionalAgent(target)
        self.worker.log_sig.connect(self.log)
        self.worker.query_sig.connect(self.add_query_node)
        self.worker.url_sig.connect(self.add_url_node)
        self.worker.vector_intel_sig.connect(self.stream_vector_insight)
        self.worker.master_section_sig.connect(self.stream_master_section)
        self.worker.finished_sig.connect(self.on_complete)
        self.worker.progress_sig.connect(self.prog.setValue)
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
            .vector-header { 
                color: #ffaa00; 
                font-size: 14px; 
                font-weight: bold; 
                text-transform: uppercase;
                letter-spacing: 1px;
                border-left: 3px solid #ffaa00;
                padding-left: 10px;
                margin-bottom: 10px;
            }
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
            body { 
                font-family: 'Segoe UI', sans-serif; 
                color: #e0e0e0; 
                background-color: #0b0e14; 
                line-height: 1.6;
            }
            h1 { color: #ffffff; text-align: center; margin-bottom: 30px; }
            h2 { 
                color: #ffaa00; 
                text-shadow: 0 0 12px rgba(255, 170, 0, 0.4); 
                border-bottom: 1px solid rgba(255, 170, 0, 0.2);
                padding-bottom: 5px;
                margin-top: 30px;
            }
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    terminal = PegasusTerminal()
    terminal.show()
    sys.exit(app.exec_())