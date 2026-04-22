import os
import sys

PROJECT_HOME = "/home/meet21/mysite/tic_tac_toe"

if PROJECT_HOME not in sys.path:
    sys.path.insert(0, PROJECT_HOME)

os.chdir(PROJECT_HOME)

from app import app as application
