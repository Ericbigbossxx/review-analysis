"""Browser abstraction only. Phase 1 deliberately does not open retail pages."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BrowserSession(ABC):
    @abstractmethod
    def describe(self) -> dict[str, str]:
        """Return non-sensitive session metadata without navigating."""


def collection_not_available() -> str:
    return "PHASE1_NO_BROWSER_COLLECTION"
