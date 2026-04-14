"""Интеграционные тесты PostgresStorage — реальный PostgreSQL."""
import pytest
import pytest_asyncio
from tests.conftest import skip_no_postgres
from pytest_postgresql import factories
from storage.postgresql import PostgresStorage
from models.device import ProtocolType
from models.telemetry import TelemetryRecord


# pytest-postgresql запускает временный процесс postgres
postgresql_proc = factories.postgresql_proc(port=None)   # случайный порт
postgresql = factories.postgresql("postgresql_proc")  # готовое соединение


def connstr(pg) -> str:
    """Собрать connstring из фикстуры pytest-postgresql."""
    i = pg.info
    return (
        f"postgresql://{i.user}:{i.password}@{i.host}:{i.port}/{i.dbname}"
    )


@pytest_asyncio.fixture
async def storage(postgresql):
    """Фикстура PostgresStorage на реальном временном Postgres."""
    db = PostgresStorage(connstr=connstr(postgresql))
    await db.setup()
    yield db
    await db.teardown()


@pytest.mark.asyncio
@pytest.mark.integration
@skip_no_postgres
async def test_save_and_get(storage):
    """Сохранить запись и получить её обратно."""
    record = TelemetryRecord(
        device_id="dev-001",
        payload={"temp": 36.6},
        message_id="msg-001",
        protocol=ProtocolType.HTTP,
    )
    await storage.save(record)

    results = await storage.get_by_device("dev-001")

    assert len(results) == 1
    assert results[0].device_id == "dev-001"
    assert results[0].message_id == "msg-001"
    assert results[0].payload == {"temp": 36.6}
    assert results[0].protocol == ProtocolType.HTTP


@pytest.mark.asyncio
@pytest.mark.integration
@skip_no_postgres
async def test_empty_if_unknown(storage):
    """Для неизвестного device_id возвращает пустой список."""
    results = await storage.get_by_device("ghost-device")
    assert results == []


@pytest.mark.asyncio
@pytest.mark.integration
@skip_no_postgres
async def test_limit_respected(storage):
    """Параметр limit ограничивает количество возвращаемых записей."""
    for i in range(10):
        await storage.save(TelemetryRecord(
            device_id="dev-001",
            payload={"i": i},
            message_id=f"msg-{i:03}",
            protocol="http",
        ))

    results = await storage.get_by_device("dev-001", limit=3)
    assert len(results) == 3


@pytest.mark.asyncio
@pytest.mark.integration
@skip_no_postgres
async def test_isolation_between_devices(storage):
    """get_by_device возвращает только записи нужного устройства."""
    await storage.save(TelemetryRecord(
        device_id="dev-A", payload={"x": 1}, message_id="a1", protocol="http"
    ))
    await storage.save(TelemetryRecord(
        device_id="dev-B", payload={"x": 2}, message_id="b1", protocol="http"
    ))

    results = await storage.get_by_device("dev-A")

    assert all(r.device_id == "dev-A" for r in results)
    assert len(results) == 1
