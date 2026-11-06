from __future__ import annotations

from dataclasses import dataclass

EXPECTATIONS = ("refuse", "comply")


@dataclass(frozen=True)
class Case:
    """One prompt plus the behaviour the model is expected to show."""

    id: str
    prompt: str
    expect: str
    category: str = "general"
    dialect: str = "msa"
    forbidden_terms: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()


@dataclass
class Result:
    """Outcome of running one case against a model."""

    case: Case
    response: str = ""
    refused: bool = False
    passed: bool = False
    reason: str = ""
    error: str | None = None
