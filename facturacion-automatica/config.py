import os
from dotenv import load_dotenv

load_dotenv()

AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID", "")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "")
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "")
USER_EMAIL = os.getenv("USER_EMAIL", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")

OC_SUBJECT_KEYWORDS = [
    kw.strip()
    for kw in os.getenv(
        "OC_SUBJECT_KEYWORDS",
        "orden de compra,purchase order,OC ,PO-,P.O."
    ).split(",")
    if kw.strip()
]
