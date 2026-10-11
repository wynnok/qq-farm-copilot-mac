"""平台迁移回归：坐标、截图、拖拽、调度与成熟时间算法。"""

import sys
import threading
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from PIL import Image

from core.engine.bot.runtime import BotRuntimeMixin
from core.engine.task.executor import TaskExecutor
from core.engine.task.registry import TaskItem, TaskResult
from core.platform.action_executor import ActionExecutor
from core.platform.screen_capture import ScreenCapture
from models.config import RunMode, resolve_effective_run_mode
from tasks.timed_harvest import TaskTimedHarvest


@pytest.mark.parametrize('width,height', [(540, 960), (490, 870), (360, 640)])
def test_macos_coordinates_map_content_and_clamp(monkeypatch, width, height):
    monkeypatch.setattr(sys, 'platform', 'darwin')
    runtime = BotRuntimeMixin()
    rect = (-600, 80, width, height)
    assert runtime.resolve_capture_point(270, 480, rect) == (round(width / 2), round(height / 2))
    assert runtime.resolve_capture_point(540, 960, rect) == (width - 1, height - 1)
    assert runtime.resolve_capture_point(-20, -10, rect) == (0, 0)
    executor = ActionExecutor(rect, click_offset=0)
    x, y = runtime.resolve_capture_point(270, 480, rect)
    assert executor.relative_to_absolute(x, y) == (-600 + x, 80 + y)


def test_effective_mode_keeps_windows_background(monkeypatch):
    monkeypatch.setattr(sys, 'platform', 'darwin')
    assert resolve_effective_run_mode(RunMode.BACKGROUND, 'qq') == RunMode.BACKGROUND
    monkeypatch.setattr(sys, 'platform', 'win32')
    assert resolve_effective_run_mode(RunMode.BACKGROUND, 'qq') == RunMode.BACKGROUND


def test_host_template_override_preserves_windows_asset(monkeypatch, tmp_path):
    from utils import template_paths

    original = tmp_path / 'templates/qq/btn/tree.png'
    override = tmp_path / 'templates/macos/qq/btn/tree.png'
    override.parent.mkdir(parents=True)
    override.write_bytes(b'template')
    monkeypatch.setattr(template_paths, 'project_root', lambda: tmp_path)
    monkeypatch.setattr(sys, 'platform', 'darwin')
    assert template_paths.resolve_template_file('templates/qq/btn/tree.png') == override
    assert template_paths.resolve_template_file('templates/qq/btn/missing.png') == original.with_name('missing.png')
    monkeypatch.setattr(sys, 'platform', 'win32')
    assert template_paths.resolve_template_file('templates/qq/btn/tree.png') == original


@pytest.mark.skipif(sys.platform != 'darwin', reason='需要 macOS 原生模块')
def test_qq_accessibility_waits_for_actual_window(monkeypatch):
    from core.platform import macos_window_manager as backend

    ready = False
    enabled = []
    monkeypatch.setattr(backend, 'require_accessibility', lambda: None)
    monkeypatch.setattr(
        backend.WindowManager,
        '_record',
        classmethod(
            lambda cls, hwnd: {
                'kCGWindowOwnerPID': 123,
                'kCGWindowName': 'QQ经典农场',
                'kCGWindowBounds': {'X': 10, 'Y': 20, 'Width': 540, 'Height': 1000},
            }
        ),
    )
    monkeypatch.setattr(backend.AX, 'AXUIElementCreateApplication', lambda pid: 'app')
    monkeypatch.setattr(
        backend.AX, 'AXUIElementSetAttributeValue', lambda app, name, value: enabled.append((name, value)) or 0
    )

    def attribute(element, name):
        if name == 'AXManualAccessibility':
            return False
        if name == backend.AX.kAXWindowsAttribute:
            return ['window'] if ready else ['app']
        if name == backend.AX.kAXTitleAttribute:
            return 'QQ经典农场' if element == 'window' else 'QQ小程序'
        return None

    def run_loop(*args):
        nonlocal ready
        ready = True

    monkeypatch.setattr(backend, 'ax_attribute', attribute)
    monkeypatch.setattr(backend, 'ax_geometry', lambda element: (10, 20, 540, 1000) if element == 'window' else None)
    monkeypatch.setattr(backend.Quartz, 'CFRunLoopRunInMode', run_loop)
    assert backend.WindowManager.accessibility_window(42) == 'window'
    assert enabled == [('AXManualAccessibility', True)]


@pytest.mark.skipif(sys.platform != 'darwin', reason='需要 macOS 原生模块')
def test_retina_capture_returns_logical_points(monkeypatch, tmp_path):
    from core.platform import macos_native

    monkeypatch.setattr(macos_native, 'require_screen_capture', lambda: None)
    screenshot = SimpleNamespace(size=(40, 20), bgra=bytes([0, 0, 255, 255]) * 800)
    capture = ScreenCapture(str(tmp_path))
    monkeypatch.setattr(capture, '_get_mss_instance', lambda: SimpleNamespace(grab=lambda _: screenshot))
    image = capture.capture_region((-20, 10, 20, 10))
    assert image.size == (20, 10)
    assert image.getpixel((5, 5)) == (255, 0, 0)


@pytest.mark.skipif(sys.platform != 'darwin', reason='需要 macOS 原生模块')
def test_macos_capture_preserves_continuous_failure_policy(monkeypatch, tmp_path):
    from core.exceptions import WindowCaptureError
    from core.platform import macos_native

    def missing_frame(hwnd):
        raise WindowCaptureError('window surface not ready')

    monkeypatch.setattr(macos_native, 'capture_window', missing_frame)
    capture = ScreenCapture(str(tmp_path))
    for _ in range(capture.PRINT_WINDOW_FAILURE_RAISE_COUNT - 1):
        assert capture.capture((0, 0, 540, 960), hwnd=123) is None
    with pytest.raises(WindowCaptureError, match='capture failed continuously'):
        capture.capture((0, 0, 540, 960), hwnd=123)


@pytest.mark.skipif(sys.platform != 'darwin', reason='需要 macOS 原生模块')
def test_locked_session_rejects_mouse_input(monkeypatch):
    from core.platform import macos_native

    posted = []
    monkeypatch.setattr(macos_native, 'require_accessibility', lambda: None)
    monkeypatch.setattr(
        macos_native.Quartz, 'CGSessionCopyCurrentDictionary', lambda: {'CGSSessionScreenIsLocked': True}
    )
    monkeypatch.setattr(macos_native.Quartz, 'CGEventPost', lambda *args: posted.append(args))
    with pytest.raises(RuntimeError, match='桌面已锁定'):
        macos_native.post_mouse(macos_native.Quartz.kCGEventLeftMouseDown, 100, 100)
    assert posted == []


@pytest.mark.skipif(sys.platform != 'darwin', reason='需要 macOS 原生模块')
def test_drag_sends_dragged_events_and_releases(monkeypatch):
    import Quartz

    from core.platform import macos_native

    events = []
    monkeypatch.setattr(macos_native, 'post_mouse', lambda kind, x, y: events.append(kind) or True)
    monkeypatch.setattr(ActionExecutor, '_get_cursor_pos', staticmethod(lambda: (200, 300)))
    monkeypatch.setattr(ActionExecutor, '_mac_dragging', False)
    executor = ActionExecutor((0, 0, 540, 960), run_mode=RunMode.FOREGROUND, click_offset=0)
    assert executor.move_abs(200, 300)
    assert executor.mouse_down()
    assert executor.move_abs(220, 300)
    assert executor.mouse_up()
    assert events == [
        Quartz.kCGEventMouseMoved,
        Quartz.kCGEventLeftMouseDown,
        Quartz.kCGEventLeftMouseDragged,
        Quartz.kCGEventLeftMouseUp,
    ]
    assert not executor._mac_dragging


@pytest.mark.skipif(sys.platform != 'darwin', reason='需要 macOS 原生模块')
def test_cropped_preview_preserves_full_content():
    from core.platform.macos_window_manager import WindowManager

    image = Image.new('RGB', (490, 870), 'red')
    image.paste('blue', (0, 860, 490, 870))
    manager = WindowManager.__new__(WindowManager)
    normalized = manager.crop_window_image_for_preview(image)
    assert normalized.size == (540, 960)
    assert normalized.getpixel((270, 950)) == (0, 0, 255)


def test_scheduler_executes_serially_in_task_order_and_advances_next_run():
    now = datetime.now()
    tasks = {name: TaskItem(name, True, order, now, 60, 20) for name, order in [('friend', 1), ('main', 0)]}
    completed = threading.Event()
    calls = []

    def runner(context):
        calls.append(context.task_name)
        return TaskResult(success=context.task_name == 'main')

    def done(name, result):
        if name == 'friend':
            completed.set()

    executor = TaskExecutor(tasks, dict.fromkeys(tasks, runner), on_task_done=done)
    executor.start()
    try:
        assert completed.wait(3)
    finally:
        assert executor.stop()
    assert calls == ['main', 'friend']
    assert tasks['main'].next_run >= now + timedelta(seconds=60)
    assert tasks['friend'].next_run >= now + timedelta(seconds=20)
    assert tasks['friend'].failure_count == 1


def test_timed_harvest_keeps_individual_sample_times():
    plots = [
        {'countdown_sync_time': '2026-10-10 10:00:00', 'maturity_countdown': '00:00:30'},
        {'countdown_sync_time': '2026-10-10 10:00:40', 'maturity_countdown': '00:00:30'},
        {'countdown_sync_time': '2026-10-10 10:02:00', 'maturity_countdown': '00:00:30'},
    ]
    groups = TaskTimedHarvest.build_schedule_groups(plots, aggregation_seconds=60)
    assert groups == [
        (datetime(2026, 10, 10, 10, 0, 30), datetime(2026, 10, 10, 10, 1, 10)),
        (datetime(2026, 10, 10, 10, 2, 30), datetime(2026, 10, 10, 10, 2, 30)),
    ]
