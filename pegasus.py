import sys, re, ast, requests, markdown
from datetime import datetime
from ollama import Client
from ddgs import DDGS
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QTextEdit, QLabel, QProgressBar, QFrame, QSplitter, QTabWidget,
    QTreeWidget, QTreeWidgetItem, QFileDialog, QMessageBox, QScrollArea, QGridLayout,
    QGroupBox, QSizePolicy, QDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtWebEngineWidgets import QWebEngineView
import plotly.graph_objects as go
from bs4 import BeautifulSoup
import pydot
import os
# ---------------------------
# Worker: Recursive Sectional Agent
# ---------------------------
class RecursiveSectionalAgent(QThread):
    log_sig = pyqtSignal(str, str)
    query_sig = pyqtSignal(str)
    url_sig = pyqtSignal(str, str)
    vector_intel_sig = pyqtSignal(str, str)
    master_section_sig = pyqtSignal(str, str)
    analytical_sig = pyqtSignal(str, str)
    chart_sig = pyqtSignal(str, object)
    image_sig = pyqtSignal(str, str)
    progress_sig = pyqtSignal(int)
    finished_sig = pyqtSignal()

    def __init__(self, target):
        super().__init__()
        self.target = target
        self.client = Client(
            host='https://ollama.com',
            headers={'Authorization': 'Bearer '+os.environ.get('OLLAMA_API_KEY')}
        )
        self.model = 'gpt-oss:120b'
        self.vector_summaries = []

    def run(self):
        try:
            self.log_sig.emit("SYSTEM", f"AGENT DEPLOYED: {self.target}")

            # --- Phase 1: Generate Research Vectors ---
            v_prompt = (
                f"Generate a Python list of exactly 3 distinct market research queries "
                f"for deep due diligence on: {self.target}. Return ONLY the Python list."
            )
            resp = self.client.chat(self.model, messages=[{'role': 'user', 'content': v_prompt}])
            try:
                match = re.search(r'\[.*\]', resp['message']['content'], re.DOTALL)
                queries = ast.literal_eval(match.group(0)) if match else [self.target]
            except:
                queries = [self.target + " analysis", self.target + " competitors"]

            # --- Phase 2: Gather Vector Intelligence ---
            for idx, q in enumerate(queries):
                self.query_sig.emit(q)
                self.log_sig.emit("AI_THOUGHT", f"Mining Vector: {q}")

                raw_texts = []
                image_links = []
                try:
                    results = DDGS().text(q, max_results=3)
                    for r in results:
                        link = r['href']
                        self.url_sig.emit(q, link)
                        data = requests.get(link, timeout=5).text
                        text = re.sub('<[^<]+?>', '', data)  # basic strip html
                        if text: raw_texts.append(text[:2000])
                        imgs = re.findall(r'<img.*?src=["\'](.*?)["\']', data, re.IGNORECASE)
                        image_links.extend(imgs[:2])                        
                except: pass

                if raw_texts:
                    sub_prompt = f"Summarize verified intelligence for: {q}.\n" + "\n".join(raw_texts)
                    sub_intel = self.client.chat(self.model, messages=[{'role':'user','content':sub_prompt}])
                    intel_txt = sub_intel['message']['content']

                    for img in image_links:
                        self.image_sig.emit(q, img)

                    self.vector_intel_sig.emit(q, intel_txt)
                    self.vector_summaries.append(f"{q}: {intel_txt}")
                    
                    self.log_sig.emit("SYSTEM PROCESSING", "Working on the analytical map...")

                    analytical_prompt = (
                        "You must output ONLY a valid Mermaid diagram for the content below.\n"
                        "Always start with 'mindmap'"
"root((Main Topic))"
"  Child1"
"    Subchild (with parentheses if long)"
"Use exactly 2 spaces per indent level"
"Wrap all node text in ( )"
"No long run-on lines; break into hierarchy"
                        f"{q}\n\n"
                        + "\n".join(intel_txt))
                    analytical_intel = self.client.chat(self.model, messages=[{'role':'user','content':analytical_prompt}])
                    self.analytical_sig.emit(q, analytical_intel['message']['content'])  # first sentence as summary

                self.progress_sig.emit(int(((idx+1)/len(queries))*50))

            # --- Phase 3: Master Section ---
            report_sections = [
                ("Executive Summary","High-level overview"),
                ("SWOT Analysis","Strengths, Weaknesses, Opportunities, Threats"),
                ("PESTLE Analysis","Political, Economic, Social, Technological, Legal, Environmental"),
                ("Porter's Five Forces","Industry competitiveness"),
                ("Moat & Defensibility","Long-term advantage"),
                ("Competitive Landscape","Market share & competitors"),
                ("Strategic Outlook","Projections 2026-2030")
            ]
            context_for_master = "\n\n".join(self.vector_summaries)
            for i,(title,instruction) in enumerate(report_sections):
                self.log_sig.emit("AI", f"Streaming Master Section: {title}")
                section_prompt = (
                    f"Write '{title}' section for {self.target} using ONLY below research data:\n"
                    f"{context_for_master[:10000]}"
                )
                section_resp = self.client.chat(self.model, messages=[{'role':'user','content':section_prompt}])
                self.master_section_sig.emit(title, section_resp['message']['content'])
                self.progress_sig.emit(50+int(((i+1)/len(report_sections))*50))

            # --- Charts ---
            # Monte Carlo
            monte_values = [100,120,90,130,110,125,95,140,115,105]
            fig = go.Figure()
            fig.add_trace(go.Histogram(x=monte_values, nbinsx=10, marker_color="#ffaa00"))
            fig.update_layout(title="Monte Carlo Forecast", autosize=True)
            self.chart_sig.emit("Monte Carlo", fig)

            # SWOT Radar
            swot = {"Strengths":8,"Weaknesses":5,"Opportunities":9,"Threats":4}
            fig2 = go.Figure(go.Barpolar(
                r=list(swot.values()), theta=[0,90,180,270], width=[90]*4,
                marker_color=["#ffaa00","#ff5555","#55ff55","#5555ff"]
            ))
            fig2.update_layout(polar=dict(radialaxis=dict(range=[0,10])), showlegend=False, title="SWOT Analysis", autosize=True)
            self.chart_sig.emit("SWOT", fig2)

            # PESTLE Radar
            pestle = {"Political":6,"Economic":7,"Social":5,"Technological":8,"Legal":6,"Environmental":7}
            fig3 = go.Figure()
            fig3.add_trace(go.Scatterpolar(r=list(pestle.values()), theta=list(pestle.keys()), fill='toself', name="PESTLE"))
            fig3.update_layout(title="PESTLE Analysis", polar=dict(radialaxis=dict(visible=True,range=[0,10])), autosize=True)
            self.chart_sig.emit("PESTLE", fig3)

            # Moat
            moat = {"Brand":8,"Tech":7,"Network":9,"Cost":6}
            fig4 = go.Figure([go.Bar(x=list(moat.keys()), y=list(moat.values()), marker_color="#ffaa00")])
            fig4.update_layout(title="Moat & Defensibility", yaxis=dict(range=[0,10]), autosize=True)
            self.chart_sig.emit("Moat", fig4)

            self.finished_sig.emit()
            self.log_sig.emit("SUCCESS", "All sections, charts, and analytical maps generated.")

        except Exception as e:
            self.log_sig.emit("ERROR", f"Agent Error: {str(e)}")


# ---------------------------
# UI: Pegasus Terminal
# ---------------------------
class PegasusTerminal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pegasus Apex v4 | Market Intelligence Terminal")
        self.resize(1900, 1000)
        self.query_nodes = {}
        self.full_report_accumulator = ""
        self.analytical_seen = set()
        self.init_ui()
        self.apply_styles()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # HUD
        hud = QFrame()
        hud.setFixedHeight(40)
        hud_layout = QHBoxLayout(hud)
        self.ticker = QLabel("PEGASUS APEX: INTERACTIVE TERMINAL | RECURSIVE AGENT READY")
        self.ticker.setStyleSheet("color: #ffaa00; font-family: 'Consolas'; font-weight: bold; font-size: 11px;")
        hud_layout.addWidget(self.ticker)
        main_layout.addWidget(hud)

        # Command panel
        cmd_panel = QFrame()
        cmd_panel.setFixedHeight(60)
        cmd_layout = QHBoxLayout(cmd_panel)
        self.input_subject = QLineEdit()
        self.input_subject.setPlaceholderText("Enter subject for analysis...")
        self.btn_run = QPushButton("DEPLOY AGENT")
        self.btn_run.clicked.connect(self.start_analysis)
        self.btn_save = QPushButton("DOWNLOAD REPORT")
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self.save_report)
        cmd_layout.addWidget(self.input_subject)
        cmd_layout.addWidget(self.btn_run)
        cmd_layout.addWidget(self.btn_save)
        main_layout.addWidget(cmd_panel)

        # Splitter layout
        splitter = QSplitter(Qt.Horizontal)

        # Left: Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Vectors & Sources"])
        splitter.addWidget(self.tree)

        # Center Tabs: Insights + Master Report
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        self.center_tabs = QTabWidget()
        self.insight_view = QTextEdit()
        self.insight_view.setReadOnly(True)
        self.report_view = QTextEdit()
        self.report_view.setReadOnly(True)
        self.center_tabs.addTab(self.insight_view, "Vector Insights")
        self.center_tabs.addTab(self.report_view, "Master Report")
        center_layout.addWidget(self.center_tabs)
        splitter.addWidget(center_widget)

        # Right Tabs: analytical Map + Charts + Images
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        self.right_tabs = QTabWidget()

        # analytical Map
        self.kmap_scroll = QScrollArea()
        self.kmap_container = QWidget()
        self.kmap_layout = QVBoxLayout(self.kmap_container)
        self.kmap_scroll.setWidgetResizable(True)
        self.kmap_scroll.setWidget(self.kmap_container)
        self.right_tabs.addTab(self.kmap_scroll, "analytical Map")

        # Charts
        self.charts_tabs = QTabWidget()
        self.chart_views = {}
        for c in ["Monte Carlo","SWOT","PESTLE","Moat"]:
            view = QWebEngineView()
            self.chart_views[c] = view
            self.charts_tabs.addTab(view, c)
        self.right_tabs.addTab(self.charts_tabs, "Charts")

        # Images
        self.image_scroll = QScrollArea()
        self.image_container = QWidget()
        self.image_layout = QVBoxLayout(self.image_container)
        self.image_scroll.setWidgetResizable(True)
        self.image_scroll.setWidget(self.image_container)
        self.right_tabs.addTab(self.image_scroll, "Reference Images")

        right_layout.addWidget(self.right_tabs)
        splitter.addWidget(right_widget)

        splitter.setStretchFactor(0,1)
        splitter.setStretchFactor(1,3)
        splitter.setStretchFactor(2,2)
        main_layout.addWidget(splitter)

        # Progress & Logs
        self.prog = QProgressBar()
        self.prog.hide()
        main_layout.addWidget(self.prog)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setFixedHeight(100)
        main_layout.addWidget(self.log_box)

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget { background-color: #0b0e14; color: #d1d5db; font-family: 'Consolas'; }
            QLineEdit { background:#0b0e14; border:1px solid #30363d; padding:5px; color:white; border-radius:4px; }
            QPushButton { background:#238636; color:white; font-weight:bold; padding:5px; border-radius:4px; }
            QPushButton:hover { background:#2ea043; }
            QPushButton:disabled { background:#1a1f26; color:#444; }
            QTabWidget::pane { border:1px solid #30363d; }
            QTreeWidget { background:#0b0e14; border:1px solid #30363d; }
            QProgressBar { border:1px solid #30363d; background:#000; height:10px; }
            QProgressBar::chunk { background:#ffaa00; }
            QTextEdit { background:#0b0e14; color:#d1d5db; }
        """)

    # -----------------
    # Event Handlers
    # -----------------
    def start_analysis(self):
        target = self.input_subject.text()
        if not target: return
        self.tree.clear()
        self.insight_view.clear()
        self.report_view.clear()
        self.full_report_accumulator = ""
        self.btn_run.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.analytical_seen.clear()
        self.prog.show()

        # Clear previous analytical map, images
        for i in reversed(range(self.kmap_layout.count())):
            self.kmap_layout.itemAt(i).widget().deleteLater()
        for i in reversed(range(self.image_layout.count())):
            self.image_layout.itemAt(i).widget().deleteLater()

        self.worker = RecursiveSectionalAgent(target)
        self.worker.log_sig.connect(self.log)
        self.worker.query_sig.connect(self.add_query_node)
        self.worker.url_sig.connect(self.add_url_node)
        self.worker.vector_intel_sig.connect(self.stream_vector_insight)
        self.worker.master_section_sig.connect(self.stream_master_section)
        self.worker.analytical_sig.connect(self.add_analytical_card)
        self.worker.chart_sig.connect(self.display_chart)
        self.worker.image_sig.connect(self.add_image)
        self.worker.progress_sig.connect(self.prog.setValue)
        self.worker.finished_sig.connect(self.on_complete)
        self.worker.start()

    def add_query_node(self,q):
        parent = QTreeWidgetItem(self.tree)
        parent.setText(0,f"VEC: {q.upper()}")
        parent.setForeground(0,QColor("#ffaa00"))
        self.query_nodes[q] = parent
        self.tree.expandItem(parent)

    def add_url_node(self,q,url):
        if q in self.query_nodes:
            child = QTreeWidgetItem(self.query_nodes[q])
            child.setText(0,url)
            child.setForeground(0,QColor("#58a6ff"))

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
        self.center_tabs.setCurrentIndex(1)
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

    def add_analytical_card(self, title, summary):
        import re
        from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QLabel
        from PyQt5.QtWebEngineWidgets import QWebEngineView
        from PyQt5.QtCore import QUrl
        import pydot

        key = (title + summary).lower()
        if key in self.analytical_seen:
            return
        self.analytical_seen.add(key)

        # Try to extract mermaid-like structure or fallback to text summary
        match = re.search(r"```mermaid\s*(.*?)```", summary, re.DOTALL | re.IGNORECASE)
        if not match:
            self.log("WARNING", f"No diagram block in {title}")
            # Fallback: show raw summary as text
            lbl = QLabel(summary[:800] + "...")
            lbl.setWordWrap(True)
            box = QGroupBox(title)
            layout = QVBoxLayout(box)
            layout.addWidget(lbl)
            self.kmap_layout.addWidget(box)
            return

        raw_text = match.group(1).strip()

        # Very basic parser: assume first line is root, then indented children
        lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
        if not lines:
            return

        root_label = lines[0].replace("mindmap", "").replace("root", "").strip("() ").strip() or title

        graph = pydot.Dot(graph_type='graph', rankdir='TB', bgcolor='transparent')
        root_node = pydot.Node("root", label=root_label, shape="ellipse", style="filled", fillcolor="#ffaa0044", fontcolor="white")
        graph.add_node(root_node)

        current_parent = root_node
        prev_indent = 0

        for line in lines[1:]:
            indent = len(line) - len(line.lstrip())
            label = line.strip().strip("()[]").strip()

            if not label:
                continue

            node = pydot.Node(label[:60], label=label, shape="box", style="rounded,filled", fillcolor="#0f1117", fontcolor="#e0e0e0", fontsize="12")
            graph.add_node(node)
            graph.add_edge(pydot.Edge(current_parent, node))

            if indent > prev_indent:
                current_parent = node  # go deeper
            elif indent < prev_indent:
                # go up - simplistic, may need stack for real trees
                current_parent = root_node
            prev_indent = indent

        try:
            svg_str = graph.create_svg().decode('utf-8')
        except Exception as e:
            self.log("ERROR", f"Graphviz failed: {e}")
            svg_str = f"<pre>{summary[:500]}</pre>"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="margin:0; background:transparent; padding:12px;">
            {svg_str}
        </body>
        </html>
        """

        box = QGroupBox(title)
        box.setCheckable(True)
        box.setChecked(False)
        layout = QVBoxLayout(box)

        view = QWebEngineView()
        view.setMinimumHeight(500)
        view.setHtml(html, QUrl("about:blank"))

        layout.addWidget(view)
        self.kmap_layout.addWidget(box)  



    def normalize_mermaid_mindmap(self, code):
        lines = [line.rstrip() for line in code.splitlines() if line.strip() and not line.strip().startswith('//')]

        if not lines or not lines[0].strip().lower().startswith('mindmap'):
            lines.insert(0, 'mindmap')

        # Force root if missing or malformed
        if len(lines) > 1 and not lines[1].startswith((' ', '\t')):
            root_text = lines[1].strip('root()').strip(')').strip('(').strip()
            lines[1] = f'  root(({root_text}))'

        # Try to indent child lines properly (very crude – assumes long lines are children)
        fixed = []
        current_indent = 0
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith(('root', 'mindmap')):
                fixed.append(line)
                continue

            # Count leading spaces/tabs
            indent_level = len(line) - len(stripped)
            if indent_level == 0:
                # No indent → make it level 2 under root
                fixed.append('  ' + stripped)
            elif indent_level % 2 != 0:
                # Odd indent → normalize to 2 spaces per level
                level = indent_level // 2 + 1
                fixed.append('  ' * level + stripped)
            else:
                fixed.append(line)

        # Ensure nodes have ( ) if missing (mindmap requirement for most nodes)
        final = []
        for line in fixed:
            stripped = line.lstrip()
            if stripped and not stripped.startswith(('root', 'mindmap')) and '(' not in stripped:
                # Very naive: wrap the whole text in ( )
                parts = stripped.split(None, 1)
                if len(parts) > 1:
                    line = line.replace(stripped, parts[0] + f'({parts[1]})')
                else:
                    line = line.replace(stripped, f'({stripped})')
            final.append(line)

        normalized = '\n'.join(final)
        return normalized
    def display_chart(self,name,fig):
        html = fig.to_html(include_plotlyjs='cdn', full_html=False)
        if name in self.chart_views:
            self.chart_views[name].setHtml(html)

    def add_image(self,title,url):
        lbl = QLabel(title)
        lbl.setStyleSheet("color:#ffaa00;")
        pix = QPixmap()
        try:
            data = requests.get(url, timeout=5).content
            pix.loadFromData(data)
            lbl.setPixmap(pix.scaledToWidth(250,Qt.SmoothTransformation))
            lbl.mousePressEvent = lambda e, d=data: self.popup_image(d)
        except: pass
        self.image_layout.addWidget(lbl)
    
    def popup_image(self, data):
        dlg = QDialog(self)
        dlg.setWindowTitle("Image Viewer")
        v = QVBoxLayout(dlg)
        lbl = QLabel()
        pix = QPixmap()
        pix.loadFromData(data)
        lbl.setPixmap(pix.scaledToWidth(500, Qt.SmoothTransformation))
        v.addWidget(lbl)
        dlg.exec_()

    def on_complete(self):
        self.btn_run.setEnabled(True)
        self.btn_save.setEnabled(True)
        self.prog.hide()
        self.log("SUCCESS","Analysis complete.")

    def save_report(self):
        path,_ = QFileDialog.getSaveFileName(self,"Export Report","Pegasus_Report.md","Markdown (*.md)")
        if path:
            with open(path,'w',encoding='utf-8') as f:
                f.write(f"# DiliGenix Intelligence Report: {self.input_subject.text()}\n\n")
                f.write(self.full_report_accumulator)
            QMessageBox.information(self,"Success","Report exported.")

    def log(self,tag,msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"<font color='#ffaa00'>[{ts}] <b>{tag}:</b></font> <font color='green'>{msg}</font>")


# ---------------------------
# Run Application
# ---------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    terminal = PegasusTerminal()
    terminal.show()
    sys.exit(app.exec_())
