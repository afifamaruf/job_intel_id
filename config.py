"""
File berisi konfigurasi

Name: Afif Alli Ma'ruf
Date: 2025
"""

from dotenv import load_dotenv
import os

# Load file .env
load_dotenv()

GLINTS_URL = os.getenv("GLINTS_URL")
JOBSTREET_URL = os.getenv("JOBSTREET_URL")
SCRAPE_DELAY = int(os.getenv("SCRAPE_DELAY", 3))
