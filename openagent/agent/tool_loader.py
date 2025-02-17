import inspect
from typing import Any, List
from loguru import logger

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

    for tool_name, tool_config in tools_config.items():
        try:
            module_path = tool_name.replace('/', '.')
            module = __import__(f"openagent.tools.{module_path}", fromlist=["*"])

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
                    logger.info(f"Loaded tool: {name} from {tool_name}")

        except ImportError as e:
            logger.error(f"Failed to import tool module {tool_name}: {e}")
        except Exception as e:
            logger.error(f"Error loading tools from {tool_name}: {e}")

    logger.success(f"Loaded {len(tools)} tools successfully")
    return tools
