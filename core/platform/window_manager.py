"""根据宿主操作系统加载窗口管理后端。"""

import sys

from core.platform.windows_window_manager import DisplayInfo, WindowInfo

if sys.platform == 'darwin':
    from core.platform.macos_window_manager import WindowManager
elif sys.platform == 'win32':
    from core.platform.windows_window_manager import WindowManager
else:
    raise RuntimeError('目前仅支持 Windows 和 macOS')

__all__ = ['DisplayInfo', 'WindowInfo', 'WindowManager']
