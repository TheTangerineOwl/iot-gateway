"""Повреждение случайных величин в пакете для симуляции ошибок."""
from enum import Enum
from math import nan, inf
from random import choice
from typing import Any


class FaultType(str, Enum):
    """Тип ошибки пакета."""

    NAN = 'NaN'
    INF = 'Inf'
    EMPTY = 'Empty payload'
    NESTING = 'Nesting'
    WRONG_TYPE = 'Wrong type'


def _fault_nan(
    payload: dict[str, Any]
) -> dict[str, Any]:
    """Замена случайной величины на NaN."""
    key = next(iter(payload))
    payload[key] = nan
    return payload


def _fault_inf(
    payload: dict[str, Any]
) -> dict[str, Any]:
    """Замена случайной величины на Infinity."""
    key = next(iter(payload))
    payload[key] = inf
    return payload


def _fault_empty(
    payload: dict[str, Any]
) -> dict[str, Any]:
    """Замена нагрузки на пустое сообщение."""
    return {}


def _fault_wrong_type(
    payload: dict[str, Any]
) -> dict[str, Any]:
    """Замена значения на некорректный тип."""
    key = next(iter(payload))
    val = payload[key]
    if isinstance(val, str):
        val = 0.0
    else:
        val = 'STRING'
    return payload


def _fault_nesting(
    payload: dict[str, Any]
) -> dict[str, Any]:
    """Добавление уровня вложения."""
    payload = {'nest': payload}
    return payload


_FAULT_GENS = {
    FaultType.EMPTY: _fault_empty,
    FaultType.INF: _fault_inf,
    FaultType.NAN: _fault_nan,
    FaultType.NESTING: _fault_nesting,
    FaultType.WRONG_TYPE: _fault_wrong_type
}


def get_faulty(
    payload: dict[str, Any],
    fault: FaultType | None = None
) -> dict[str, Any]:
    """Получить поврежденный пакет."""
    if fault is None:
        fault = choice(list(FaultType))
    return _FAULT_GENS[fault](payload)
