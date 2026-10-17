"""sudo -A tarafından çağrılan şifre penceresi. Şifreyi stdout'a yazar."""
import sys

from PySide6.QtWidgets import QApplication, QInputDialog, QLineEdit


def main() -> int:
    app = QApplication(sys.argv[:1])
    prompt = sys.argv[1] if len(sys.argv) > 1 else "Şifre:"
    text, ok = QInputDialog.getText(
        None, "Yönetici izni gerekli",
        "Kurulum yönetici (sudo) izni istiyor.\n" + prompt,
        QLineEdit.EchoMode.Password,
    )
    if not ok:
        return 1
    sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
