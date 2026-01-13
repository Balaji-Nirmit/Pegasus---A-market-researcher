import sys
from PyQt5.QtWidgets import QApplication
from ui import PegasusTerminal


def main():
    app = QApplication(sys.argv)
    terminal = PegasusTerminal()
    terminal.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
