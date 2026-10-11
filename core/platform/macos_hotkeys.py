"""macOS F9/F10 全局监听，将原生事件转为 Qt 信号。"""

import Quartz
from loguru import logger
from PyQt6.QtCore import QObject, pyqtSignal


class MacHotkeys(QObject):
    pause_requested = pyqtSignal()
    stop_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._callback = self._handle_event
        self._tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionListenOnly,
            1 << Quartz.kCGEventKeyDown,
            self._callback,
            None,
        )
        self._source = None
        if self._tap is None:
            logger.warning('全局 F9/F10 监听不可用，请授权输入监控；应用内快捷键仍可用')
            return
        self._source = Quartz.CFMachPortCreateRunLoopSource(None, self._tap, 0)
        Quartz.CFRunLoopAddSource(Quartz.CFRunLoopGetMain(), self._source, Quartz.kCFRunLoopCommonModes)
        Quartz.CGEventTapEnable(self._tap, True)

    def _handle_event(self, proxy, event_type, event, context):
        if event_type in (Quartz.kCGEventTapDisabledByTimeout, Quartz.kCGEventTapDisabledByUserInput):
            Quartz.CGEventTapEnable(self._tap, True)
        elif event_type == Quartz.kCGEventKeyDown:
            code = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
            if code == 101:
                self.pause_requested.emit()
            elif code == 109:
                self.stop_requested.emit()
        return event

    @property
    def active(self):
        return self._tap is not None

    def close(self):
        if self._source is not None:
            Quartz.CFRunLoopRemoveSource(Quartz.CFRunLoopGetMain(), self._source, Quartz.kCFRunLoopCommonModes)
        if self._tap is not None:
            Quartz.CGEventTapEnable(self._tap, False)
            Quartz.CFMachPortInvalidate(self._tap)
