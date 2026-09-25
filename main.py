"""PDF Studio giris noktasi.

Kullanim:
    python main.py [dosya.pdf]
"""

import sys

from pdfstudio.mainwindow import run

if __name__ == "__main__":
    sys.exit(run(sys.argv))
