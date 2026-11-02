import logging

from openai import APIConnectionError, APIStatusError, OpenAI, RateLimitError

logger = logging.getLogger(__name__)


class OpenAIServiceError(RuntimeError):
    pass


def request_completion(api_key: str, model: str, prompt: str) -> str:
    try:
        client = OpenAI(api_key=api_key)
        response = client.responses.create(model=model, input=prompt)
        return response.output_text.strip()
    except (RateLimitError, APIConnectionError, APIStatusError) as exc:
        logger.exception("OpenAI request failed")
        raise OpenAIServiceError(f"Помилка OpenAI API: {exc}") from exc
