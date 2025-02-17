import inspect
from typing import Any, List
from loguru import logger
import importlib
import pkgutil

from openagent.core.tool import Tool


async def init_tools(tools_config: dict) -> List[Any]:
    """Initialize tool functions based on config

    Args:
        tools_config (dict): Tool configuration dictionary

    Returns:
        List[Any]: List of initialized tool functions
    """
    logger.info("Loading tools...")
    tools = []

    for tool_path, tool_config in tools_config.items():
        try:
            # Convert path to module notation (e.g. 'twitter/search' -> 'twitter.search')
            module_path = tool_path.replace("/", ".")

            # First try direct import
            try:
                module = importlib.import_module(f"openagent.tools.{module_path}")
                tools.extend(await load_tools_from_module(module, tool_config))
                continue
            except ImportError:
                pass

            # If direct import fails, try to find the module in subdirectories
            parts = module_path.split(".")
            if len(parts) == 1:  # Single name like 'twitter_post'
                # Try to find in all subdirectories
                base_module = importlib.import_module("openagent.tools")
                for _, name, is_pkg in pkgutil.iter_modules(base_module.__path__):
                    if is_pkg:  # Look in package directories
                        try:
                            sub_module = importlib.import_module(
                                f"openagent.tools.{name}.{parts[0]}"
                            )
                            tools.extend(
                                await load_tools_from_module(sub_module, tool_config)
                            )
                            break
                        except ImportError:
                            continue
            else:  # Path like 'twitter.post'
                try:
                    # Try importing from the specified subdirectory
                    parent_module = importlib.import_module(
                        f"openagent.tools.{parts[0]}"
                    )
                    for _, name, is_pkg in pkgutil.iter_modules(parent_module.__path__):
                        if not is_pkg and name == parts[-1]:
                            sub_module = importlib.import_module(
                                f"openagent.tools.{parts[0]}.{name}"
                            )
                            tools.extend(
                                await load_tools_from_module(sub_module, tool_config)
                            )
                            break
                except ImportError as e:
                    logger.error(f"Failed to import from subdirectory {parts[0]}: {e}")

        except Exception as e:
            logger.error(f"Error loading tools from {tool_path}: {e}")

    logger.success(f"Loaded {len(tools)} tools successfully")
    return tools


async def load_tools_from_module(module: Any, tool_config: dict) -> List[Any]:
    """Load all tool classes from a module

    Args:
        module (Any): The imported module
        tool_config (dict): Configuration for the tools

    Returns:
        List[Any]: List of initialized tool functions
    """
    tools = []

    # Import all concrete implementations of Tool
    for name, obj in inspect.getmembers(module):
        if (
            inspect.isclass(obj)
            and issubclass(obj, Tool)
            and not inspect.isabstract(obj)
        ):
            # Initialize the tool instance
            tool_instance = obj()

            # Get the tool's generic type parameter for config
            config_class = None
            if hasattr(obj, "__orig_bases__"):
                for base in obj.__orig_bases__:
                    if (
                        hasattr(base, "__origin__")
                        and base.__origin__ is Tool
                        and hasattr(base, "__args__")
                        and len(base.__args__) > 0
                    ):
                        config_class = base.__args__[0]
                        break

            # Setup the tool with config from yaml if available
            if config_class:
                if tool_config:
                    config_instance = config_class(**tool_config)
                else:
                    config_instance = config_class()
                await tool_instance.setup(config_instance)

            # Convert to Function object and add to tools list
            tools.append(tool_instance.to_function())
            logger.info(f"Loaded tool: {name} from {module.__name__}")

    return tools
