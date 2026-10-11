"""后台输入不得使用系统鼠标；三段拖拽使用窗口独立的输入位置。"""

import sys

import pytest

from core.platform.action_executor import ActionExecutor
from models.config import RunMode, resolve_effective_run_mode


@pytest.mark.skipif(sys.platform != 'darwin', reason='macOS 输入后端')
def test_background_mode_and_drag_stay_in_target_window(monkeypatch):
    import Quartz

    from core.platform import macos_native

    events = []
    monkeypatch.setattr(
        macos_native,
        'post_window_mouse',
        lambda hwnd, kind, x, y: events.append((hwnd, kind, x, y)) or True,
        raising=False,
    )
    monkeypatch.setattr(ActionExecutor, '_set_cursor_pos', lambda *args: pytest.fail('后台输入移动了系统鼠标'))
    assert resolve_effective_run_mode(RunMode.BACKGROUND, 'qq') == RunMode.BACKGROUND
    executor = ActionExecutor((100, 140, 540, 960), hwnd=42, run_mode=RunMode.BACKGROUND, click_offset=0)
    assert executor.click_absolute(150, 190)
    assert executor.move_abs(180, 200)
    assert executor.mouse_down()
    assert executor.move_abs(200, 220, duration=0.02)
    assert executor.mouse_up()
    assert [event[1] for event in events] == [
        Quartz.kCGEventMouseMoved,
        Quartz.kCGEventLeftMouseDown,
        Quartz.kCGEventLeftMouseUp,
        Quartz.kCGEventMouseMoved,
        Quartz.kCGEventLeftMouseDown,
        Quartz.kCGEventLeftMouseDragged,
        Quartz.kCGEventLeftMouseUp,
    ]
    assert events[-1] == (42, Quartz.kCGEventLeftMouseUp, 200, 220)


@pytest.mark.skipif(sys.platform != 'darwin', reason='macOS 输入后端')
def test_background_escape_targets_qq_process(monkeypatch):
    import Quartz

    from core.platform import macos_native
    from core.platform.macos_window_manager import WindowManager
    from utils.win_input import press_escape

    events = []
    monkeypatch.setattr(macos_native, 'require_accessibility', lambda: None)
    monkeypatch.setattr(macos_native, 'require_unlocked_session', lambda: None)
    monkeypatch.setattr(WindowManager, '_record', classmethod(lambda cls, hwnd: {'kCGWindowOwnerPID': 123}))
    monkeypatch.setattr(Quartz, 'CGEventCreateKeyboardEvent', lambda source, key, down: (key, down))
    monkeypatch.setattr(Quartz, 'CGEventPostToPid', lambda pid, event: events.append((pid, event)))
    monkeypatch.setattr(Quartz, 'CGEventPost', lambda *args: pytest.fail('后台 ESC 影响了前台应用'))
    assert press_escape(hwnd=42, run_mode=RunMode.BACKGROUND, hold_seconds=0)
    assert events == [(123, (53, True)), (123, (53, False))]
