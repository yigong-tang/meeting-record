"""Backend registry for transcription and summarization plugins.

New backends are discovered by scanning this package.  Add a new
backend by dropping a Python file into this directory that defines
a subclass of :class:`BaseTranscriber` or :class:`BaseSummarizer`
with a unique ``name``.
"""

from meeting_cli.backends.transcriber import BaseTranscriber, Segment
from meeting_cli.backends.summarizer import BaseSummarizer

# Module-private registries
_transcribers: dict[str, type[BaseTranscriber]] = {}
_summarizers: dict[str, type[BaseSummarizer]] = {}


def _discover() -> None:
    """Scan this package for backend classes and register them."""
    import pkgutil
    import importlib

    # Only scan on first access
    if _transcribers or _summarizers:
        return

    package = __package__  # "meeting_cli.backends"
    for _, modname, _ in pkgutil.iter_modules(__path__):
        if modname.startswith("_"):
            continue
        module = importlib.import_module(f".{modname}", package)
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if not isinstance(attr, type):
                continue
            if issubclass(attr, BaseTranscriber) and attr is not BaseTranscriber:
                if not getattr(attr, "name", None):
                    continue
                _transcribers[attr.name] = attr
            if issubclass(attr, BaseSummarizer) and attr is not BaseSummarizer:
                if not getattr(attr, "name", None):
                    continue
                _summarizers[attr.name] = attr


def get_transcriber(name: str) -> BaseTranscriber | None:
    """Get a transcriber instance by name."""
    _discover()
    cls = _transcribers.get(name)
    if cls is None:
        return None
    return cls()


def list_transcribers() -> list[str]:
    """List all registered transcriber backend names."""
    _discover()
    return sorted(_transcribers.keys())


def get_summarizer(name: str) -> BaseSummarizer | None:
    """Get a summarizer instance by name."""
    _discover()
    cls = _summarizers.get(name)
    if cls is None:
        return None
    return cls()


def list_summarizers() -> list[str]:
    """List all registered summarizer backend names."""
    _discover()
    return sorted(_summarizers.keys())


__all__ = [
    "BaseTranscriber",
    "BaseSummarizer",
    "Segment",
    "get_transcriber",
    "list_transcribers",
    "get_summarizer",
    "list_summarizers",
]
