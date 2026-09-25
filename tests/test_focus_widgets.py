from percolate.focus_widgets import grid_neighbor

GRID = [["a", "b"], ["c", "d"]]


def test_down_moves_to_next_row() -> None:
    assert grid_neighbor(GRID, "a", 1, 0) == "c"


def test_up_past_top_edge_is_none() -> None:
    assert grid_neighbor(GRID, "b", -1, 0) is None


def test_down_past_bottom_edge_is_none() -> None:
    assert grid_neighbor(GRID, "c", 1, 0) is None


def test_right_moves_to_next_column() -> None:
    assert grid_neighbor(GRID, "c", 0, 1) == "d"


def test_left_past_edge_is_none() -> None:
    assert grid_neighbor(GRID, "a", 0, -1) is None


def test_unknown_id_is_none() -> None:
    assert grid_neighbor(GRID, None, 1, 0) is None
