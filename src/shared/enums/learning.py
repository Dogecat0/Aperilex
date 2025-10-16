"""Learning-related enumerations used across the application."""

from __future__ import annotations

from enum import Enum


class LearningReviewStatus(str, Enum):
    """Human review status for learning walkthrough artifacts."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class LearningWalkthroughArtifactType(str, Enum):
    """Artifact types that participate in learning walkthrough bindings."""

    HIGHLIGHT = "HIGHLIGHT"
    COMPREHENSION_CHECK = "COMPREHENSION_CHECK"
