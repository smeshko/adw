"""ADW configuration package.

Provides three-tier configuration resolution:
1. Project config (.adw/project.yaml)
2. User config (~/.config/adw/config.yaml)
3. Bundled defaults based on detected project type

Also provides project initialization and type detection.
"""

from adw.config.detector import ProjectTypeDetector
from adw.config.initializer import ProjectInitializer
from adw.config.loader import ConfigLoader

__all__ = ["ConfigLoader", "ProjectInitializer", "ProjectTypeDetector"]
