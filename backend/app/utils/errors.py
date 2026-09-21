from dataclasses import dataclass

@dataclass
class AppError(Exception):
    code: str
    message: str
    status: int = 422

    def __str__(self) -> str:
        return self.message

class CancelledError(Exception):
    """Cooperative cancellation at a safe training boundary."""
