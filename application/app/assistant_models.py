from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
    )


class AssistantError(Exception):
    """Safe application error: expose the code, not internal diagnostics."""

    def __init__(self, status_code: int, code: str) -> None:
        super().__init__(code)
        self.status_code = status_code
        self.code = code


class AssistantRequest(StrictModel):
    question: str = Field(min_length=1, max_length=4000)

    @field_validator("question")
    @classmethod
    def reject_blank_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Question must not be blank")
        return value


class LLMDecision(StrictModel):
    action: Literal["propose", "unsupported"]
    sql: str | None = Field(max_length=2000)

    @model_validator(mode="after")
    def validate_decision(self):
        if self.action == "propose":
            if self.sql is None or not self.sql.strip():
                raise ValueError("A proposal requires SQL")

        if self.action == "unsupported" and self.sql is not None:
            raise ValueError("Unsupported questions must not include SQL")

        return self


class QueryOutcome(StrictModel):
    """Normalized successful gateway outcome."""

    status: Literal["completed", "suppressed"]
    count: int | None = Field(ge=0)

    @model_validator(mode="after")
    def validate_outcome(self):
        if self.status == "completed" and self.count is None:
            raise ValueError("Completed result requires a count")

        if self.status == "suppressed" and self.count is not None:
            raise ValueError("Suppressed result must not contain a count")

        return self


class AssistantReply(StrictModel):
    status: Literal[
        "completed",
        "suppressed",
        "unsupported",
        "rejected",
    ]
    proposed_sql: str | None = None
    count: int | None = Field(default=None, ge=0)