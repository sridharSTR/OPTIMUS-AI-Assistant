from django.conf import settings
import httpx
import logging
from rest_framework.exceptions import APIException


logger = logging.getLogger(__name__)
LAST_PROVIDER_STATUS = {
    "active_provider": None,
    "fallback_occurred": False,
    "fallback_reason": "",
}


class ProviderAPIException(APIException):
    def __init__(self, detail, status_code=None):
        super().__init__(detail)
        self.provider_status_code = status_code


def get_ai_response(messages):
    _set_provider_status(None, False, "")
    provider = settings.AI_PROVIDER.lower()
    if provider == "openrouter":
        return _openrouter_response(messages)
    if provider == "gemini":
        return _gemini_response(messages)
    if provider == "auto":
        return _auto_response(messages)

    raise APIException("AI_PROVIDER must be one of: auto, openrouter, gemini.")


def get_tavily_context(query):
    if not settings.TAVILY_API_KEY:
        raise APIException("Tavily live search is not configured. Add TAVILY_API_KEY in backend/.env.")

    payload = {
        "api_key": settings.TAVILY_API_KEY,
        "query": query,
        "search_depth": "basic",
        "include_answer": True,
        "include_raw_content": False,
        "max_results": settings.TAVILY_MAX_RESULTS,
    }

    try:
        response = _http_client(timeout=20).post("https://api.tavily.com/search", json=payload)
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise APIException("Tavily live search timed out. Check your network connection and try again.") from exc
    except httpx.HTTPStatusError as exc:
        raise APIException(f"Tavily API error: {_tavily_error_message(exc.response)}") from exc
    except httpx.HTTPError as exc:
        raise APIException(f"Could not connect to Tavily: {exc}") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise APIException("Tavily returned an invalid response.") from exc

    lines = []
    answer = data.get("answer")
    if answer:
        lines.append(f"Summary: {answer}")

    for index, result in enumerate(data.get("results", [])[: settings.TAVILY_MAX_RESULTS], start=1):
        title = result.get("title") or "Untitled"
        url = result.get("url") or ""
        content = result.get("content") or ""
        lines.append(f"{index}. {title}\nURL: {url}\nSnippet: {content}")

    context = "\n\n".join(lines).strip()
    if not context:
        raise APIException("Tavily returned no live search results for this question.")

    return context


def _auto_response(messages):
    errors = []

    if settings.OPENROUTER_API_KEY:
        try:
            text = _openrouter_response(messages)
            _set_provider_status("openrouter", False, "")
            return text
        except ProviderAPIException as exc:
            reason = str(exc.detail)
            logger.warning("OpenRouter failed during auto provider request: %s", reason)
            if not settings.GEMINI_API_KEY and not _should_fallback_from_openrouter(exc):
                _set_provider_status("openrouter", False, reason)
                raise
            _set_provider_status("gemini", True, reason)
            errors.append(f"OpenRouter: {exc}")

    try:
        text = _gemini_response(messages)
        if not LAST_PROVIDER_STATUS["fallback_occurred"]:
            _set_provider_status("gemini", False, "")
        return text
    except APIException as exc:
        errors.append(f"Gemini: {exc}")

    raise APIException(
        "No AI provider is currently available. Add quota/credits or replace the API key for OpenRouter or Gemini. "
        f"Provider errors: {' | '.join(errors)}"
    )


def _openrouter_response(messages):
    if not settings.OPENROUTER_API_KEY:
        raise APIException("OPENROUTER_API_KEY is not configured.")

    if settings.OPENROUTER_API_KEY.startswith(":"):
        raise APIException("OPENROUTER_API_KEY has an extra leading colon. It should start with sk-or.")

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.OPENROUTER_SITE_URL,
        "X-Title": settings.OPENROUTER_APP_NAME,
    }
    payload = {
        "model": settings.OPENROUTER_MODEL,
        "messages": messages,
        "max_tokens": settings.OPENROUTER_MAX_TOKENS,
        "temperature": 0.7,
    }

    try:
        response = _http_client().post(url, headers=headers, json=payload)
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise ProviderAPIException("OpenRouter request timed out. Check your network connection and try again.") from exc
    except httpx.HTTPStatusError as exc:
        detail = _openrouter_error_message(exc.response)
        raise ProviderAPIException(f"OpenRouter API error: {detail}", status_code=exc.response.status_code) from exc
    except httpx.HTTPError as exc:
        raise ProviderAPIException(f"Could not connect to OpenRouter: {exc}") from exc

    data = response.json()
    text = _extract_openrouter_text(data)
    if not text:
        raise ProviderAPIException("OpenRouter returned an empty response.")

    _set_provider_status("openrouter", LAST_PROVIDER_STATUS["fallback_occurred"], LAST_PROVIDER_STATUS["fallback_reason"])
    return text.strip()


def _gemini_response(messages):
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "replace_with_new_gemini_key":
        raise APIException("GEMINI_API_KEY is not configured.")

    prompt = "\n".join(f"{message['role']}: {message['content']}" for message in messages)
    last_error = None
    models = [settings.GEMINI_MODEL, *settings.GEMINI_FALLBACK_MODELS]

    for model in dict.fromkeys(models):
        try:
            text = _gemini_generate(model, prompt)
            if LAST_PROVIDER_STATUS["active_provider"] != "gemini":
                _set_provider_status("gemini", LAST_PROVIDER_STATUS["fallback_occurred"], LAST_PROVIDER_STATUS["fallback_reason"])
            return text
        except APIException as exc:
            last_error = exc
            error_message = str(exc)
            if _is_gemini_quota_error(error_message):
                raise APIException(
                    "Gemini quota exceeded. Wait for the quota window to reset, add billing in Google AI Studio, "
                    "or replace GEMINI_API_KEY in backend/.env."
                ) from exc
            if not _is_retryable_gemini_error(error_message):
                raise

    raise last_error or APIException("Gemini API error.")


def _gemini_generate(model, prompt):
    model_name = model.removeprefix("models/")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{model_name}:generateContent"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = _gemini_http_client().post(
            url,
            params={"key": settings.GEMINI_API_KEY},
            json=payload,
        )
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise APIException("Gemini request timed out. Check your network connection and try again.") from exc
    except httpx.HTTPStatusError as exc:
        detail = _gemini_error_message(exc.response)
        raise APIException(f"Gemini API error: {detail}") from exc
    except httpx.HTTPError as exc:
        raise APIException(f"Could not connect to Gemini: {exc}") from exc

    data = response.json()
    text = _extract_gemini_text(data)
    if not text:
        raise APIException("Gemini returned an empty response.")

    return text.strip()


def _is_retryable_gemini_error(message):
    retryable_phrases = (
        "high demand",
        "temporarily unavailable",
        "try again later",
        "429",
        "503",
    )
    lowered = message.lower()
    return any(phrase in lowered for phrase in retryable_phrases)


def _is_gemini_quota_error(message):
    quota_phrases = (
        "quota exceeded",
        "exceeded your current quota",
        "generate_content_free_tier",
        "rate-limit",
        "rate limit",
    )
    lowered = message.lower()
    return any(phrase in lowered for phrase in quota_phrases)


def _gemini_http_client():
    return _http_client(timeout=30)


def _http_client(timeout=30):
    try:
        import ssl
        import truststore

        ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        return httpx.Client(verify=ssl_context, timeout=timeout)
    except ImportError:
        return httpx.Client(timeout=timeout)


def _openrouter_error_message(response):
    try:
        error = response.json().get("error", {})
        return error.get("message") or error.get("metadata", {}).get("raw") or response.text
    except ValueError:
        return response.text


def _gemini_error_message(response):
    try:
        return response.json().get("error", {}).get("message", response.text)
    except ValueError:
        return response.text


def _tavily_error_message(response):
    try:
        data = response.json()
    except ValueError:
        return response.text

    if isinstance(data, dict):
        return data.get("detail") or data.get("error") or data.get("message") or response.text
    return response.text


def _extract_gemini_text(data):
    candidates = data.get("candidates", [])
    if not candidates:
        return ""

    parts = candidates[0].get("content", {}).get("parts", [])
    return "\n".join(part.get("text", "") for part in parts if part.get("text"))


def _extract_openrouter_text(data):
    choices = data.get("choices", [])
    if not choices:
        return ""

    message = choices[0].get("message", {})
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("text")
        )
    return ""


def _should_fallback_from_openrouter(exc):
    status_code = getattr(exc, "provider_status_code", None)
    return status_code is None or status_code >= 500


def _set_provider_status(active_provider, fallback_occurred, fallback_reason):
    LAST_PROVIDER_STATUS.update(
        {
            "active_provider": active_provider,
            "fallback_occurred": fallback_occurred,
            "fallback_reason": fallback_reason,
        }
    )


def get_provider_status():
    return {
        "configured_provider": settings.AI_PROVIDER,
        "active_provider": LAST_PROVIDER_STATUS["active_provider"],
        "fallback_occurred_last_request": LAST_PROVIDER_STATUS["fallback_occurred"],
        "fallback_reason_last_request": LAST_PROVIDER_STATUS["fallback_reason"],
        "openrouter_configured": bool(settings.OPENROUTER_API_KEY),
        "gemini_configured": bool(settings.GEMINI_API_KEY),
    }
