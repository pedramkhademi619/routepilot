"""Port interface for policy persistence repository."""

from abc import ABC, abstractmethod

from routepilot.domain.policy.policy_document import PolicyDocument


class PolicyRepositoryPort(ABC):
    """Port interface for loading and saving versioned policy documents."""

    @abstractmethod
    def load_policy(self) -> PolicyDocument:
        """Loads the current policy document from persistent storage."""

    @abstractmethod
    def save_policy(self, document: PolicyDocument) -> None:
        """Atomically saves the policy document to persistent storage."""
