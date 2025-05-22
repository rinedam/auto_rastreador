import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv("credenciais.env")

# API settings
API_BASE_URL = os.getenv("API_BASE_URL", "http://vstrack.ddns.net/komando/integracao/")
API_USER = os.getenv("API_USER", "")
API_PASSWORD = os.getenv("API_PASSWORD", "")

API2_BASE_URL = os.getenv("API2_BASE_URL", "https://us1.locationiq.com/v1/reverse")
LOCATIONIQ_API_KEY = os.getenv("LOCATIONIQ_API_KEY", "")  # Chave da LocationIQ
