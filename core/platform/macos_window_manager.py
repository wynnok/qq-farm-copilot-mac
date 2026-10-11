"""macOS 窗口后端：Quartz 枚举，Accessibility 调整与激活。"""

import time
from types import SimpleNamespace

import ApplicationServices as AX
import Quartz
from AppKit import NSApplicationActivateIgnoringOtherApps, NSRunningApplication, NSScreen
from loguru import logger
from PIL import Image

from core.platform.macos_native import ax_attribute, ax_geometry, require_accessibility, require_unlocked_session
from core.platform.windows_window_manager import DisplayInfo, WindowInfo
from core.platform.windows_window_manager import WindowManager as BaseWindowManager


class WindowManager(BaseWindowManager):
    # QQ Mac 的标题栏高度可在 nonclient_metrics.json 的 macos 节点校准。
    @staticmethod
    def _enable_dpi_awareness() -> None:
        pass

    @staticmethod
    def _window_records():
        return Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionAll, Quartz.kCGNullWindowID) or []

    @classmethod
    def _record(cls, hwnd):
        return next((r for r in cls._window_records() if int(r['kCGWindowNumber']) == int(hwnd)), None)

    @classmethod
    def list_windows(cls, title_keyword: str = 'QQ经典农场') -> list[WindowInfo]:
        matched = []
        for record in cls._window_records():
            if int(record.get('kCGWindowLayer', 0)) != 0:
                continue
            title = str(record.get('kCGWindowName', ''))
            if not cls._matches_keyword(title, title_keyword):
                continue
            bounds = record['kCGWindowBounds']
            if bounds['Width'] <= 0 or bounds['Height'] <= 0:
                continue
            matched.append(
                WindowInfo(
                    hwnd=int(record['kCGWindowNumber']),
                    title=title,
                    left=round(bounds['X']),
                    top=round(bounds['Y']),
                    width=round(bounds['Width']),
                    height=round(bounds['Height']),
                    pid=int(record['kCGWindowOwnerPID']),
                    process_name=str(record.get('kCGWindowOwnerName', '')),
                )
            )
        return sorted(matched, key=lambda info: info.hwnd)

    @classmethod
    def is_window_alive(cls, hwnd: int) -> bool:
        return bool(hwnd and cls._record(hwnd))

    @classmethod
    def _get_window_rect(cls, hwnd: int):
        record = cls._record(hwnd)
        if record is None:
            return None
        b = record['kCGWindowBounds']
        return round(b['X']), round(b['Y']), round(b['X'] + b['Width']), round(b['Y'] + b['Height'])

    @classmethod
    def accessibility_window(cls, hwnd: int):
        require_accessibility()
        record = cls._record(hwnd)
        if record is None:
            return None
        app = AX.AXUIElementCreateApplication(int(record['kCGWindowOwnerPID']))
        b = record['kCGWindowBounds']
        expected = (b['X'], b['Y'], b['Width'], b['Height'])
        # QQ 的 Chromium 辅助功能树按需开启；初始化是异步的，必须等到真实窗口节点出现。
        if ax_attribute(app, 'AXManualAccessibility') is False:
            AX.AXUIElementSetAttributeValue(app, 'AXManualAccessibility', True)
        deadline = time.monotonic() + 1.5
        while True:
            windows = ax_attribute(app, AX.kAXWindowsAttribute) or []
            matches = []
            for window in windows:
                geometry = ax_geometry(window)
                if geometry and all(abs(a - c) <= 2 for a, c in zip(geometry, expected)):
                    matches.append(window)
            if len(matches) == 1:
                return matches[0]
            title = record.get('kCGWindowName', '')
            matches = [w for w in matches if ax_attribute(w, AX.kAXTitleAttribute) == title]
            if len(matches) == 1:
                return matches[0]
            if time.monotonic() >= deadline:
                return None
            Quartz.CFRunLoopRunInMode(Quartz.kCFRunLoopDefaultMode, 0.05, False)

    @classmethod
    def close_window(cls, hwnd: int) -> bool:
        window = cls.accessibility_window(hwnd)
        if window is None:
            return False
        button = ax_attribute(window, AX.kAXCloseButtonAttribute)
        return bool(button and AX.AXUIElementPerformAction(button, AX.kAXPressAction) == AX.kAXErrorSuccess)

    def _title_height(self) -> int:
        return max(0, int(self._nonclient_config.get('macos', {}).get('title_height', 40)))

    def get_capture_rect(self):
        info = self.refresh_cached_window_info()
        if info is None or info.height <= self._title_height():
            return None
        self._last_capture_rect_is_client = True
        return info.left, info.top + self._title_height(), info.width, info.height - self._title_height()

    def get_preview_crop_box(self, raw_width, raw_height, platform='qq'):
        return 0, 0, int(raw_width), int(raw_height)

    def get_preview_crop_margins(self, platform='qq'):
        return 0, 0, 0, 0

    def crop_window_image_for_preview(self, image, platform='qq'):
        if image is None:
            return None
        return image.resize((self.TARGET_CLIENT_WIDTH, self.TARGET_CLIENT_HEIGHT), Image.Resampling.LANCZOS)

    def activate_window(self) -> bool:
        if self._cached_window is None:
            return False
        return self.activate_window_handle(self._cached_window.hwnd)

    @classmethod
    def activate_window_handle(cls, hwnd: int) -> bool:
        require_accessibility()
        require_unlocked_session()
        record = cls._record(hwnd)
        if record is None:
            return False
        app = NSRunningApplication.runningApplicationWithProcessIdentifier_(int(record['kCGWindowOwnerPID']))
        window = cls.accessibility_window(hwnd)
        if app is None or window is None:
            return False
        AX.AXUIElementSetAttributeValue(window, AX.kAXMinimizedAttribute, False)
        activated = bool(app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps))
        raised = AX.AXUIElementPerformAction(window, AX.kAXRaiseAction) == AX.kAXErrorSuccess
        if not activated or not raised:
            return False
        # 解除最小化是异步操作，点击和截图必须等待窗口实际恢复到当前屏幕。
        deadline = time.monotonic() + 1.5
        while True:
            record = cls._record(hwnd)
            if record and record.get('kCGWindowIsOnscreen', False):
                return True
            if time.monotonic() >= deadline:
                return False
            Quartz.CFRunLoopRunInMode(Quartz.kCFRunLoopDefaultMode, 0.05, False)

    def list_displays(self):
        screens = list(NSScreen.screens())
        if not screens:
            return []
        main_height = screens[0].frame().size.height
        displays = []
        for index, screen in enumerate(screens, 1):
            frame, work = screen.frame(), screen.visibleFrame()
            left, top = round(frame.origin.x), round(main_height - frame.origin.y - frame.size.height)
            wl, wt = round(work.origin.x), round(main_height - work.origin.y - work.size.height)
            width, height = round(frame.size.width), round(frame.size.height)
            ww, wh = round(work.size.width), round(work.size.height)
            scale = float(screen.backingScaleFactor())
            displays.append(
                DisplayInfo(
                    index,
                    int(screen.deviceDescription()['NSScreenNumber']),
                    left,
                    top,
                    left + width,
                    top + height,
                    wl,
                    wt,
                    wl + ww,
                    wt + wh,
                    width,
                    height,
                    ww,
                    wh,
                    round(scale * 100),
                    round(scale * 96),
                    index == 1,
                    str(screen.localizedName()),
                )
            )
        return displays

    def get_display_metrics(self, hwnd=None):
        displays = self.list_displays()
        if not displays:
            return None
        display = displays[0]
        rect = self._get_window_rect(hwnd) if hwnd else None
        if rect:
            cx, cy = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
            display = next((d for d in displays if d.left <= cx < d.right and d.top <= cy < d.bottom), display)
        return dict(
            screen_width=displays[0].width,
            screen_height=displays[0].height,
            monitor_width=display.width,
            monitor_height=display.height,
            work_width=display.work_width,
            work_height=display.work_height,
            dpi=display.dpi,
            scale_percent=display.scale_percent,
            monitor_index=display.index,
        )

    def resize_window(self, position='left_center', platform='qq', screen_index=0) -> bool:
        if self._cached_window is None:
            return False
        window = self.accessibility_window(self._cached_window.hwnd)
        displays = self.list_displays()
        if window is None or not displays:
            logger.error('无法读取目标窗口辅助功能对象，请检查辅助功能授权')
            return False
        display = next((d for d in displays if d.index == screen_index), displays[0])
        title = self._title_height()
        scale = min(1.0, display.work_width / 540, (display.work_height - title) / 960)
        width, height = round(540 * scale), round(960 * scale) + title
        area = SimpleNamespace(
            left=display.work_left, top=display.work_top, right=display.work_right, bottom=display.work_bottom
        )
        x, y = self._calculate_position(area, width, height, position)
        size = AX.AXValueCreate(AX.kAXValueCGSizeType, (width, height))
        point = AX.AXValueCreate(AX.kAXValueCGPointType, (x, y))
        size_error = AX.AXUIElementSetAttributeValue(window, AX.kAXSizeAttribute, size)
        position_error = AX.AXUIElementSetAttributeValue(window, AX.kAXPositionAttribute, point)
        time.sleep(0.1)
        info = self.refresh_cached_window_info()
        if info is None:
            return False
        # 拒绝把横屏、侧栏或被客户端限制尺寸的画面拉伸成竖屏。
        ratio = info.width / max(1, info.height - title)
        if abs(ratio - 540 / 960) > 0.02:
            logger.error(
                '农场内容区比例不匹配，请调整窗口或校准 macos.title_height: {}x{}', info.width, info.height - title
            )
            return False
        logger.info('macOS 窗口内容区 {}x{}，识别归一化为 540x960', info.width, info.height - title)
        return size_error == AX.kAXErrorSuccess and position_error == AX.kAXErrorSuccess

    @staticmethod
    def list_virtual_desktops():
        return []

    def get_system_current_virtual_desktop_index(self):
        return 0

    def get_current_virtual_desktop_index(self, hwnd):
        return 0

    def move_window_to_virtual_desktop(self, hwnd, target_desktop_index):
        return int(target_desktop_index or 0) == 0

    def hide_window(self):
        logger.warning('macOS 前台运行时需要保持游戏窗口可见')
        return False

    def show_window(self):
        return self.activate_window()

    def is_window_hidden(self):
        return False

    def is_window_visible(self):
        if self._cached_window is None:
            return False
        record = self._record(self._cached_window.hwnd)
        return bool(record and record.get('kCGWindowIsOnscreen', False))
