from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config"

load_dotenv(dotenv_path=REPO_ROOT / ".env")


def strip_openai_compat_suffix(base_url: str) -> str:
    """ChatGroq / the native groq SDK append '/openai/v1' internally, so a
    base_url already ending in that suffix (the OpenAI-compatible convention
    used by GROQ_API_URL and scripts/groq_sample_client.py) would double the
    path and 404. Normalize to the host groq/ChatGroq actually expect.
    """
    return base_url.rstrip("/").removesuffix("/openai/v1")


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


class Settings:
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
    @property
    def groq_api_key(self) -> str:
        return self._env.GROQ_API_KEY

    @property
    def groq_base_url(self) -> str:
        return strip_openai_compat_suffix(self._env.GROQ_API_URL)

    @property
    def groq_model(self) -> str:
        return self._env.GROQ_MODEL or self.model_config_yaml["llm"]["default_model"]

    @property
    def llm_temperature(self) -> float:
        return self.model_config_yaml["llm"]["temperature"]

    @property
    def llm_max_tokens(self) -> int:
        return self.model_config_yaml["llm"]["max_tokens"]

    @property
    def llm_timeout_seconds(self) -> int:
        return self.model_config_yaml["llm"]["request_timeout_seconds"]

    @property
    def embeddings_model(self) -> str:
        return self.model_config_yaml["embeddings"]["model"]

    # ---- App ----
    @property
    def app_env(self) -> str:
        return self._env.APP_ENV

    @property
    def categories(self) -> list[str]:
        return self.app_config_yaml["app"]["categories"]

    @property
    def required_fields(self) -> dict:
        return self.app_config_yaml["app"]["required_fields"]

    @property
    def refusal_templates(self) -> dict:
        return self.app_config_yaml["app"]["refusal_templates"]

    @property
    def groundedness_threshold(self) -> float:
        return self.app_config_yaml["app"]["groundedness_threshold"]

    @property
    def llm_groundedness_threshold(self) -> float:
        return self.app_config_yaml["app"]["llm_groundedness_threshold"]

    @property
    def max_retrieval_attempts(self) -> int:
        return self.app_config_yaml["app"]["max_retrieval_attempts"]

    @property
    def reviewer_db_path(self) -> Path:
        return REPO_ROOT / self.app_config_yaml["app"]["reviewer_db_path"]

    @property
    def audit_log_path(self) -> Path:
        return REPO_ROOT / self.app_config_yaml["app"]["audit_log_path"]

    @property
    def thread_store_path(self) -> Path:
        return REPO_ROOT / self.app_config_yaml["app"].get("thread_store_path", "outputs/databases/threads.db")

    @property
    def results_dir(self) -> Path:
        return REPO_ROOT / self.app_config_yaml["app"].get("results_dir", "outputs/results")

    @property
    def drafted_replies_dir(self) -> Path:
        return REPO_ROOT / self.app_config_yaml["app"].get("drafted_replies_dir", "outputs/drafted_replies")

    @property
    def evaluation_reports_dir(self) -> Path:
        return REPO_ROOT / self.app_config_yaml["app"].get("evaluation_reports_dir", "outputs/evaluation_reports")

    @property
    def reviewer_mode(self) -> str:
        return self.app_config_yaml["app"]["reviewer_mode"]

    # ---- Routing ----
    @property
    def routing(self) -> dict:
        return self.routing_rules_yaml["routing"]

    @property
    def refund_rules(self) -> dict:
        return self.routing_rules_yaml["refund_rules"]

    @property
    def escalation_keywords(self) -> dict:
        return self.routing_rules_yaml.get("escalation_keywords", {})

    # ---- Data paths ----
    @property
    def kb_dir(self) -> Path:
        return REPO_ROOT / "data" / "knowledge_base"

    @property
    def tickets_path(self) -> Path:
        return REPO_ROOT / "data" / "synthetic_tickets.json"

    @property
    def golden_dataset_path(self) -> Path:
        return REPO_ROOT / "evaluation" / "golden_dataset.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
