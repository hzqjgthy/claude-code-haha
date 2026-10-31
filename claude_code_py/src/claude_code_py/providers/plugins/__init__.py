"""Plugin loading adapters."""

from claude_code_py.providers.plugins.loader import (
    PluginLoadResult,
    load_plugin_from_path,
    load_plugins,
)
from claude_code_py.providers.plugins.manifest import (
    LoadedPlugin,
    PluginManifest,
)

__all__ = [
    "LoadedPlugin",
    "PluginLoadResult",
    "PluginManifest",
    "load_plugin_from_path",
    "load_plugins",
]
