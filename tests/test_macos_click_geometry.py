"""截图更新窗口位置后，点击必须使用同一内容区的屏幕坐标。"""

import sys
from types import SimpleNamespace

import pytest
from PIL import Image

from core.engine.bot.runtime import BotRuntimeMixin
from core.platform.action_executor import ActionExecutor
from core.platform.device import Device
from core.vision.cv_detector import CVDetector
from models.config import AppConfig


@pytest.mark.skipif(sys.platform != 'darwin', reason='macOS 内容区映射')
def test_screenshot_refreshes_click_origin_after_window_moves(monkeypatch):
    from core.platform import macos_native

    monkeypatch.setattr(macos_native, 'require_unlocked_session', lambda: None)
    config = AppConfig()
    config.screenshot.capture_interval_seconds = 0
    old_rect = (0, 40, 540, 960)
    current_rect = (300, 200, 360, 640)
    runtime = BotRuntimeMixin()
    runtime.config = config
    runtime.window_manager = SimpleNamespace(
        get_capture_rect=lambda: current_rect,
        get_window_handle=lambda: 123,
        crop_window_image_for_preview=lambda image, platform: image.resize((540, 960)),
    )
    runtime.action_executor = ActionExecutor(old_rect, click_offset=0)
    runtime.screen_capture = SimpleNamespace(capture=lambda rect, hwnd: Image.new('RGB', (rect[2], rect[3])))
    runtime.cv_detector = CVDetector()
    runtime.emit_preview = lambda image: None
    runtime.device = Device(runtime)
    runtime.device.set_rect(old_rect)
    assert runtime.device.screenshot().shape[:2] == (960, 540)
    point = runtime.resolve_live_click_point(270, 480)
    assert runtime.action_executor.relative_to_absolute(*point) == (480, 520)
