"""Abstract base class for LLM summarization backends."""

from abc import ABC, abstractmethod


class BaseSummarizer(ABC):
    """Abstract base for LLM summarization backends.

    Subclasses must define *name* (a unique string identifier)
    and implement :meth:`summarize`.
    """

    name: str

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Check that any abstract methods from the parent are overridden
        for base in cls.__mro__[1:]:
            for attr_name, attr_val in base.__dict__.items():
                if getattr(attr_val, "__isabstractmethod__", False):
                    if attr_name not in cls.__dict__:
                        raise TypeError(
                            "Can't instantiate abstract class "
                            f"{cls.__name__} without an implementation "
                            f"for abstract method(s): {attr_name}"
                        )
        # Concrete subclasses must define class-level `name`
        if not getattr(cls, "name", None):
            raise TypeError(
                f"{cls.__name__} must define class-level `name`"
            )

    @abstractmethod
    def summarize(self, transcript: str) -> str:
        """Summarize a transcript into structured meeting notes.

        Args:
            transcript: Full transcript text (with or without timestamps).

        Returns:
            Markdown-formatted meeting summary.
        """
        ...
