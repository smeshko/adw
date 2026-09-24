"""ADW configuration package.

Provides three-tier configuration resolution:
1. Project config (.adw/project.yaml)
2. User config (~/.config/adw/config.yaml)
3. Bundled defaults based on detected project type

``ConfigLoader`` stays importable from the package path because project hook
scripts written against older ADW versions import it from here.
"""

from adw.config.loader import ConfigLoader

__all__ = ["ConfigLoader"]
