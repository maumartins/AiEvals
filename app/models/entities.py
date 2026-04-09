"""Entidades do banco de dados usando SQLModel."""

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Column, Field, Relationship, SQLModel, Text


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class ScenarioType(str, Enum):
    general_qa = "general_qa"
    rag_qa = "rag_qa"
    summarization = "summarization"
    extraction = "extraction"
    classification = "classification"
    safety_adversarial = "safety_adversarial"


class RunStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class MetricStatus(str, Enum):
    computed = "computed"
    skipped = "skipped"
    failed = "failed"


class ScoringPreset(str, Enum):
    general_assistant = "general_assistant"
    rag_grounded_qa = "rag_grounded_qa"
    safety_first = "safety_first"
    extraction_structured = "extraction_structured"


# ---------------------------------------------------------------------------
# Dataset e TestCase
# ---------------------------------------------------------------------------

class Dataset(SQLModel, table=True):
    __tablename__ = "datasets"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str = ""
    category: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    cases: list["TestCase"] = Relationship(back_populates="dataset")


class TestCase(SQLModel, table=True):
    __tablename__ = "test_cases"
    __test__ = False

    id: Optional[int] = Field(default=None, primary_key=True)
    dataset_id: int = Field(foreign_key="datasets.id", index=True)
    name: str = ""
    category: str = ""
    tags: str = ""  # JSON array serializado como string
    user_input: str = Field(sa_column=Column(Text))
    system_prompt: Optional[str] = Field(default=None, sa_column=Column(Text))
    expected_answer: Optional[str] = Field(default=None, sa_column=Column(Text))
    retrieved_context: Optional[str] = Field(default=None, sa_column=Column(Text))
    reference_context: Optional[str] = Field(default=None, sa_column=Column(Text))
    expected_citations: Optional[str] = Field(default=None, sa_column=Column(Text))
    metadata_json: str = "{}"  # JSON serializado
    severity: Severity = Severity.low
    scenario_type: ScenarioType = ScenarioType.general_qa
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    dataset: Optional[Dataset] = Relationship(back_populates="cases")
    results: list["RunCaseResult"] = Relationship(back_populates="test_case")

    def get_tags(self) -> list[str]:
        try:
            return json.loads(self.tags or "[]")
        except Exception:
            return []

    def get_metadata(self) -> dict:
        try:
            return json.loads(self.metadata_json or "{}")
        except Exception:
            return {}


# ---------------------------------------------------------------------------
# PromptTemplate
# ---------------------------------------------------------------------------

class PromptTemplate(SQLModel, table=True):
    __tablename__ = "prompt_templates"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    version: str = "1.0"
    system_template: Optional[str] = Field(default=None, sa_column=Column(Text))
    user_template: str = Field(sa_column=Column(Text))
    description: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# ExperimentRun
# ---------------------------------------------------------------------------

class ExperimentRun(SQLModel, table=True):
    __tablename__ = "experiment_runs"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = ""
    dataset_id: int = Field(foreign_key="datasets.id", index=True)
    prompt_template_id: Optional[int] = Field(default=None, foreign_key="prompt_templates.id")
    provider: str = "mock"
    model: str = "mock"
    temperature: float = 0.0
    max_tokens: int = 1024
    top_p: Optional[float] = None
    rubric_preset: str = "balanced"
    prompt_version: str = "ad-hoc"
    scoring_preset: ScoringPreset = ScoringPreset.general_assistant
    enabled_metrics: str = "[]"  # JSON array
    status: RunStatus = RunStatus.pending
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    results: list["RunCaseResult"] = Relationship(back_populates="run")

    def get_enabled_metrics(self) -> list[str]:
        try:
            return json.loads(self.enabled_metrics or "[]")
        except Exception:
            return []


# ---------------------------------------------------------------------------
# RunCaseResult
# ---------------------------------------------------------------------------

class RunCaseResult(SQLModel, table=True):
    __tablename__ = "run_case_results"

    id: Optional[int] = Field(default=None, primary_key=True)
    run_id: int = Field(foreign_key="experiment_runs.id", index=True)
    test_case_id: int = Field(foreign_key="test_cases.id", index=True)
    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    final_prompt: Optional[str] = Field(default=None, sa_column=Column(Text))
    prompt_version: str = "ad-hoc"
    response: Optional[str] = Field(default=None, sa_column=Column(Text))
    tokens_input: Optional[int] = None
    tokens_output: Optional[int] = None
    cost_usd: Optional[float] = None
    latency_ms: Optional[float] = None
    status: RunStatus = RunStatus.pending
    raw_error: Optional[str] = None
    model_metadata: str = "{}"
    context_hash: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    run: Optional[ExperimentRun] = Relationship(back_populates="results")
    test_case: Optional[TestCase] = Relationship(back_populates="results")
    metric_scores: list["MetricScore"] = Relationship(back_populates="result")
    judge_result: Optional["JudgeResult"] = Relationship(back_populates="result")
    safety_result: Optional["SafetyResult"] = Relationship(back_populates="result")


# ---------------------------------------------------------------------------
# MetricScore
# ---------------------------------------------------------------------------

class MetricScore(SQLModel, table=True):
    __tablename__ = "metric_scores"

    id: Optional[int] = Field(default=None, primary_key=True)
    result_id: int = Field(foreign_key="run_case_results.id", index=True)
    metric_name: str = Field(index=True)
    metric_family: str = ""  # deterministic | reference | rag | judge | safety
    value: Optional[float] = None
    status: MetricStatus = MetricStatus.computed
    skip_reason: Optional[str] = None
    details: str = "{}"  # JSON com detalhes extras

    result: Optional[RunCaseResult] = Relationship(back_populates="metric_scores")

    def get_details(self) -> dict:
        try:
            return json.loads(self.details or "{}")
        except Exception:
            return {}


# ---------------------------------------------------------------------------
# JudgeResult
# ---------------------------------------------------------------------------

class JudgeResult(SQLModel, table=True):
    __tablename__ = "judge_results"

    id: Optional[int] = Field(default=None, primary_key=True)
    result_id: int = Field(foreign_key="run_case_results.id", index=True, unique=True)
    judge_provider: str = ""
    judge_model: str = ""
    judge_prompt: Optional[str] = Field(default=None, sa_column=Column(Text))
    correctness: Optional[float] = None
    completeness: Optional[float] = None
    clarity: Optional[float] = None
    helpfulness: Optional[float] = None
    safety: Optional[float] = None
    instruction_following: Optional[float] = None
    rationale: Optional[str] = Field(default=None, sa_column=Column(Text))
    raw_response: Optional[str] = Field(default=None, sa_column=Column(Text))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    result: Optional[RunCaseResult] = Relationship(back_populates="judge_result")


# ---------------------------------------------------------------------------
# SafetyResult
# ---------------------------------------------------------------------------

class SafetyResult(SQLModel, table=True):
    __tablename__ = "safety_results"

    id: Optional[int] = Field(default=None, primary_key=True)
    result_id: int = Field(foreign_key="run_case_results.id", index=True, unique=True)
    attack_type: str = ""
    passed: bool = True
    explanation: str = ""
    severity: Severity = Severity.low
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    result: Optional[RunCaseResult] = Relationship(back_populates="safety_result")


# ---------------------------------------------------------------------------
# AppSetting
# ---------------------------------------------------------------------------

class AppSetting(SQLModel, table=True):
    __tablename__ = "app_settings"

    key: str = Field(primary_key=True)
    value: str = ""
    description: str = ""
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
