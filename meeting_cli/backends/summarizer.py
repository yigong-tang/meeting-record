"""Abstract base class for LLM summarization backends."""

from abc import ABC, abstractmethod


class BaseSummarizer(ABC):
    """Abstract base for LLM summarization backends.

    Subclasses must define ``name`` (a unique string identifier)
    and implement :meth:`summarize`.
    """

    name: str

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Only check name on concrete (non-abstract) subclasses
        if not hasattr(cls, "__abstractmethods__") or not cls.__abstractmethods__:
            if not getattr(cls, "name", None):
                raise TypeError(f"{cls.__name__} must define class-level `name`")

    @abstractmethod
    def summarize(self, transcript: str) -> str:
        """Summarize a transcript into structured meeting notes.

        Args:
            transcript: Full transcript text (with or without timestamps).

        Returns:
            Markdown-formatted meeting summary.
        """
        ...
