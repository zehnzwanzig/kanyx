import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from db import Store
from ui import run

if __name__ == '__main__':
    try:
        store = Store()
    except Exception as exc:
        app = QApplication(sys.argv)
        QMessageBox.critical(None, 'Kanyx – Startfehler', f'Datenverzeichnis konnte nicht geöffnet werden:\n{exc}')
        sys.exit(1)
    sys.exit(run(store))
