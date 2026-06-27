import os
import sys

# Add project directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dpmservice.settings')

# Import Django WSGI application
from dpmservice.wsgi import application as django_application
