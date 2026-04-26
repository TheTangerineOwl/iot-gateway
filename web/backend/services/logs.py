"""Сервисы для работы с файлами логов."""
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterable

from web.backend.dependencies.config import Settings
from web.backend.schemas.logs import LogFile, LogFileList, LogLines


logger = logging.getLogger(__name__)


async def _iter_log_dir(dir: Path):
    files = []
    for f in dir.iterdir():
        if f.is_file():
            if f.suffix == '.log':
                files.append(f)
        elif f.is_dir():
            files.extend(await _iter_log_dir(f))
    return files


async def read_log_list(settings: Settings) -> LogFileList:
    """Получить список файлов логов."""
    logs_dir = Path(settings.logs_dir).resolve()

    if not logs_dir.exists():
        raise FileNotFoundError(f'Директория {logs_dir} не найдена')

    files = await _iter_log_dir(logs_dir)
    files = sorted(
        files,
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    log_files = [
        LogFile(
            filename=f.name,
            size_bytes=f.stat().st_size,
            modified_at=datetime.fromtimestamp(
                f.stat().st_mtime, tz=timezone.utc
            ),
            is_active=(i == 0),
        )
        for i, f in enumerate(files)
    ]

    return LogFileList(
        files=log_files,
        total=len(log_files),
        logs_dir=str(logs_dir)
    )


async def read_log_file(
    filename: str,
    settings: Settings,
    lines: int = 100,
    level: str | None = None,
    search: str | None = None,
) -> LogLines:
    """Получить содержимое лог-файла."""
    logs_dir = Path(settings.logs_dir).resolve()
    file_path = (logs_dir / filename).resolve()

    if not str(file_path).startswith(str(logs_dir)):
        raise PermissionError('Доступ запрещен')

    if not file_path.exists() or not file_path.is_file():
        raise FileNotFoundError(f'Файл {filename} не найден')

    if lines <= 0:
        raise ValueError('Некорректный параметр запроса lines')
    if level and level not in [
        'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    ]:
        raise ValueError('Некорректный параметр запроса level')

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        all_lines = f.readlines()

    all_lines = [line.rstrip("\n") for line in all_lines]
    total_lines = len(all_lines)

    filtered = all_lines

    if level:
        level_upper = level.upper()
        filtered = [
            line for line in filtered
            if f"│ {level_upper}" in line
        ]

    if search:
        search_lower = search.lower()
        filtered = [line for line in filtered if search_lower in line.lower()]

    filtered = filtered[-lines:]

    return LogLines(
        filename=filename,
        lines=filtered,
        total_lines=total_lines,
        filtered_lines=len(filtered),
        level_filter=level,
        search_filter=search,
    )


async def read_stream_logs(
    settings: Settings,
    level: str = "INFO",
) -> AsyncIterable[str]:
    """Получить SSE-поток из активного файла лога."""
    logs_dir = Path(settings.logs_dir)

    if not logs_dir.exists():
        logger.error(f'Директория логов {logs_dir} не найдена')
        raise FileNotFoundError('Директория логов не найдена')

    log_files = sorted(
        [f for f in logs_dir.iterdir() if f.is_file() and f.suffix == ".log"],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    if not log_files:
        logger.error('Нет активного лог-файла')
        raise FileNotFoundError('Нет активного лог-файла')

    active_file = log_files[0]
    level_upper = level.upper()

    async def event_generator():
        with open(active_file, "r", encoding="utf-8", errors="replace") as f:
            # Перемотать в конец, чтобы стримить только новые строки
            f.seek(0, 2)
            while True:
                line = f.readline()
                if line:
                    line = line.rstrip("\n")
                    if level_upper == "DEBUG" or f"│ {level_upper}" in line:
                        yield f"data: {line}\n\n"
                else:
                    await asyncio.sleep(0.5)

    return event_generator()
