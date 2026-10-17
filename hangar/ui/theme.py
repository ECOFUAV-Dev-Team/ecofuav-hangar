from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

STATE_STYLE = {
    "stopped": ("#6b7280", "Kapalı"),
    "starting": ("#f59e0b", "Başlıyor…"),
    "running": ("#22c55e", "Çalışıyor"),
    "stopping": ("#f59e0b", "Durduruluyor…"),
    "crashed": ("#ef4444", "Hata ile kapandı"),
}

STYLESHEET = """
QWidget { font-size: 10pt; }
#Sidebar { background: #15181e; border: none; }
#Sidebar::item { padding: 12px 16px; color: #c9d1d9; }
#Sidebar::item:selected { background: #2563eb; color: white; }
#Brand { padding: 18px 16px 14px 16px; border-bottom: 1px solid #262c36; }
#PageTitle { font-size: 15pt; font-weight: 600; }
#Card { background: #1f242c; border: 1px solid #30363d; border-radius: 8px; }
#Card[selected="true"] { border: 1px solid #3b82f6; }
#CardTitle { font-size: 11pt; font-weight: 600; }
#Muted { color: #8b949e; }
QPushButton { padding: 5px 12px; border-radius: 5px; background: #2d333b; border: 1px solid #444c56; }
QPushButton:hover { background: #373e47; }
QPushButton:disabled { color: #6e7681; background: #22272e; }
QPushButton#Primary { background: #2563eb; border-color: #2563eb; color: white; }
QPushButton#Primary:hover { background: #1d4ed8; }
QPushButton#Danger { background: #7f1d1d; border-color: #991b1b; color: white; }
QPushButton#Danger:hover { background: #991b1b; }
QPushButton#Primary:disabled, QPushButton#Danger:disabled { background: #22272e; border-color: #30363d; color: #6e7681; }
QPlainTextEdit#Log { font-family: "DejaVu Sans Mono", "Ubuntu Mono", monospace; font-size: 9pt; background: #0d1117; }
"""


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    p = QPalette()
    p.setColor(QPalette.Window, QColor("#1a1d23"))
    p.setColor(QPalette.WindowText, QColor("#e6edf3"))
    p.setColor(QPalette.Base, QColor("#0d1117"))
    p.setColor(QPalette.AlternateBase, QColor("#161b22"))
    p.setColor(QPalette.Text, QColor("#e6edf3"))
    p.setColor(QPalette.Button, QColor("#2d333b"))
    p.setColor(QPalette.ButtonText, QColor("#e6edf3"))
    p.setColor(QPalette.Highlight, QColor("#2563eb"))
    p.setColor(QPalette.HighlightedText, QColor("white"))
    p.setColor(QPalette.ToolTipBase, QColor("#1f242c"))
    p.setColor(QPalette.ToolTipText, QColor("#e6edf3"))
    p.setColor(QPalette.PlaceholderText, QColor("#6e7681"))
    p.setColor(QPalette.Disabled, QPalette.Text, QColor("#6e7681"))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#6e7681"))
    app.setPalette(p)
    app.setStyleSheet(STYLESHEET)
