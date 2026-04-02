"""Модуль конвейера для обработки сообщений на шине."""
from .pipeline import Pipeline
from .stages import PipelineStage, ValidationStage


__all__ = ['Pipeline', 'PipelineStage', 'ValidationStage']
