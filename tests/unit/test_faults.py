import pytest

from services.common.faults import FaultController, FaultInjected, FaultMode, FaultProfile


@pytest.mark.asyncio
async def test_latency_fault_waits_without_replacing_business_result(monkeypatch) -> None:
    observed: list[float] = []

    async def fake_sleep(value: float) -> None:
        observed.append(value)

    monkeypatch.setattr("services.common.faults.asyncio.sleep", fake_sleep)
    controller = FaultController(FaultProfile(mode=FaultMode.LATENCY, probability=1, delay_ms=2200))
    await controller.apply()
    assert observed == [2.2]


@pytest.mark.asyncio
async def test_error_fault_is_controlled_and_resettable() -> None:
    controller = FaultController(
        FaultProfile(mode=FaultMode.ERROR, probability=1, label="test fault")
    )
    with pytest.raises(FaultInjected, match="test fault"):
        await controller.apply()
    assert controller.reset().mode == FaultMode.OFF
