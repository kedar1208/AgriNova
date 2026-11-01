"""Single entry point used by the view: respond() chooses the provider and always falls back to the offline rules."""
from .providers import OfflineProvider, ProviderError, configured_provider
from . import rules

_OFFLINE = OfflineProvider()


def status():
    """{'external': provider-or-None}. The view uses it to say honestly whether a language model is connected."""
    return {"external": configured_provider()}


def respond(question, facts, lang="en", history=None, allow_external=False):
    """Returns {'text', 'mode': 'offline' | 'llm' | 'fallback'}. 'fallback' = an external provider was allowed but failed."""
    prov = configured_provider() if allow_external else None
    if prov is not None:
        try:
            return {"text": prov.reply(question, facts, lang, history), "mode": "llm", "provider": prov.name}
        except ProviderError:
            return {"text": rules.answer(question, facts, lang)["text"], "mode": "fallback"}
    return {"text": _OFFLINE.reply(question, facts, lang, history), "mode": "offline"}
