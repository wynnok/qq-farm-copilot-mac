"""自己的四格作物必须多次逐块收获，不能只检查一键收获。"""

from types import SimpleNamespace

from core.ui.assets import BTN_HARVEST, BTN_MATURE
from models.config import AppConfig
from models.farm_state import ActionType
from tasks.main_actions import TaskMainActionsMixin


def test_harvest_drains_repeated_mature_crops_without_bulk_button(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr('core.base.timer.time.time', lambda: clock[0])
    pending = {(120, 450): 3, (300, 500): 2}
    calls, stats = [], []

    def screenshot():
        clock[0] += 0.4

    def click(x, y, desc, **kwargs):
        calls.append((x, y, desc))
        pending[(x, y)] -= 1
        return True

    ui = SimpleNamespace(
        device=SimpleNamespace(screenshot=screenshot, click_point=click),
        appear=lambda button, **kw: button is BTN_MATURE and any(pending.values()),
        appear_then_click=lambda button, **kw: False,
        appear_location_in_roi=lambda button, roi, **kw: next((p for p, n in pending.items() if n), None),
    )
    task = TaskMainActionsMixin()
    task.ui = ui
    task.engine = SimpleNamespace(config=AppConfig(), _record_stat=stats.append)
    result = task._run_feature_harvest()
    assert not any(pending.values()), '四格成熟作物仍有待收获次数'
    assert result == 5
    assert stats == [ActionType.HARVEST] * 5
    assert len({desc for _, _, desc in calls}) == 2


def test_harvest_keeps_bulk_action_and_then_drains_special_crop(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr('core.base.timer.time.time', lambda: clock[0])
    pending = [1, 2]
    stats = []

    def bulk(button, **kwargs):
        assert kwargs['interval'] >= 1
        if button is BTN_HARVEST and pending[0]:
            pending[0] -= 1
            return True
        return False

    def click(*args, **kwargs):
        pending[1] -= 1
        return True

    task = TaskMainActionsMixin()
    task.ui = SimpleNamespace(
        device=SimpleNamespace(screenshot=lambda: clock.__setitem__(0, clock[0] + 0.4), click_point=click),
        appear=lambda button, **kw: bool(pending[0] if button is BTN_HARVEST else pending[1]),
        appear_then_click=bulk,
        appear_location_in_roi=lambda *args, **kwargs: (250, 500) if pending[1] else None,
    )
    task.engine = SimpleNamespace(config=AppConfig(), _record_stat=stats.append)
    result = task._run_feature_harvest()
    assert pending == [0, 0]
    assert result == 3


def test_harvest_waits_through_short_animation_before_finishing(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr('core.base.timer.time.time', lambda: clock[0])
    pending, hidden_until, stats = [2], [0.0], []

    def click(*args, **kwargs):
        pending[0] -= 1
        hidden_until[0] = clock[0] + 2
        return True

    task = TaskMainActionsMixin()
    task.engine = SimpleNamespace(config=AppConfig(), _record_stat=stats.append)
    task.ui = SimpleNamespace(
        device=SimpleNamespace(screenshot=lambda: clock.__setitem__(0, clock[0] + 0.4), click_point=click),
        appear=lambda *args, **kwargs: False,
        appear_then_click=lambda *args, **kwargs: False,
        appear_location_in_roi=lambda *args, **kwargs: (
            (250, 500) if pending[0] and clock[0] >= hidden_until[0] else None
        ),
    )
    assert task._run_feature_harvest() == 2
    assert pending[0] == 0


def test_failed_manual_input_does_not_record_success(monkeypatch):
    import pytest

    clock, stats = [1000.0], []
    monkeypatch.setattr('core.base.timer.time.time', lambda: clock[0])
    task = TaskMainActionsMixin()
    task.engine = SimpleNamespace(config=AppConfig(), _record_stat=stats.append)
    task.ui = SimpleNamespace(
        device=SimpleNamespace(
            screenshot=lambda: clock.__setitem__(0, clock[0] + 0.4), click_point=lambda *args, **kwargs: False
        ),
        appear=lambda *args, **kwargs: False,
        appear_then_click=lambda *args, **kwargs: False,
        appear_location_in_roi=lambda *args, **kwargs: (250, 500),
    )
    with pytest.raises(RuntimeError, match='逐块收获点击失败'):
        task._run_feature_harvest()
    assert not stats


def test_timed_harvest_uses_repeated_own_crop_harvest_and_preserves_next_run(monkeypatch):
    from datetime import datetime, timedelta

    import tasks.timed_harvest as timed

    clock = [1000.0]
    monkeypatch.setattr('core.base.timer.time.time', lambda: clock[0])

    class ClockDateTime(datetime):
        @classmethod
        def now(cls):
            return datetime(2026, 10, 12) + timedelta(seconds=clock[0] - 1000)

    monkeypatch.setattr(timed, 'datetime', ClockDateTime)
    pending, stats, queued = [3], [], []

    def click(*args, **kwargs):
        pending[0] -= 1
        return True

    config = AppConfig()
    from models.config import TaskScheduleItemConfig

    config.tasks['land_scan'] = TaskScheduleItemConfig(enabled=True)
    task = timed.TaskTimedHarvest.__new__(timed.TaskTimedHarvest)
    task.engine = SimpleNamespace(config=config, _record_stat=stats.append)
    task.ui = SimpleNamespace(
        device=SimpleNamespace(screenshot=lambda: clock.__setitem__(0, clock[0] + 0.4), click_point=click),
        ui_ensure=lambda page: True,
        appear=lambda *args, **kwargs: False,
        appear_then_click=lambda *args, **kwargs: False,
        appear_location_in_roi=lambda *args, **kwargs: (250, 500) if pending[0] else None,
    )
    task.task = SimpleNamespace(
        timed_harvest=SimpleNamespace(feature=SimpleNamespace(aggregation_seconds=30)),
        main=SimpleNamespace(call=lambda **kwargs: queued.append(kwargs) or True),
    )
    task.collect_land_cells = lambda **kwargs: []
    task._resolve_next_run_seconds = lambda: 60
    result = task.run((0, 0, 540, 960))
    assert pending[0] == 0
    assert stats == [ActionType.HARVEST] * 3
    assert result.success and result.next_run_seconds == 60
    assert queued == [{'force_call': False}]


def test_harvest_does_not_wait_or_click_when_no_crop_is_ready(monkeypatch):
    clock, stats = [1000.0], []
    monkeypatch.setattr('core.base.timer.time.time', lambda: clock[0])
    task = TaskMainActionsMixin()
    task.engine = SimpleNamespace(config=AppConfig(), _record_stat=stats.append)
    task.ui = SimpleNamespace(
        device=SimpleNamespace(screenshot=lambda: clock.__setitem__(0, clock[0] + 0.4)),
        appear=lambda *args, **kwargs: False,
        appear_location_in_roi=lambda *args, **kwargs: None,
    )
    assert task._run_feature_harvest() == 0
    assert clock[0] < 1001 and not stats


def test_harvest_stops_if_clicks_never_clear_the_mature_marker(monkeypatch):
    import pytest

    clock = [1000.0]
    monkeypatch.setattr('core.base.timer.time.time', lambda: clock[0])
    config = AppConfig()
    config.safety.stuck_long_wait_seconds = 2
    task = TaskMainActionsMixin()
    task.engine = SimpleNamespace(config=config, _record_stat=lambda action: None)
    task.ui = SimpleNamespace(
        device=SimpleNamespace(
            screenshot=lambda: clock.__setitem__(0, clock[0] + 0.4), click_point=lambda *args, **kwargs: True
        ),
        appear=lambda *args, **kwargs: False,
        appear_then_click=lambda *args, **kwargs: False,
        appear_location_in_roi=lambda *args, **kwargs: (250, 500),
    )
    with pytest.raises(RuntimeError, match='收获超时'):
        task._run_feature_harvest()


def test_real_macos_mature_badges_include_glowing_crop_and_repeated_clicks(monkeypatch):
    import sys
    from pathlib import Path

    import cv2
    import numpy as np
    import pytest
    from PIL import Image

    from core.platform.device import Device
    from core.ui.ui import UI
    from core.vision.cv_detector import CVDetector
    from models.farm_state import OperationResult

    if sys.platform != 'darwin':
        pytest.skip('当前客户端成熟标记模板仅覆盖 macOS')
    clock = [1000.0]
    monkeypatch.setattr('core.base.timer.time.time', lambda: clock[0])
    fixture = cv2.cvtColor(
        np.array(Image.open(Path(__file__).parent / 'fixtures/macos_mature_badges.png')), cv2.COLOR_RGB2BGR
    )
    pending = [3] * 6
    stats = []

    def execute(action):
        x, y = action.click_position['x'], action.click_position['y']
        index = (x - 20) // 48
        assert 0 <= index < 6 and 400 <= y <= 422
        pending[index] -= 1
        return OperationResult(action=action, success=True, message='', timestamp=clock[0])

    engine = SimpleNamespace(
        config=AppConfig(),
        action_executor=SimpleNamespace(execute_action=execute),
        resolve_live_click_point=lambda x, y: (x, y),
        _record_stat=stats.append,
    )
    device = Device(engine)

    def screenshot():
        clock[0] += 0.4
        frame = np.zeros((960, 540, 3), dtype=np.uint8)
        for i, n in enumerate(pending):
            if n:
                frame[400:422, 20 + i * 48 : 37 + i * 48] = fixture[:22, i * 48 : i * 48 + 17]
        device.set_image(frame)

    device.screenshot = screenshot
    task = TaskMainActionsMixin()
    task.engine = engine
    task.ui = UI(engine.config, CVDetector(), device, lambda: '')
    assert task._run_feature_harvest() == 18
    assert not any(pending)
    assert stats == [ActionType.HARVEST] * 18
