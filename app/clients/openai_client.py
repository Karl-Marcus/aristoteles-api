from openai import OpenAI

from app.core.config import OPENAI_API_KEY


def get_openai_client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY não foi encontrada. Verifique se o arquivo .env existe e se a chave foi preenchida."
        )

    return OpenAI(api_key=OPENAI_API_KEY)
