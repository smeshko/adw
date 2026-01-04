"""Evidence config loader for API endpoints and CLI commands.

This module provides functionality to load evidence gathering configurations
from the project's .adw/project.yaml file.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError

from adw.logging import LogCategory, get_logger
from adw.models.evidence import AuthConfig, AuthType, CommandConfig, EndpointConfig


# =============================================================================
# API Evidence Configuration
# =============================================================================


class EvidenceConfig(BaseModel):
    """Configuration for API evidence capture.

    Loaded from the 'evidence' section of .adw/project.yaml.

    Attributes:
        base_url: Base URL for all API endpoints
        auth: Optional authentication configuration
        endpoints: List of endpoint configurations to capture

    Example:
        >>> config = EvidenceConfig(
        ...     base_url="http://localhost:8000",
        ...     endpoints=[EndpointConfig(name="health", path="/health")],
        ... )
    """

    base_url: str = Field(..., description="Base URL for API endpoints")
    auth: AuthConfig | None = Field(
        default=None, description="Authentication configuration"
    )
    endpoints: list[EndpointConfig] = Field(
        default_factory=list, description="Endpoints to capture"
    )


def load_evidence_config(project_root: Path) -> EvidenceConfig | None:
    """Load evidence configuration from project config file.

    Reads the .adw/project.yaml file and extracts the 'evidence'
    section, parsing it into an EvidenceConfig model.

    Args:
        project_root: Path to the project root directory

    Returns:
        EvidenceConfig if evidence section exists, None otherwise

    Example:
        >>> config = load_evidence_config(Path("/my/project"))
        >>> if config:
        ...     print(f"Base URL: {config.base_url}")
    """
    logger = get_logger()

    config_path = project_root / ".adw" / "project.yaml"
    if not config_path.exists():
        logger.debug(
            LogCategory.STATE,
            f"No config file found at {config_path}",
        )
        return None

    try:
        content = config_path.read_text()
        data = yaml.safe_load(content)

        if not isinstance(data, dict):
            return None

        evidence_data = data.get("evidence")
        if not evidence_data:
            logger.debug(
                LogCategory.STATE,
                "No 'evidence' section in project config",
            )
            return None

        return _parse_evidence_config(evidence_data)

    except yaml.YAMLError as e:
        logger.warn(
            LogCategory.STATE,
            f"Failed to parse config file: {e}",
        )
        return None

    except (OSError, IOError) as e:
        logger.warn(
            LogCategory.STATE,
            f"Failed to read config file: {e}",
        )
        return None


def _parse_evidence_config(data: dict[str, Any]) -> EvidenceConfig:
    """Parse evidence configuration from dictionary.

    Args:
        data: Evidence section from config file

    Returns:
        Parsed EvidenceConfig model
    """
    base_url = data.get("base_url", "")

    # Parse auth config if present
    auth = None
    auth_data = data.get("auth")
    if auth_data:
        auth = _parse_auth_config(auth_data)

    # Parse endpoints
    endpoints = []
    endpoints_data = data.get("endpoints", [])
    for ep_data in endpoints_data:
        endpoint = _parse_endpoint_config(ep_data)
        endpoints.append(endpoint)

    return EvidenceConfig(
        base_url=base_url,
        auth=auth,
        endpoints=endpoints,
    )


def _parse_auth_config(data: dict[str, Any]) -> AuthConfig:
    """Parse authentication configuration.

    Args:
        data: Auth section from config

    Returns:
        Parsed AuthConfig model
    """
    auth_type_str = data.get("type", "bearer")
    auth_type = AuthType(auth_type_str)

    return AuthConfig(
        type=auth_type,
        token_env=data.get("token_env"),
        header=data.get("header"),
        key_env=data.get("key_env"),
    )


def _parse_endpoint_config(data: dict[str, Any]) -> EndpointConfig:
    """Parse endpoint configuration.

    Args:
        data: Endpoint data from config

    Returns:
        Parsed EndpointConfig model
    """
    return EndpointConfig(
        name=data.get("name", "unnamed"),
        method=data.get("method", "GET"),
        path=data.get("path", "/"),
        headers=data.get("headers"),
        body=data.get("body"),
        expected_status=data.get("expected_status"),
        timeout_seconds=data.get("timeout_seconds", 30),
    )


# =============================================================================
# CLI Evidence Configuration
# =============================================================================


def load_evidence_commands(project_root: Path) -> list[CommandConfig]:
    """Load evidence command configurations from project config.

    Reads the evidence.commands section from .adw/project.yaml and
    returns a list of validated CommandConfig objects.

    Args:
        project_root: Path to the project root directory

    Returns:
        List of CommandConfig objects, or empty list if none configured

    Note:
        Invalid command configurations are silently skipped with a warning.
        Returns empty list if config file doesn't exist or has no commands.

    Example:
        >>> from pathlib import Path
        >>> commands = load_evidence_commands(Path("/my/project"))
        >>> for cmd in commands:
        ...     print(f"{cmd.name}: {cmd.cmd}")
        version: adw --version
    """
    logger = get_logger()
    config_path = project_root / ".adw" / "project.yaml"

    if not config_path.exists():
        return []

    try:
        content = config_path.read_text()
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        logger.warn(
            LogCategory.STATE,
            f"Failed to parse evidence config: {e}",
        )
        return []
    except OSError as e:
        logger.warn(
            LogCategory.STATE,
            f"Failed to read evidence config file: {e}",
        )
        return []

    if not isinstance(data, dict):
        return []

    evidence = data.get("evidence")
    if not isinstance(evidence, dict):
        return []

    commands_data = evidence.get("commands")
    if not isinstance(commands_data, list):
        return []

    commands: list[CommandConfig] = []
    for cmd_data in commands_data:
        if not isinstance(cmd_data, dict):
            continue

        try:
            command = CommandConfig.model_validate(cmd_data)
            commands.append(command)
        except ValidationError as e:
            logger.warn(
                LogCategory.STATE,
                f"Skipping invalid command config: {e}",
            )
            continue

    return commands
