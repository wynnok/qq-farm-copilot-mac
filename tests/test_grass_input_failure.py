"""种草拖拽输入失败不能继续执行或报告完成。"""

from types import SimpleNamespace

from tasks.grass import TaskGrass


def test_grass_does_not_move_or_release_when_drag_start_fails():
    calls = []
    device = SimpleNamespace(
        drag_down_point=lambda *args, **kwargs: False,
        drag_move_point=lambda *args, **kwargs: calls.append('move') or True,
        drag_up=lambda: calls.append('up') or True,
        sleep=lambda seconds: None,
    )
    task = TaskGrass.__new__(TaskGrass)
    task.engine = SimpleNamespace(device=device)
    task.ui = SimpleNamespace(device=device)
    result = task._drag_grass_to_lands((100, 100), [SimpleNamespace(order=1, center=(200, 200))])
    assert result is False
    assert calls == []


def test_open_grass_popup_checks_state_and_tries_uncovered_plot():
    clicks = []
    device = SimpleNamespace(click_point=lambda x, y, **kw: clicks.append((x, y)) or True, sleep=lambda seconds: None)
    task = TaskGrass.__new__(TaskGrass)
    task.ui = SimpleNamespace(device=device)
    task._detect_grass_or_end = lambda: ('grass', (120, 300), 0.9) if len(clicks) == 2 else None
    cells = [SimpleNamespace(label='1-1', center=(100, 200)), SimpleNamespace(label='2-2', center=(140, 240))]
    assert task._open_grass_popup(land_cells=cells)
    assert clicks == [(100, 200), (140, 240)]


def test_macos_grass_single_anchor_uses_measured_grid_width(monkeypatch):
    import sys

    from utils.land_grid import get_lands_from_land_anchor

    monkeypatch.setattr(sys, 'platform', 'darwin')
    task = TaskGrass.__new__(TaskGrass)
    task.engine = SimpleNamespace(
        config=SimpleNamespace(planting=SimpleNamespace(window_platform=SimpleNamespace(value='qq')))
    )
    task.ui = SimpleNamespace(device=SimpleNamespace(screenshot=lambda: None), appear_location=lambda *args, **kw: None)
    task.appear_land_right = lambda **kw: (412, 544)
    actual = task._collect_land_cells_for_grass()
    expected = get_lands_from_land_anchor((412, 544), (43, 583))
    assert [cell.center for cell in actual] == [cell.center for cell in expected]


def test_open_grass_popup_finds_immature_plot_beyond_first_merged_group():
    clicks = []
    device = SimpleNamespace(click_point=lambda x, y, **kw: clicks.append((x, y)) or True, sleep=lambda seconds: None)
    task = TaskGrass.__new__(TaskGrass)
    task.ui = SimpleNamespace(device=device)
    task._detect_grass_or_end = lambda: ('grass', (120, 300), 0.9) if (190, 601) in clicks else None
    cells = [
        SimpleNamespace(label='1-1', center=(266, 488)),
        SimpleNamespace(label='2-2', center=(265, 526)),
        SimpleNamespace(label='5-3', center=(190, 601)),
    ]
    assert task._open_grass_popup(land_cells=cells)
    assert clicks[-1] == (190, 601)
