"""Windows 注册表公共读写方法。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

if sys.platform == 'win32':
    import winreg


def _preferences_path() -> Path:
    # 源码运行的数据路径偏好也保存在仓库内，避免修改系统偏好设置。
    return Path(__file__).resolve().parent.parent / '.dev_appdata' / 'path_preferences.json'


def read_current_user_string(subkey: str, name: str) -> str | None:
    """读取 HKCU 下的字符串值。"""
    try:
        if sys.platform != 'win32':
            values = json.loads(_preferences_path().read_text(encoding='utf-8'))
            return values.get(str(subkey), {}).get(str(name)) or None
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, str(subkey), 0, winreg.KEY_READ) as key:
            value, _value_type = winreg.QueryValueEx(key, str(name))
    except FileNotFoundError:
        return None
    except Exception:
        return None
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def write_current_user_string(subkey: str, name: str, value: str) -> bool:
    """写入 HKCU 下的字符串值。"""
    try:
        if sys.platform != 'win32':
            path = _preferences_path()
            values = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
            values.setdefault(str(subkey), {})[str(name)] = str(value)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(values, ensure_ascii=False, indent=2), encoding='utf-8')
            return True
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, str(subkey)) as key:
            winreg.SetValueEx(key, str(name), 0, winreg.REG_SZ, str(value))
        return True
    except Exception:
        return False
