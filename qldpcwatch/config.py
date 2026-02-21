from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field


class QueryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expression: str


class ArxivConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    base_url: str = "http://export.arxiv.org/api/query"
    rate_limit_seconds: float = 3.2
    retries: int = 3
    max_results_per_query: int = 100
    user_agent: str = "qldpcwatch/0.1"


class FiltersConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    categories: list[str] = Field(default_factory=lambda: ["quant-ph", "cs.IT", "math.IT", "cs.DS"])


class OpenAIConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    default_model: str = "gpt-5"
    max_text_chars: int = 120000


class SiteConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = True


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    arxiv: ArxivConfig = Field(default_factory=ArxivConfig)
    queries: list[QueryConfig] = Field(default_factory=list)
    filters: FiltersConfig = Field(default_factory=FiltersConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    site: SiteConfig = Field(default_factory=SiteConfig)


DEFAULT_QUERIES = [
    QueryConfig(expression='abs:"quantum ldpc" AND (abs:decode OR abs:decoding OR abs:decoder)'),
    QueryConfig(
        expression=(
            'abs:"quantum low-density parity-check" '
            "AND (abs:decode OR abs:decoding OR abs:decoder)"
        )
    ),
    QueryConfig(
        expression='abs:"hypergraph product" AND (abs:decode OR abs:decoding OR abs:decoder)'
    ),
    QueryConfig(
        expression='abs:"balanced product" AND (abs:decode OR abs:decoding OR abs:decoder)'
    ),
    QueryConfig(expression='abs:"lifted product" AND (abs:decode OR abs:decoding OR abs:decoder)'),
    QueryConfig(
        expression=(
            'abs:"belief propagation" '
            'AND (abs:"quantum ldpc" OR abs:"quantum low-density parity-check")'
        )
    ),
    QueryConfig(
        expression=(
            '(abs:"small-set-flip" OR abs:SSF OR abs:"union-find" OR abs:MWPM) '
            'AND (abs:"quantum ldpc" OR abs:"quantum low-density parity-check")'
        )
    ),
]


def load_config(path: Path | None = None) -> AppConfig:
    config_path = path or Path("config.yaml")
    raw: dict = {}
    if config_path.exists():
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    cfg = AppConfig.model_validate(raw)
    if not cfg.queries:
        cfg.queries = DEFAULT_QUERIES

    model_override = os.getenv("OPENAI_MODEL")
    if model_override:
        cfg.openai.default_model = model_override

    return cfg
