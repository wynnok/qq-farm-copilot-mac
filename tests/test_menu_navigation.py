"""页面识别得到当前菜单位置后，导航必须点击同一帧的实际按钮。"""

from types import SimpleNamespace

import numpy as np

from core.platform.device import Device
from core.ui.assets import MAIN_GOTO_FRIEND, MAIN_GOTO_MENU, MENU_GOTO_MAIN, SETTING_CHECK
from core.ui.page import page_main, page_menu
from core.ui.ui import UI
from core.vision.cv_detector import CVDetector
from models.config import AppConfig
from models.farm_state import OperationResult


def test_menu_navigation_uses_current_match_instead_of_design_coordinate(monkeypatch):
    config = AppConfig()
    stage = ['main']
    clicks = []
    frames = {key: np.zeros((960, 540, 3), dtype=np.uint8) for key in ('main', 'menu')}
    buttons = (MAIN_GOTO_FRIEND, MAIN_GOTO_MENU, SETTING_CHECK, MENU_GOTO_MAIN)
    saved = [(button, button._button_offset) for button in buttons]

    def paste(button, stage_name, position=None):
        button.ensure_template()
        x, y = position or button.area[:2]
        height, width = button.image.shape[:2]
        frames[stage_name][y : y + height, x : x + width] = button.image

    paste(MAIN_GOTO_FRIEND, 'main')
    paste(MAIN_GOTO_MENU, 'main', (32, 382))
    paste(SETTING_CHECK, 'menu')
    paste(MENU_GOTO_MAIN, 'menu', (31, 382))

    def execute(action):
        point = (action.click_position['x'], action.click_position['y'])
        clicks.append(point)
        if 31 <= point[0] <= 52 and 382 <= point[1] <= 402:
            stage[0] = 'menu' if stage[0] == 'main' else 'main'
        return OperationResult(action=action, success=True, message='', timestamp=0)

    engine = SimpleNamespace(
        config=config,
        action_executor=SimpleNamespace(execute_action=execute),
        resolve_live_click_point=lambda x, y: (x, y),
    )
    device = Device(engine)
    device.screenshot = lambda: device.set_image(frames[stage[0]])
    ui = UI(config, CVDetector(), device, lambda: '')
    monkeypatch.setattr(ui, '_button_interval_ready', lambda *args: True)
    monkeypatch.setattr(ui, '_button_interval_hit', lambda *args: None)
    ui.ui_pages = [page_main, page_menu]
    try:
        ui.ui_current = page_main
        assert ui.ui_goto(page_menu)
        assert clicks[0] == (40, 391)
        assert stage[0] == 'menu'
        assert ui.ui_goto(page_main)
        assert clicks[-1] == (41, 391)
        assert len(clicks) == 2
    finally:
        for button, offset in saved:
            button._button_offset = offset
        for page in ui.ui_pages:
            page.parent = None
