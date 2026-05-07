from enum import Enum

class AnalysisStatus(Enum):
    """Status of an AI analysis job"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskType(Enum):
    """Type of AI task within the pipeline"""
    EMBEDDING = "embedding"
    EXTRACTION = "extraction"
    CLASSIFICATION = "classification"
    SCORING = "scoring"
    EXPLANATION = "explanation"


class AnalysisQualityTier(Enum):
    """
    Quality tier determines model size and latency

    FAST: ~5s with 7B models
    BALANCED: ~15s with 12B models (default)
    PRECISE: ~45s with 22B models
    """
    FAST = "fast"
    BALANCED = "balanced"
    PRECISE = "precise"

