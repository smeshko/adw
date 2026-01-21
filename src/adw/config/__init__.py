"""ADW configuration package.

Provides three-tier configuration resolution:
1. Project config (.adw/project.yaml)
2. User config (~/.config/adw/config.yaml)
3. Bundled defaults based on detected project type

Also provides project initialization and type detection.
"""

from adw.config.detector import ProjectType, ProjectTypeDetector
from adw.config.initializer import ProjectInitializer
from adw.config.loader import ConfigLoader
from adw.config.registry import ConfigRegistry, SettingDefinition
from adw.config.yaml_generator import (
    YAMLWithComments,
    generate_all_phase_configs,
)

__all__ = [
    "ConfigLoader",
    "ConfigRegistry",
    "ProjectInitializer",
    "ProjectType",
    "ProjectTypeDetector",
    "SettingDefinition",
    "YAMLWithComments",
    "generate_all_phase_configs",
]
