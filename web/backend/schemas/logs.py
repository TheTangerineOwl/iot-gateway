"""Модели для вывода логов."""
from typing import Optional
from pydantic import BaseModel


class LogFile(BaseModel):
    """Модель файла логов."""

    filename: str
    size_bytes: int
    modified_at: str
    is_active: bool = False


class LogFileList(BaseModel):
    """Модель для списка файлов логов."""

    files: list[LogFile]
    total: int
    logs_dir: str


class LogLines(BaseModel):
    """Модель для среза файлов логов."""

    filename: str
    lines: list[str]
    total_lines: int
    filtered_lines: int
    level_filter: Optional[str] = None
    search_filter: Optional[str] = None
