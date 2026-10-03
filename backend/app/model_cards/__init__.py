"""Canonical, evidence-only model card assembly."""

from .service import MODEL_CARD_SCHEMA_VERSION, get_or_create_card

__all__ = ["MODEL_CARD_SCHEMA_VERSION", "get_or_create_card"]