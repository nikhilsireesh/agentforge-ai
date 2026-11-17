"""Shared response shapes."""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    """Base for response models built from SQLAlchemy objects."""

    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    """Standard paginated list response."""

    items: list[T]
    total: int
    page: int
    page_size: int


class Message(BaseModel):
    success: bool = True
    message: str
