from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True, slots=True)
class MatchScore:
    overall: float
    skills_score: float
    experience_score: float
    location_score: float
    salary_score: float
    explanation: str

    def __post_init__(self) -> None:
        scores = [
            ("overall", self.overall),
            ("skills_score", self.skills_score),
            ("experience_score", self.experience_score),
            ("location_score", self.location_score),
            ("salary_score", self.salary_score),
        ]

        for name, value in scores:
            if not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be a number, got {type(value).__name__}")
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{name} must be between 0.0 and 1.0, got {value}"
                )

        if not isinstance(self.explanation, str):
            raise TypeError(f"explanation must be a string, got {type(self.explanation).__name__}")


@dataclass(frozen=True, slots=True)
class ProviderConfig:
    embedding_provider: str # "ollama", "openai+, etc.
    llm_provider: str
    ollama_base_url: str = "http://localhost:11434"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_llm_model: str = "mistral:7b"
    openai_api_key: str | None = None


class ModelType(str, Enum):
    EMBEDDING = "embedding"
    LLM = "llm"
    CHAT = "chat"


class ProviderType(str, Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
