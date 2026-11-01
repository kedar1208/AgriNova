"""Provider abstraction for the assistant.

OfflineProvider  - always available, rule-based (assistant.rules). Nothing leaves the computer.
OpenAICompatibleProvider - optional; works with any server that speaks the OpenAI chat-completions format (hosted free tiers, or a local
Ollama / LM Studio server). It is enabled ONLY by environment variables; no key or model name is ever stored in the code:

    AGRINOVA_LLM_MODEL     model name (required to enable)          e.g. a model offered by your provider
    AGRINOVA_LLM_API_KEY   API key (optional for a local server)
    AGRINOVA_LLM_BASE_URL  default https://api.openai.com/v1        e.g. http://localhost:11434/v1 for a local Ollama server
    AGRINOVA_LLM_NAME      optional display name for the provider

Only the redacted summary from assistant.context.external_payload() is ever sent, and only after the user ticks the consent box."""
import json
import os
import requests
from . import rules


class ProviderError(RuntimeError):
    pass


class OfflineProvider:
    name, external = "offline", False

    def reply(self, question, facts, lang, history=None):
        return rules.answer(question, facts, lang)["text"]


class OpenAICompatibleProvider:
    external = True

    def __init__(self, model, api_key, base_url, label):
        self.model, self.api_key, self.base_url, self.name = model, api_key, base_url.rstrip("/"), label

    def reply(self, question, facts, lang, history=None):
        from .context import external_payload
        from .i18n import LANGS
        system = ("You are the AGRI NOVA farm assistant for Indian farmers. Answer ONLY from the JSON facts below, which are numbers already calculated by the app. "
                  "Never invent numbers, prices, dates or forecasts. If the facts do not contain the answer, say so and name the app page to open (Crop planner, Risk and irrigation, Report). "
                  "Risk scores are heuristic exposure indicators, NOT probabilities of crop loss or disease. Optimiser outputs are simulations, not forecasts or guarantees. "
                  "If weather.live_data is false the weather is synthetic sample data - say so. Keep answers under 140 words, practical, in simple language. "
                  f"Reply in {LANGS[lang]}.\n\nFACTS:\n" + json.dumps(external_payload(facts), ensure_ascii=False))
        msgs = [{"role": "system", "content": system}] + [{"role": h["role"], "content": h["content"][:600]} for h in (history or [])[-6:]] + [{"role": "user", "content": question[:500]}]
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            r = requests.post(f"{self.base_url}/chat/completions", headers=headers, timeout=25,
                              json={"model": self.model, "messages": msgs, "temperature": 0.2, "max_tokens": 450})
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"].strip()
        except (requests.RequestException, KeyError, IndexError, ValueError) as e:
            raise ProviderError(type(e).__name__) from e
        if not text:
            raise ProviderError("empty answer")
        return text


def configured_provider():
    """The external provider if the environment configures one, else None."""
    model = os.environ.get("AGRINOVA_LLM_MODEL", "").strip()
    if not model:
        return None
    base = os.environ.get("AGRINOVA_LLM_BASE_URL", "https://api.openai.com/v1").strip()
    key = os.environ.get("AGRINOVA_LLM_API_KEY", "").strip()
    local = any(h in base for h in ("localhost", "127.0.0.1", "[::1]"))
    if not key and not local:
        return None                      # a hosted provider without a key is not usable - do not pretend it is connected
    return OpenAICompatibleProvider(model, key, base, os.environ.get("AGRINOVA_LLM_NAME", "").strip() or "LLM provider")
