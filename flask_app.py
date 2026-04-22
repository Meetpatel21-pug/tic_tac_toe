import sys
path = '/home/meet21/mysite'
if path not in sys.path:
    sys.path.append(path)

from app import app as application
