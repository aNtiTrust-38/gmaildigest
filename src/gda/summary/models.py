"""
Data models for the summarization module.

This module defines Pydantic models for summarization results, providers,
options, and other types used in the summarization process.
"""
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Union, Any, Literal

from pydantic import BaseModel, Field, validator, root_validator


class SummaryProvider(str, Enum):
    """Supported summarization providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    SUMY = "sumy"
    HEURISTIC = "heuristic"


class SummaryType(str, Enum):
    """Types of summaries."""
    SINGLE_EMAIL = "single_email"
    MULTIPLE_EMAILS = "multiple_emails"
    THREAD = "thread"
    CUSTOM = "custom"


class UrgencyLevel(str, Enum):
    """Urgency levels for emails."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    IMPORTANT_SENDER = "important_sender"


class UrgencyReason(str, Enum):
    """Reasons for urgency classification."""
    KEYWORDS = "keywords"
    DEADLINE = "deadline"
    IMPORTANT_SENDER = "important_sender"
    ML_CLASSIFICATION = "ml_classification"
    MANUAL = "manual"


class SumizerMethod(str, Enum):
    """Available methods for Sumy summarizer."""
    LSA = "lsa"  # Latent Semantic Analysis
    LEX_RANK = "lex_rank"
    LU_SUMMARIZER = "lu"
    KL = "kl"  # Kullback-Leibler
    EDMUNDSON = "edmundson"
    TEXT_RANK = "text_rank"
    RANDOM = "random"


class AnthropicOptions(BaseModel):
    """Options for Anthropic Claude summarizer."""
    model: str = "claude-3-5-sonnet-20240620"
    max_tokens: int = Field(default=512, ge=1, le=4096)
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    system_prompt: str = "You are a helpful assistant that summarizes emails."
    timeout_seconds: int = Field(default=15, ge=1, le=60)


class OpenAIOptions(BaseModel):
    """Options for OpenAI GPT summarizer."""
    model: str = "gpt-4o"
    max_tokens: int = Field(default=512, ge=1, le=4096)
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)
    system_prompt: str = "You are a helpful assistant that summarizes emails."
    timeout_seconds: int = Field(default=15, ge=1, le=60)


class SumyOptions(BaseModel):
    """Options for Sumy summarizer."""
    method: SumizerMethod = SumizerMethod.LSA
    sentence_count: int = Field(default=3, ge=1, le=10)
    language: str = "english"


class HeuristicOptions(BaseModel):
    """Options for heuristic summarizer."""
    max_sentences: int = Field(default=3, ge=1, le=10)
    prefer_beginning: bool = True
    include_subject: bool = True


class SummaryOptions(BaseModel):
    """Combined options for all summarizers."""
    max_length: int = Field(default=400, ge=100, le=2000)
    combined_length: int = Field(default=800, ge=200, le=4000)
    reading_speed_wpm: int = Field(default=225, ge=100, le=500)
    
    # Provider-specific options
    anthropic: AnthropicOptions = Field(default_factory=AnthropicOptions)
    openai: OpenAIOptions = Field(default_factory=OpenAIOptions)
    sumy: SumyOptions = Field(default_factory=SumyOptions)
    heuristic: HeuristicOptions = Field(default_factory=HeuristicOptions)
    
    # Provider order for fallback chain
    provider_chain: List[SummaryProvider] = Field(
        default_factory=lambda: [
            SummaryProvider.ANTHROPIC,
            SummaryProvider.OPENAI,
            SummaryProvider.SUMY,
            SummaryProvider.HEURISTIC,
        ]
    )
    
    # Urgency detection options
    use_ml_urgency: bool = True
    urgency_model_path: Optional[str] = None
    urgency_keywords: Set[str] = Field(
        default_factory=lambda: {
            "urgent", "asap", "emergency", "important", 
            "deadline", "due", "immediately", "critical",
            "action required", "time sensitive", "priority"
        }
    )


class DeadlineInfo(BaseModel):
    """Information about a detected deadline."""
    text: str
    date: datetime
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    is_expired: bool = False
    
    @property
    def days_remaining(self) -> Optional[float]:
        """Calculate days remaining until deadline."""
        if self.is_expired:
            return 0
        
        now = datetime.now()
        if self.date < now:
            return 0
        
        delta = self.date - now
        return delta.total_seconds() / (24 * 3600)


class UrgencyInfo(BaseModel):
    """Information about detected urgency in an email."""
    level: UrgencyLevel = UrgencyLevel.NORMAL
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    reasons: List[UrgencyReason] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    deadlines: List[DeadlineInfo] = Field(default_factory=list)
    explanation: Optional[str] = None
    
    @validator("level", pre=True, always=True)
    def set_level_from_score(cls, v, values):
        """Set urgency level based on score if not explicitly provided."""
        if v != UrgencyLevel.NORMAL and "score" in values:
            score = values["score"]
            if score < 0.25:
                return UrgencyLevel.LOW
            elif score < 0.5:
                return UrgencyLevel.NORMAL
            elif score < 0.75:
                return UrgencyLevel.HIGH
            else:
                return UrgencyLevel.URGENT
        return v


class SummaryResult(BaseModel):
    """Result of a summarization operation."""
    text: str
    provider: SummaryProvider
    type: SummaryType = SummaryType.SINGLE_EMAIL
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Metadata
    original_length: int
    summary_length: int
    compression_ratio: float = Field(default=0.0, ge=0.0)
    reading_time_minutes: float = Field(default=0.0, ge=0.0)
    
    # Urgency information
    urgency: UrgencyInfo = Field(default_factory=UrgencyInfo)
    
    # Provider-specific metadata
    provider_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Error information
    error: Optional[str] = None
    fallback_chain: List[SummaryProvider] = Field(default_factory=list)
    
    @root_validator
    def calculate_compression_ratio(cls, values):
        """Calculate compression ratio if not provided."""
        if (
            values.get("compression_ratio") == 0.0 
            and values.get("original_length") 
            and values.get("summary_length")
        ):
            original = values.get("original_length")
            if original > 0:
                values["compression_ratio"] = values.get("summary_length") / original
        return values
    
    @property
    def is_fallback(self) -> bool:
        """Check if this result was generated by a fallback provider."""
        return len(self.fallback_chain) > 0
    
    @property
    def is_error(self) -> bool:
        """Check if this result contains an error."""
        return self.error is not None


class SummarizationTask(BaseModel):
    """A task for the summarization engine."""
    id: str
    content: Union[str, List[str]]
    subject: Optional[str] = None
    type: SummaryType = SummaryType.SINGLE_EMAIL
    max_length: Optional[int] = None
    options: Optional[SummaryOptions] = None
    provider_override: Optional[SummaryProvider] = None
    
    @property
    def is_multi_content(self) -> bool:
        """Check if this task has multiple content items."""
        return isinstance(self.content, list)
    
    @property
    def content_length(self) -> int:
        """Get the total length of content."""
        if isinstance(self.content, str):
            return len(self.content)
        return sum(len(c) for c in self.content)


class SummaryBatch(BaseModel):
    """A batch of summarization tasks."""
    tasks: List[SummarizationTask] = Field(default_factory=list)
    options: SummaryOptions = Field(default_factory=SummaryOptions)
    
    def add_task(
        self, 
        content: Union[str, List[str]], 
        task_id: Optional[str] = None,
        subject: Optional[str] = None,
        type: SummaryType = SummaryType.SINGLE_EMAIL,
        max_length: Optional[int] = None,
        provider_override: Optional[SummaryProvider] = None,
    ) -> str:
        """
        Add a task to the batch.
        
        Args:
            content: Text content to summarize
            task_id: Optional task ID (generated if not provided)
            subject: Optional subject for context
            type: Type of summary
            max_length: Maximum length of summary
            provider_override: Override default provider chain
            
        Returns:
            Task ID
        """
        if task_id is None:
            task_id = f"task_{len(self.tasks) + 1}"
            
        task = SummarizationTask(
            id=task_id,
            content=content,
            subject=subject,
            type=type,
            max_length=max_length,
            provider_override=provider_override,
        )
        
        self.tasks.append(task)
        return task_id
