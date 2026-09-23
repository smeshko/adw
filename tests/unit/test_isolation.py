"""Guard test: the suite never reaches the real ~/.adw."""

from pathlib import Path

from adw.core.index_manager import IndexManager
from adw.core.project_registry import ProjectRegistryManager
from adw.core.stats_aggregator import StatsAggregator


def test_home_is_isolated(tmp_path: Path) -> None:
    """Test that HOME and every default ~/.adw path resolve under the test's tmp_path."""
    home = Path.home()
    global_adw = home / ".adw"

    assert home.is_relative_to(tmp_path)
    assert IndexManager().index_path.is_relative_to(global_adw)
    assert ProjectRegistryManager().registry_path.is_relative_to(global_adw)
    assert StatsAggregator().cache_path.is_relative_to(global_adw)
