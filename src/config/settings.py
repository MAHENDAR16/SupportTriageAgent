from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config"

load_dotenv(dotenv_path=REPO_ROOT / ".env")


# Normalizes a Groq base URL that already carries the OpenAI-compat suffix,
# since ChatGroq appends it internally and would otherwise double the path.
def strip_openai_compat_suffix(base_url: str) -> str:
    """ChatGroq / the native groq SDK append '/openai/v1' internally, so a
    base_url already ending in that suffix (the OpenAI-compatible convention
    used by GROQ_API_URL and scripts/groq_sample_client.py) would double the
    path and 404. Normalize to the host groq/ChatGroq actually expect.
    """
    return base_url.rstrip("/").removesuffix("/openai/v1")


# Reads and parses a YAML config file from the repo's config/ directory.
# Returns an empty dict if the file is empty rather than None.
def _load_yaml(name: str) -> dict:
    path = CONFIG_DIR / name
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


class EnvSettings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    GROQ_API_KEY: str
    GROQ_API_URL: str = "https://api.groq.com/openai/v1"
    GROQ_MODEL: str | None = None
    APP_ENV: str = "development"

    ARIZE_API_KEY: str | None = None
    ARIZE_SPACE_ID: str | None = None
    ARIZE_PROJECT_NAME: str = "support-triage-agent"


class Settings:
    # Loads env vars (raising a clear error if GROQ_API_KEY is missing) plus
    # the three YAML config files, so every property below can read from them.
    def __init__(self) -> None:
        try:
            self._env = EnvSettings()
        except Exception as exc:
            raise RuntimeError(
                "Missing required environment variable: GROQ_API_KEY. "
                "Copy .env.example to .env and fill in your GROQ credentials."
            ) from exc

        self.model_config_yaml = _load_yaml("model_config.yaml")
        self.app_config_yaml = _load_yaml("app_config.yaml")
        self.routing_rules_yaml = _load_yaml("routing_rules.yaml")

    # ---- Groq / LLM ----
    # Returns the Groq API key loaded from the environment.
    @property
    def groq_api_key(self) -> str:
        return self._env.GROQ_API_KEY

    # Returns the Groq base URL, normalized to strip any OpenAI-compat suffix.
    @property
    def groq_base_url(self) -> str:
        return strip_openai_compat_suffix(self._env.GROQ_API_URL)

    # Returns the configured model name, falling back to model_config.yaml's
    # default if GROQ_MODEL isn't set in the environment.
    @property
    def groq_model(self) -> str:
        return self._env.GROQ_MODEL or self.model_config_yaml["llm"]["default_model"]

    # Returns the LLM sampling temperature from model_config.yaml.
    @property
    def llm_temperature(self) -> float:
        return self.model_config_yaml["llm"]["temperature"]

    # Returns the max output tokens per LLM call from model_config.yaml.
    @property
    def llm_max_tokens(self) -> int:
        return self.model_config_yaml["llm"]["max_tokens"]

    # Returns the LLM request timeout in seconds from model_config.yaml.
    @property
    def llm_timeout_seconds(self) -> int:
        return self.model_config_yaml["llm"]["request_timeout_seconds"]

    # Returns the embeddings model name used by the retriever.
    @property
    def embeddings_model(self) -> str:
        return self.model_config_yaml["embeddings"]["model"]

    # ---- App ----
    # Returns the application environment name (e.g. development/production).
    @property
    def app_env(self) -> str:
        return self._env.APP_ENV

    # ---- Arize (optional LLM tracing) ----
    # True once both an API key and space ID are configured -- Arize
    # requires both to route traces to the right space.
    @property
    def arize_enabled(self) -> bool:
        return bool(self._env.ARIZE_API_KEY and self._env.ARIZE_SPACE_ID)

    @property
    def arize_api_key(self) -> str | None:
        return self._env.ARIZE_API_KEY

    @property
    def arize_space_id(self) -> str | None:
        return self._env.ARIZE_SPACE_ID

    @property
    def arize_project_name(self) -> str:
        return self._env.ARIZE_PROJECT_NAME

    # Returns the list of valid ticket categories from app_config.yaml.
    @property
    def categories(self) -> list[str]:
        return self.app_config_yaml["app"]["categories"]

    # Returns the per-category required-identifier-field mapping.
    @property
    def required_fields(self) -> dict:
        return self.app_config_yaml["app"]["required_fields"]

    # Returns the scripted refusal reply templates (abusive, refund_abuse, ...).
    @property
    def refusal_templates(self) -> dict:
        return self.app_config_yaml["app"]["refusal_templates"]

    # Returns the minimum retrieval-similarity score required to AUTO_RESOLVE.
    @property
    def groundedness_threshold(self) -> float:
        return self.app_config_yaml["app"]["groundedness_threshold"]

    # Returns the minimum LLM-judge groundedness score required to pass
    # confidence_recheck without retrying or force-escalating.
    @property
    def llm_groundedness_threshold(self) -> float:
        return self.app_config_yaml["app"]["llm_groundedness_threshold"]

    # Returns how many retrieval retries confidence_recheck allows before
    # force-escalating a low-confidence draft.
    @property
    def max_retrieval_attempts(self) -> int:
        return self.app_config_yaml["app"]["max_retrieval_attempts"]

    # Returns the absolute path to the reviewer SQLite database.
    @property
    def reviewer_db_path(self) -> Path:
        return REPO_ROOT / self.app_config_yaml["app"]["reviewer_db_path"]

    # Returns the absolute path to the append-only audit log JSONL file.
    @property
    def audit_log_path(self) -> Path:
        return REPO_ROOT / self.app_config_yaml["app"]["audit_log_path"]

    # Returns the absolute path to the customer conversation-thread SQLite DB.
    @property
    def thread_store_path(self) -> Path:
        return REPO_ROOT / self.app_config_yaml["app"].get("thread_store_path", "outputs/databases/threads.db")

    # Returns the absolute path to the directory where per-ticket result
    # JSON files are written.
    @property
    def results_dir(self) -> Path:
        return REPO_ROOT / self.app_config_yaml["app"].get("results_dir", "outputs/results")

    # Returns the absolute path to the directory where per-ticket drafted
    # reply text files are written.
    @property
    def drafted_replies_dir(self) -> Path:
        return REPO_ROOT / self.app_config_yaml["app"].get("drafted_replies_dir", "outputs/drafted_replies")

    # Returns the absolute path to the directory where evaluation reports
    # (golden-dataset eval runs) are written.
    @property
    def evaluation_reports_dir(self) -> Path:
        return REPO_ROOT / self.app_config_yaml["app"].get("evaluation_reports_dir", "outputs/evaluation_reports")

    # Returns the reviewer UI mode setting (e.g. sync CLI vs async queue).
    @property
    def reviewer_mode(self) -> str:
        return self.app_config_yaml["app"]["reviewer_mode"]

    # ---- Routing ----
    # Returns the general routing config block from routing_rules.yaml.
    @property
    def routing(self) -> dict:
        return self.routing_rules_yaml["routing"]

    # Returns the refund-specific rules (window, repeat-request threshold, ...).
    @property
    def refund_rules(self) -> dict:
        return self.routing_rules_yaml["refund_rules"]

    # Returns the per-category escalation keyword lists, or {} if undefined.
    @property
    def escalation_keywords(self) -> dict:
        return self.routing_rules_yaml.get("escalation_keywords", {})

    # ---- Data paths ----
    # Returns the absolute path to the knowledge-base markdown directory.
    @property
    def kb_dir(self) -> Path:
        return REPO_ROOT / "data" / "knowledge_base"

    # Returns the absolute path to the synthetic tickets dataset JSON file.
    @property
    def tickets_path(self) -> Path:
        return REPO_ROOT / "data" / "synthetic_tickets.json"

    # Returns the absolute path to the golden dataset used for evaluation.
    @property
    def golden_dataset_path(self) -> Path:
        return REPO_ROOT / "evaluation" / "golden_dataset.json"


# Builds (and memoizes via lru_cache) the single process-wide Settings
# instance, so env/YAML loading only happens once per process.
@lru_cache
def get_settings() -> Settings:
    return Settings()
