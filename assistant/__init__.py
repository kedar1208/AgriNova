"""AGRI NOVA farm assistant (English / Hindi / Marathi).

Deliberately separate from engine/: it only READS numbers the engines already produced (via assistant.context) and never
recalculates risk, irrigation or optimisation. Two interchangeable back-ends sit behind assistant.service.respond():
  * an offline rule-based explainer (always available, no network), and
  * an optional OpenAI-compatible LLM provider, enabled only by environment variables (see assistant/providers.py).
"""
