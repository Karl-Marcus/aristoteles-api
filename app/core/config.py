import os

from dotenv import load_dotenv


load_dotenv()


PROJECT_NAME = "Aristóteles API"
PROJECT_DESCRIPTION = "Back-end da plataforma tutora de redação ENEM."
PROJECT_VERSION = "0.1.0"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5-mini")