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
    SCORING = "scoring"
    EXPLANATION = "explanation"


class AnalysisQualityTier(Enum):
    """Quality tier determines model size and latency: FAST ~5s, BALANCED ~15s, PRECISE ~45s"""
    FAST = "fast"
    BALANCED = "balanced"
    PRECISE = "precise"

