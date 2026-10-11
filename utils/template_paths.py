"""模板资源路径工具：用于平台模板扫描与平台名规范化。"""

from __future__ import annotations

import sys
from pathlib import Path

DEFAULT_TEMPLATE_PLATFORM = 'qq'
VALID_TEMPLATE_PLATFORMS = {'qq', 'wechat'}


def normalize_template_platform(platform: str | None) -> str:
    """规范化平台名称；不合法值统一回退为 `qq`。"""
    text = str(platform or '').strip().lower()
    if text in VALID_TEMPLATE_PLATFORMS:
        return text
    return DEFAULT_TEMPLATE_PLATFORM


def project_root() -> Path:
    """返回项目根目录。"""
    return Path(__file__).resolve().parents[1]


def resolve_template_file(file_path: str | Path) -> Path:
    """优先使用当前宿主实测的模板，保留 QQ/微信业务平台字段。"""
    path = Path(file_path)
    root = project_root()
    if not path.is_absolute():
        path = root / path
    if sys.platform == 'darwin' and path.is_relative_to(root / 'templates'):
        mac_path = root / 'templates' / 'macos' / path.relative_to(root / 'templates')
        if mac_path.is_file():
            return mac_path
    return path


def template_root(base_dir: str = 'templates') -> Path:
    """返回模板根目录（支持传入绝对路径覆盖）。"""
    base = Path(base_dir)
    if base.is_absolute():
        return base
    return (project_root() / base).resolve()


def template_scan_roots(
    platform: str | None,
    base_dir: str = 'templates',
) -> list[Path]:
    """返回模板扫描目录列表（低优先级在前，高优先级在后）。"""
    root = template_root(base_dir)
    roots: list[Path] = [root / DEFAULT_TEMPLATE_PLATFORM]
    selected = normalize_template_platform(platform)
    if selected != DEFAULT_TEMPLATE_PLATFORM:
        roots.append(root / selected)
    return roots
