"""Abstract base class for transcription backends."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Segment:
    """A timestamped segment of transcribed text."""

    start: float  # seconds from audio start
    end: float  # seconds from audio start
    text: str  # transcribed text content


class BaseTranscriber(ABC):
    """Abstract base for ASR transcription backends.

    Subclasses must define *name* (a unique string identifier)
    and implement :meth:`transcribe`.
    """

    name: str

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        # Only check name on concrete (non-abstract) subclasses
        if not hasattr(cls, "__abstractmethods__") or not cls.__abstractmethods__:
            if not getattr(cls, "name", None):
                raise TypeError(f"{cls.__name__} must define class-level `name`")

    @abstractmethod
    def transcribe(self, audio_path: str) -> list[Segment]:
        """Transcribe an audio file into timestamped segments.

        Args:
            audio_path: Path to the audio file (mp3/wav).

        Returns:
            List of Segment objects with start, end, and text.
        """
        ...
