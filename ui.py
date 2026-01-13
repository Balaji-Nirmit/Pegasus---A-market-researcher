"""
ui.py
-----
Contains all PyQt5 UI logic for Pegasus.
This file is responsible ONLY for:
- Rendering the interface
- Handling user interaction
- Wiring UI events to the agent
"""

import markdown
from pdf_exporter import export_markdown_to_pdf
from datetime import datetime

from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QTextEdit,
    QLabel,
    QProgressBar,
    QFrame,
    QSplitter,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QFileDialog,
    QMessageBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from agent import RecursiveSectionalAgent


class PegasusTerminal(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pegasus Apex v1.0 | Recursive Sectional Terminal")
        self.resize(1550, 950)

        self.query_nodes = {}
        self.full_report_accumulator = ""

        self._init_ui()
        self._apply_styles()

    # ================================
    # UI Construction
    # ================================

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # ---------- HUD ----------
        hud = QFrame()
        hud.setFixedHeight(40)
        hud_layout = QHBoxLayout(hud)
        self.ticker = QLabel(
            "PEGASUS APEX: SECTIONAL SYNTHESIS ACTIVE | VECTOR INTELLIGENCE ONLINE | RECURSIVE AGENT READY"
        )
        self.ticker.setStyleSheet(
            "color: #ffaa00; font-family: Consolas; font-weight: bold; font-size: 11px;"
        )
        hud_layout.addWidget(self.ticker)
        main_layout.addWidget(hud)

        # ---------- COMMAND PANEL ----------
        cmd_panel = QFrame()
        cmd_panel.setFixedHeight(60)
        cmd_layout = QHBoxLayout(cmd_panel)

        self.input_subject = QLineEdit()
        self.input_subject.setPlaceholderText(
            "ENTER SUBJECT FOR SECTIONAL RECURSIVE ANALYSIS..."
        )

        self.btn_run = QPushButton("DEPLOY AGENT")
        self.btn_run.clicked.connect(self.start_analysis)

        self.btn_save = QPushButton("DOWNLOAD")
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self.save_report)

        cmd_layout.addWidget(QLabel(
            "<b><font color='#ffaa00' size='4'>> </font></b>"
        ))
        cmd_layout.addWidget(self.input_subject)
        cmd_layout.addWidget(self.btn_run)
        cmd_layout.addWidget(self.btn_save)

        main_layout.addWidget(cmd_panel)

        # ---------- WORKSPACE ----------
        splitter = QSplitter(Qt.Horizontal)

        # Left panel: Research Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Research Vectors / Mined Sources"])
        self.tree.setFixedWidth(380)
        splitter.addWidget(self.tree)

        # Right panel: Tabs
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

        self.tabs.addTab(self.insight_view, "Vector Intelligence Blocks")
        self.tabs.addTab(self.report_view, "Master Strategic Analysis")

        splitter.addWidget(self.tabs)
        main_layout.addWidget(splitter)

        # ---------- FOOTER ----------
        self.progress = QProgressBar()
        self.progress.hide()
        main_layout.addWidget(self.progress)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setFixedHeight(100)
        self.log_box.setStyleSheet(
            "background: #000; color: #00FF41; font-family: Consolas; font-size: 10px;"
        )
        main_layout.addWidget(self.log_box)

    # ================================
    # Styling
    # ================================

    def _apply_styles(self):
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background-color: #0b0e14; color: #d1d5db; font-family: Consolas; }
            QLineEdit { background: #0b0e14; border: 1px solid #30363d; padding: 10px; color: white; border-radius: 4px; }
            QPushButton { background: #238636; color: white; font-weight: bold; padding: 10px 15px; border-radius: 4px; }
            QPushButton:hover { background: #2ea043; }
            QPushButton:disabled { background: #1a1f26; color: #444; }
            QTabWidget::pane { border: 1px solid #30363d; }
            QTabBar::tab { background: #161b22; padding: 12px 25px; border: 1px solid #30363d; }
            QTabBar::tab:selected { background: #58a6ff; color: black; font-weight: bold; }
            QTreeWidget { background: #0b0e14; border: 1px solid #30363d; }
            QHeaderView::section { background: #161b22; color: #ffaa00; padding: 5px; border: none; }
            QProgressBar { border: 1px solid #30363d; background: #000; height: 10px; }
            QProgressBar::chunk { background: #ffaa00; }
            """
        )

    # ================================
    # Agent Wiring
    # ================================

    def start_analysis(self):
        target = self.input_subject.text().strip()
        if not target:
            return

        self.tree.clear()
        self.query_nodes.clear()
        self.insight_view.clear()
        self.report_view.clear()
        self.full_report_accumulator = ""

        self.btn_run.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.progress.show()

        self.worker = RecursiveSectionalAgent(target)
        self.worker.log_sig.connect(self.log)
        self.worker.query_sig.connect(self.add_query_node)
        self.worker.url_sig.connect(self.add_url_node)
        self.worker.vector_intel_sig.connect(self.stream_vector_insight)
        self.worker.master_section_sig.connect(self.stream_master_section)
        self.worker.progress_sig.connect(self.progress.setValue)
        self.worker.finished_sig.connect(self.on_complete)
        self.worker.start()

    # ================================
    # UI Update Handlers
    # ================================

    def log(self, tag, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_box.append(
            f"<font color='#ffaa00'>[{timestamp}] <b>{tag}:</b></font> {message}"
        )

    def add_query_node(self, query):
        parent = QTreeWidgetItem(self.tree)
        parent.setText(0, f"VEC: {query.upper()}")
        parent.setForeground(0, QColor("#ffaa00"))
        self.query_nodes[query] = parent
        self.tree.expandItem(parent)

    def add_url_node(self, query, url):
        if query in self.query_nodes:
            child = QTreeWidgetItem(self.query_nodes[query])
            child.setText(0, url)
            child.setForeground(0, QColor("#58a6ff"))

    def stream_vector_insight(self, header, content):
        html = markdown.markdown(
            content,
            extensions=["fenced_code", "tables"],
            output_format="html5"
        )

        block = f"""
        <div style="border-left:3px solid #ffaa00;padding-left:10px;margin-bottom:15px;">
            <div style="color:#ffaa00;font-weight:bold;">RECURSIVE VECTOR: {header.upper()}</div>
            {html}
        </div>
        """
        self.insight_view.append(block)

    def stream_master_section(self, title, content):
        self.tabs.setCurrentIndex(1)
        self.full_report_accumulator += f"## {title}\n\n{content}\n\n"
        html = markdown.markdown(self.full_report_accumulator, extensions=["fenced_code", "tables"])
        self.report_view.setHtml(html)

    def on_complete(self):
        self.btn_run.setEnabled(True)
        self.btn_save.setEnabled(True)
        self.progress.hide()
        self.log("SUCCESS", "Master Strategic Report Generation Finalized.")

    def save_report(self):
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Report",
            "Pegasus_Report",
            "Markdown (*.md);;PDF (*.pdf)",
        )

        if not path:
            return

        title = f"Pegasus Intelligence Report: {self.input_subject.text()}"

        # Normalize extension
        if "Markdown" in selected_filter:
            if not path.lower().endswith(".md"):
                path = path.rsplit(".", 1)[0] + ".md"

            with open(path, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n\n")
            f.write(self.full_report_accumulator)

        elif "PDF" in selected_filter:
            if not path.lower().endswith(".pdf"):
                path = path.rsplit(".", 1)[0] + ".pdf"

            export_markdown_to_pdf(
                filename=path,
                title=title,
                markdown_text=self.full_report_accumulator,
            )

        QMessageBox.information(
            self,
            "Success",
            f"Report exported successfully:\n{path}",
        )
