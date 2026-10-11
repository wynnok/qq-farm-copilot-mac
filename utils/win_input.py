"""Windows 键盘输入工具。"""

from __future__ import annotations

import ctypes
import sys
import time

from models.config import RunMode

VK_ESCAPE = 0x1B
KEYEVENTF_KEYUP = 0x0002


def press_escape(
    *, hold_seconds: float = 0.02, hwnd: int | None = None, run_mode: RunMode = RunMode.FOREGROUND
) -> bool:
    """发送一次 ESC 按键。"""
    try:
        if sys.platform == 'darwin':
            import Quartz

            from core.platform.macos_native import require_accessibility, require_unlocked_session
            from core.platform.macos_window_manager import WindowManager

            require_accessibility()
            require_unlocked_session()
            pid = None
            if run_mode == RunMode.BACKGROUND:
                record = WindowManager._record(int(hwnd or 0))
                if record is None:
                    return False
                pid = int(record['kCGWindowOwnerPID'])
            down = Quartz.CGEventCreateKeyboardEvent(None, 53, True)
            if pid is None:
                Quartz.CGEventPost(Quartz.kCGHIDEventTap, down)
            else:
                Quartz.CGEventPostToPid(pid, down)
            time.sleep(max(0.0, float(hold_seconds)))
            up = Quartz.CGEventCreateKeyboardEvent(None, 53, False)
            if pid is None:
                Quartz.CGEventPost(Quartz.kCGHIDEventTap, up)
            else:
                Quartz.CGEventPostToPid(pid, up)
            return True
        user32 = ctypes.windll.user32
        user32.keybd_event(int(VK_ESCAPE), 0, 0, 0)
        if float(hold_seconds) > 0:
            time.sleep(float(hold_seconds))
        user32.keybd_event(int(VK_ESCAPE), 0, int(KEYEVENTF_KEYUP), 0)
        return True
    except Exception:
        return False
