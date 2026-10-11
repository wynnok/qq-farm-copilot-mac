"""macOS 原生辅助功能和 Quartz 输入，所有坐标均为屏幕逻辑点。"""

import ctypes
import threading
import time
from io import BytesIO

import ApplicationServices as AX
import objc
import Quartz
import ScreenCaptureKit as SC
from AppKit import NSBitmapImageFileTypePNG, NSBitmapImageRep, NSEvent, NSRunningApplication
from PIL import Image

from core.exceptions import WindowCaptureError


def require_accessibility() -> None:
    if not AX.AXIsProcessTrusted():
        raise RuntimeError('请在系统设置 → 隐私与安全性 → 辅助功能中允许启动本程序的终端或应用，然后重新启动程序')


def require_unlocked_session() -> None:
    session = Quartz.CGSessionCopyCurrentDictionary()
    if session is None or bool(session.get('CGSSessionScreenIsLocked', False)):
        raise RuntimeError('当前 Mac 桌面已锁定，无法执行游戏操作；请解锁后重新启动任务')


def require_screen_capture() -> None:
    if not Quartz.CGPreflightScreenCaptureAccess():
        raise RuntimeError(
            '请在系统设置 → 隐私与安全性 → 屏幕与系统音频录制中允许启动本程序的终端或应用，然后重新启动程序'
        )


def ax_attribute(element, name):
    error, value = AX.AXUIElementCopyAttributeValue(element, name, None)
    return value if error == AX.kAXErrorSuccess else None


def ax_geometry(element):
    position = ax_attribute(element, AX.kAXPositionAttribute)
    size = ax_attribute(element, AX.kAXSizeAttribute)
    if position is None or size is None:
        return None
    ok_position, point = AX.AXValueGetValue(position, AX.kAXValueCGPointType, None)
    ok_size, dimensions = AX.AXValueGetValue(size, AX.kAXValueCGSizeType, None)
    if not ok_position or not ok_size:
        return None
    return tuple(round(v) for v in (point.x, point.y, dimensions.width, dimensions.height))


def post_mouse(event_type: int, x: int, y: int) -> bool:
    require_accessibility()
    require_unlocked_session()
    event = Quartz.CGEventCreateMouseEvent(None, event_type, (x, y), Quartz.kCGMouseButtonLeft)
    if event is None:
        return False
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)
    return True


class _CGPoint(ctypes.Structure):
    _fields_ = [('x', ctypes.c_double), ('y', ctypes.c_double)]


_core_graphics = ctypes.CDLL('/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics')


def post_window_mouse(hwnd: int, event_type: int, x: int, y: int) -> bool:
    """向窗口所属进程发送鼠标事件，不激活窗口或移动系统鼠标。

    CGEventSetWindowLocation 是私有接口；QQ Chromium 需要窗口内坐标和 subtype=3。
    """
    require_accessibility()
    require_unlocked_session()
    records = Quartz.CGWindowListCopyWindowInfo(Quartz.kCGWindowListOptionAll, Quartz.kCGNullWindowID) or []
    window = next((record for record in records if int(record['kCGWindowNumber']) == hwnd), None)
    if window is None:
        return False
    bounds = window['kCGWindowBounds']
    local_x, local_y = x - float(bounds['X']), y - float(bounds['Y'])
    pid = int(window['kCGWindowOwnerPID'])
    event = NSEvent.mouseEventWithType_location_modifierFlags_timestamp_windowNumber_context_eventNumber_clickCount_pressure_(  # noqa: E501
        event_type,
        (local_x, float(bounds['Height']) - local_y),
        0,
        time.monotonic(),
        hwnd,
        None,
        int(time.monotonic() * 1e6) & 0x7FFFFFFF,
        1,
        1.0 if event_type in (Quartz.kCGEventLeftMouseDown, Quartz.kCGEventLeftMouseDragged) else 0.0,
    )
    if event is None:
        return False
    cg_event = event.CGEvent()
    if cg_event is None:
        return False
    for field, value in ((3, 0), (7, 3), (91, hwnd), (92, hwnd)):
        Quartz.CGEventSetIntegerValueField(cg_event, field, value)
    Quartz.CGEventSetLocation(cg_event, (x, y))
    try:
        setter = _core_graphics.CGEventSetWindowLocation
    except AttributeError as exc:
        raise RuntimeError('当前 macOS 缺少窗口后台输入接口，请选择前台模式') from exc
    setter.argtypes = [ctypes.c_void_p, _CGPoint]
    setter.restype = None
    setter(objc.pyobjc_id(cg_event), _CGPoint(local_x, local_y))
    application = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
    if application is not None and not application.isActive():
        Quartz.CGEventSetFlags(cg_event, Quartz.kCGEventFlagMaskCommand)
    Quartz.CGEventPostToPid(pid, cg_event)
    return True


def capture_window(hwnd: int):
    """读取目标窗口自己的画面，避免前台覆盖窗口污染视觉识别。"""
    require_screen_capture()
    content_ready = threading.Event()
    content_result = {}

    def on_content(content, error):
        content_result.update(content=content, error=error)
        content_ready.set()

    SC.SCShareableContent.getShareableContentExcludingDesktopWindows_onScreenWindowsOnly_completionHandler_(
        True, False, on_content
    )
    if not content_ready.wait(3):
        raise WindowCaptureError('ScreenCaptureKit 获取窗口列表超时')
    if content_result['error'] is not None or content_result['content'] is None:
        raise WindowCaptureError(f'ScreenCaptureKit 获取窗口列表失败: {content_result["error"]}')
    window = next((w for w in content_result['content'].windows() if int(w.windowID()) == int(hwnd)), None)
    if window is None:
        raise WindowCaptureError(f'ScreenCaptureKit 未找到目标窗口: {hwnd}')
    frame = window.frame()
    config = SC.SCStreamConfiguration.alloc().init()
    config.setWidth_(round(frame.size.width))
    config.setHeight_(round(frame.size.height))
    config.setShowsCursor_(False)
    config.setIgnoreShadowsSingleWindow_(True)
    content_filter = SC.SCContentFilter.alloc().initWithDesktopIndependentWindow_(window)
    image_ready = threading.Event()
    image_result = {}

    def on_image(image, error):
        image_result.update(image=image, error=error)
        image_ready.set()

    SC.SCScreenshotManager.captureImageWithFilter_configuration_completionHandler_(content_filter, config, on_image)
    if not image_ready.wait(3):
        raise WindowCaptureError('ScreenCaptureKit 窗口截图超时')
    cg_image = image_result['image']
    if image_result['error'] is not None or cg_image is None:
        raise WindowCaptureError(f'ScreenCaptureKit 窗口截图失败: {image_result["error"]}')
    bitmap = NSBitmapImageRep.alloc().initWithCGImage_(cg_image)
    data = bitmap.representationUsingType_properties_(NSBitmapImageFileTypePNG, {})
    with Image.open(BytesIO(bytes(data))) as image:
        return image.convert('RGB')


def press_named_element(root, name: str) -> bool:
    require_accessibility()
    if root is None:
        return False
    pending = [root]
    # 限制节点数，避免异常辅助功能树无限遍历。
    for _ in range(2000):
        if not pending:
            break
        element = pending.pop()
        title = ax_attribute(element, AX.kAXTitleAttribute)
        description = ax_attribute(element, AX.kAXDescriptionAttribute)
        if name in (title, description):
            if AX.AXUIElementPerformAction(element, AX.kAXPressAction) == AX.kAXErrorSuccess:
                return True
        pending.extend(ax_attribute(element, AX.kAXChildrenAttribute) or [])
    return False
