from PySide6.QtWidgets import QLabel, QPlainTextEdit

from .theme import STATE_STYLE


class StatusBadge(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.set_state("stopped")

    def set_state(self, state: str) -> None:
        color, text = STATE_STYLE.get(state, STATE_STYLE["stopped"])
        self.setText(f'<span style="color:{color}; font-size:13pt;">●</span> {text}')


class LogView(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Log")
        self.setReadOnly(True)
        self.setMaximumBlockCount(5000)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)

    def append_text(self, text: str) -> None:
        bar = self.verticalScrollBar()
        at_bottom = bar.value() >= bar.maximum() - 4
        self.appendPlainText(text)
        if at_bottom:
            bar.setValue(bar.maximum())


def format_uptime(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
