"""Command loader for loading command content from resolved directories.

This module implements the CommandLoader class that loads command content
(prompts, schemas, hooks) from a resolved command directory.
"""

class CommandLoader:
    """Loads command content from a resolved command directory.

    The loader reads the contents of a command directory including:
    - prompt.md (required)
    - schema.json (optional)
    - pre-hook.sh / pre.sh (optional)
    - post-hook.sh / post.sh (optional)

    Example:
        >>> loader = CommandLoader()
        >>> command = loader.load(Path(".adw/commands/plan"))
        >>> print(command.prompt)
        "..."
    """

    def __init__(self) -> None:
        """Initialize the CommandLoader."""
        pass
