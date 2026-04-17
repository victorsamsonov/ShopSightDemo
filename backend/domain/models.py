from typing import Any, Optional, Final
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv
from dataclasses import dataclass

load_dotenv()

@dataclass(frozen=True)
class Config:
    # Expected env vars (see `.cursor/rules/env_variables.md`)
    OPENAI_API_KEY: Final[Optional[str]] = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: Final[Optional[str]] = os.getenv("OPENAI_MODEL")

    def is_llm_configured(self) -> bool:
        return bool(self.OPENAI_API_KEY and self.OPENAI_MODEL)

class ChatRequest(BaseModel):
    message: str = Field(..., description="User question in plain English.")
    is_followup: bool = Field(default=False, description="Whether this message is a follow-up to the immediately previous query.")
    followup_context: Optional[dict[str, Any]] = Field(
        default=None,
        description="Serialized context of the previous query/response to constrain follow-up answers.",
    )


class KpiPayload(BaseModel):
    label: str
    value: float
    unit: Optional[str] = None


class ChartPayload(BaseModel):
    title: Optional[str] = None
    x: list[str]
    series: list[float]
    series_label: Optional[str] = None


class TablePayload(BaseModel):
    columns: list[str]
    rows: list[list[Any]]


class ChatResponse(BaseModel):
    action_type: str
    output_type: str
    insight: str
    kpi: Optional[KpiPayload] = None
    chart: Optional[ChartPayload] = None
    table: Optional[TablePayload] = None
    followups: list[str] = Field(default_factory=list)

