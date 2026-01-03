"""ADW configuration loading package.

Provides three-tier configuration resolution:
1. Project config (.adw/project.yaml)
2. User config (~/.config/adw/config.yaml)
3. Bundled defaults based on detected project type
"""

from adw.config.detector import ProjectType, ProjectTypeDetector
from adw.config.loader import ConfigLoader

__all__ = ["ConfigLoader", "ProjectType", "ProjectTypeDetector"]
