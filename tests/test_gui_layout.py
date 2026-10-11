"""真实 Mac GUI 的文字裁切回归；单独启用，避免无桌面环境创建 Cocoa 窗口。"""

import os
import sys

import pytest


@pytest.fixture(scope='module')
def qt_app():
    from PyQt6.QtWidgets import QApplication

    # Fluent 的全局 QConfig 在 QApplication 生命周期内共享。
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.mark.skipif(
    sys.platform != 'darwin' or os.environ.get('QQFARM_NATIVE_GUI_TEST') != '1',
    reason='需要真实 Mac 桌面；设置 QQFARM_NATIVE_GUI_TEST=1',
)
def test_small_window_keeps_status_text_readable(tmp_path, monkeypatch, qt_app):
    from PyQt6.QtCore import QCoreApplication, QEvent

    import utils.app_paths as paths
    from core.instance.manager import InstanceManager
    from gui.main_window_core import MainWindow
    from gui.window_loader import build_main_window

    app = qt_app
    monkeypatch.setattr(paths, '_RUNTIME_USER_APP_DIR', tmp_path)
    monkeypatch.setattr(MainWindow, '_check_updates_on_startup', lambda self: None)
    manager = InstanceManager()
    manager.load()
    window = build_main_window(manager)
    window._skip_free_notice = True
    status = next(iter(window._workspaces.values())).status_panel
    status.update_stats({'state': 'paused', 'current_task': '好友巡查', 'next_run': '10-10 17:45:00'})
    try:
        for width, height in [(970, 600), (1747, 1000)]:
            window.resize(width, height)
            window.show()
            app.processEvents()
            assert all(label.height() >= label.fontMetrics().height() for label in status._labels.values())
    finally:
        window.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.mark.skipif(
    sys.platform != 'darwin' or os.environ.get('QQFARM_NATIVE_GUI_TEST') != '1',
    reason='需要真实 Mac 桌面；设置 QQFARM_NATIVE_GUI_TEST=1',
)
def test_feature_panel_keeps_checkbox_hint_and_time_text_readable(tmp_path, qt_app):
    from PyQt6.QtWidgets import QStyle, QStyleOptionButton
    from qfluentwidgets import CaptionLabel

    from gui.widgets.feature_panel import FeaturePanel
    from models.config import AppConfig

    app = qt_app
    config = AppConfig.load(str(tmp_path / 'config.json'))
    panel = FeaturePanel(config, 'gui-layout-test')
    try:
        for width in (780, 1100, 500):
            panel.resize(width, 700)
            panel.show()
            app.processEvents()
            failures = []
            for key, box in panel._bool_widgets.items():
                option = QStyleOptionButton()
                option.initFrom(box)
                option.text = box.text()
                text_rect = box.style().subElementRect(QStyle.SubElement.SE_CheckBoxContents, option, box)
                if not box.parentWidget().rect().contains(box.geometry()):
                    failures.append(f'{key}: checkbox clipped by parent')
                required = box.fontMetrics().horizontalAdvance(box.text())
                if text_rect.width() < required:
                    failures.append(f'{key}: checkbox text {text_rect.width()} < {required}')
            for label in panel.findChildren(CaptionLabel):
                if label.wordWrap() and label.height() < label.heightForWidth(label.width()):
                    failures.append(
                        f'hint {label.text()[:14]}: {label.height()} < {label.heightForWidth(label.width())}'
                    )
            for pair in panel._time_range_widgets.values():
                for edit in pair:
                    if edit.width() < edit.sizeHint().width():
                        failures.append(f'time edit: {edit.width()} < {edit.sizeHint().width()}')
            assert not failures, '\n'.join(failures)
    finally:
        panel.close()
        panel.deleteLater()
        app.processEvents()
