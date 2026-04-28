"""Схемы для вывода логов."""
from datetime import datetime, timezone
from typing import Optional, List
import re
from pathlib import Path
from pydantic import BaseModel, field_validator, model_validator


class LogFile(BaseModel):
    """Схема файла логов."""

    filename: str
    size_bytes: int
    modified_at: datetime  # ISO
    is_active: bool = False

    @field_validator('filename')
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """Валидация имени файла."""
        if not v:
            raise ValueError('filename не может быть пустым')
        if re.search(r'[<>:"\\|?*]', v):
            raise ValueError('Недопустимые символы в имени файла')
        if '..' in v:
            raise ValueError('Обнаружена попытка path traversal')
        return v

    @field_validator('size_bytes')
    @classmethod
    def validate_size(cls, v: int) -> int:
        """Валидация размера файла."""
        if v < 0:
            raise ValueError('size_bytes не может быть отрицательным')
        return v

    @field_validator('modified_at')
    @classmethod
    def validate_modified_at(cls, v: datetime):
        """Валидация поля modified_at."""
        if not v.tzinfo:
            val = v.replace(tzinfo=timezone.utc)
        else:
            val = v.astimezone(timezone.utc)
        if val > datetime.now(timezone.utc):
            raise ValueError('modified_at не может быть в будущем')
        return val


class LogFileList(BaseModel):
    """Схема для списка файлов логов."""

    files: list[LogFile]
    total: int
    logs_dir: str

    @field_validator('total')
    @classmethod
    def validate_total(cls, v: int, info) -> int:
        """Валидация количества файлов."""
        files = info.data.get('files', [])
        if v != len(files):
            raise ValueError(
                f'total ({v}) не соответствует '
                f'количеству файлов ({len(files)})'
            )
        return v

    @field_validator('logs_dir')
    @classmethod
    def validate_logs_dir(cls, v: str) -> str:
        """Валидация пути к директории лога."""
        if not v:
            raise ValueError('logs_dir не может быть пустым')
        path = Path(v)
        if not path.is_absolute():
            raise ValueError('logs_dir должен быть абсолютным путём')
        return str(path.resolve())


class LogLines(BaseModel):
    """Схема для среза файлов логов."""

    filename: str
    lines: list[str]
    total_lines: int
    filtered_lines: int
    level_filter: Optional[str]
    search_filter: Optional[str]

    @model_validator(mode='after')
    def validate_consistency(self):
        """Валидация модели."""
        if self.filtered_lines > self.total_lines:
            raise ValueError(
                'filtered_lines не может превышать total_lines'
            )
        if len(self.lines) != self.filtered_lines:
            raise ValueError(
                'Количество строк в lines не соответствует filtered_lines'
            )
        return self

    @field_validator('lines')
    @classmethod
    def validate_lines(cls, v: List[str]) -> List[str]:
        """Валидация количества строк."""
        for line in v:
            if not isinstance(line, str):
                raise ValueError('Все элементы lines должны быть строками')
            if len(line) > 10000:
                raise ValueError('Строка лога слишком длинная')
        return v

    @field_validator('level_filter')
    @classmethod
    def validate_level_filter(cls, v: Optional[str]) -> Optional[str]:
        """Валидация фильтра."""
        if v is None:
            return v
        valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        if v.upper() not in valid_levels:
            raise ValueError(f'Недопустимый уровень логирования: {v}')
        return v.upper()

    @field_validator('search_filter')
    @classmethod
    def validate_search_filter(cls, v: Optional[str]) -> Optional[str]:
        """Валидация поиска."""
        if v is not None:
            if len(v) > 255:
                raise ValueError('Поисковый запрос слишком длинный')
            if re.search(r'[()\[\]{}]', v):
                raise ValueError('Недопустимые символы в поисковом запросе')
        return v

    @field_validator('total_lines', 'filtered_lines')
    @classmethod
    def validate_line_counts(cls, v: int) -> int:
        """Валидация количества строк."""
        if v < 0:
            raise ValueError('Количество строк не может быть отрицательным')
        return v
