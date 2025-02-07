import asyncio
import inspect
import time
from typing import Dict, Any

import pyfiglet
from agno.agent import Agent
from agno.storage.agent.sqlite import SqliteAgentStorage
from loguru import logger
from pydantic import BaseModel

from openagent.core.config import AgentConfig
from openagent.core.input import Input, InputMessage
from openagent.core.output import Output
from openagent.core.tool import BaseFunction


def print_banner():
    """Print the OpenAgent ASCII banner"""
    banner = pyfiglet.figlet_format("OpenAgent", font="slant")
    version = "v0.2.0"
    print(banner)
    print(f"{' ' * 45}version {version}", flush=True)
    time.sleep(0.1)


# Print banner at module level
print_banner()


class OpenAgent:
    @staticmethod
    def from_yaml_file(config_path: str) -> "OpenAgent":
        """Create an OpenAgent instance from a yaml config file

        Args:
            config_path (str): Path to the yaml config file

        Returns:
            OpenAgent: A new OpenAgent instance
        """
        agent = OpenAgent._from_init(config_path)
        return agent

    @staticmethod
    def from_config(config: AgentConfig) -> "OpenAgent":
        """Create an OpenAgent instance from an AgentConfig object

        Args:
            config (AgentConfig): The configuration object

        Returns:
            OpenAgent: A new OpenAgent instance
        """
        return OpenAgent(config)

    @classmethod
    def _from_init(cls, config_path: str) -> "OpenAgent":
        """Private method to create instance from __init__ logic"""
        logger.info("Initializing OpenAgent...")
        config = AgentConfig.from_yaml(config_path)
        return cls(config)

    def __init__(self, config: AgentConfig):
        """Initialize OpenAgent with a config object

        Args:
            config (AgentConfig): The configuration object
        """
        self.config = config
        logger.info(f"Agent Name: {self.config.name}")
        # Shared context between inputs and outputs
        self.shared_context: dict[object, object] = {}
        self.agent = None
        # Initialize input/output handlers
        self.inputs: list[Input] = []
        self.outputs: list[Output] = []

    def _init_model(self):
        """Initialize the language model based on config"""
        logger.info("Initializing language model...")
        model_name = self.config.llm.model
        logger.info(f"Using model: {model_name}")

        # Model class mapping
        MODEL_CLASS_MAP = {
            "deepseek": ("agno.models.deepseek", "DeepSeek"),
            "gpt": ("agno.models.openai", "OpenAIChat"),
            "claude": ("agno.models.anthropic", "Claude"),
            # Add more models here as needed
        }

        # Find the appropriate model class based on model name prefix
        model_class = None
        for prefix, (module_path, class_name) in MODEL_CLASS_MAP.items():
            if model_name.startswith(prefix):
                try:
                    module = __import__(module_path, fromlist=[class_name])
                    model_class = getattr(module, class_name)
                    break
                except ImportError as e:
                    logger.error(f"Failed to import {module_path}: {e}")

        # Default to OpenAI if no matching model found
        if model_class is None:
            logger.warning("No specific model class found, defaulting to OpenAI")
            from agno.models.openai import OpenAIChat

            model_class = OpenAIChat

        # Initialize and return the model
        model = model_class(
            id=model_name,
            temperature=self.config.llm.temperature,
            api_key=self.config.llm.api_key,
        )
        logger.success("Model initialized successfully")
        return model

    async def _init_tools(self):
        """Initialize tool functions based on config"""
        logger.info("Loading tools...")
        tools = []

        for tool_name, tool_config in self.config.tools.items():
            try:
                module = __import__(f"openagent.tools.{tool_name}", fromlist=["*"])

                # Import all concrete implementations of BaseFunction
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BaseFunction) and 
                        not inspect.isabstract(obj)):
                        
                        # Initialize the tool instance
                        tool_instance = obj()
                        
                        # If tool has a config defined in the module, use it
                        config_class = None
                        for config_name, config_obj in inspect.getmembers(module):
                            if (inspect.isclass(config_obj) and 
                                issubclass(config_obj, BaseModel) and 
                                config_name.endswith('Config')):
                                config_class = config_obj
                                break
                        
                        # Setup the tool with config from yaml if available, otherwise use default
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

    def _get_concrete_implementation(self, module_path, base_class):
        """Helper function to get concrete implementation of a base class"""
        try:
            module = __import__(module_path, fromlist=["*"])
            for name, obj in inspect.getmembers(module):
                if (
                    inspect.isclass(obj)
                    and issubclass(obj, base_class)
                    and not inspect.isabstract(obj)
                ):
                    return obj
            return None
        except ImportError:
            logger.error(f"Failed to import module: {module_path}")
            return None

    async def _init_io_handlers(self):
        """Initialize input and output handlers based on config"""
        logger.info("Initializing I/O handlers...")

        # Setup inputs
        for input_name, input_config in self.config.io.inputs.items():
            try:
                module_path = f"openagent.inputs.{input_name}"
                InputClass = self._get_concrete_implementation(module_path, Input)
                if InputClass is None:
                    raise ImportError(
                        f"No concrete Input implementation found in {module_path}"
                    )

                input_handler = InputClass()
                # Convert dict to appropriate config type if needed
                if isinstance(input_config, dict):
                    config_class = InputClass.__orig_bases__[0].__args__[0]
                    input_config = config_class(**input_config)
                await input_handler.setup(input_config)
                self.inputs.append(input_handler)
                logger.info(f"Initialized input handler: {input_name}")
            except Exception as e:
                logger.error(f"Failed to initialize input handler {input_name}: {e}")

        # Setup outputs
        for output_name, output_config in self.config.io.outputs.items():
            try:
                module_path = f"openagent.outputs.{output_name}"
                OutputClass = self._get_concrete_implementation(module_path, Output)
                if OutputClass is None:
                    raise ImportError(
                        f"No concrete Output implementation found in {module_path}"
                    )

                output_handler = OutputClass()
                # Convert dict to appropriate config type if needed
                if isinstance(output_config, dict):
                    config_class = OutputClass.__orig_bases__[0].__args__[0]
                    output_config = config_class(**output_config)
                await output_handler.setup(output_config)
                self.outputs.append(output_handler)
                logger.info(f"Initialized output handler: {output_name}")
            except Exception as e:
                logger.error(f"Failed to initialize output handler {output_name}: {e}")

        logger.success("I/O handlers initialization completed")

    async def setup_io_handlers(self):
        """Setup input and output handlers"""
        await self._init_io_handlers()

    async def handle_input(self, message: str, input_context: Dict[str, Any] = None):
        """Handle input message"""
        logger.debug(f"Processing input: {message[:100]}...")

        # Update shared context with input context
        if input_context:
            self.shared_context.update(input_context)

        response = await self.agent.arun(message)

        # Send response to all configured outputs
        for output in self.outputs:
            try:
                # Share context with output handler
                output.context = self.shared_context.copy()
                await output.send(response.content)
                logger.debug(f"{output.__class__.__name__} output sent")
            except Exception as e:
                logger.error(f"Failed to send response through output: {e}")

    async def _init_agent(self):
        """Initialize the agent with tools"""
        tools = await self._init_tools()
        self.agent = Agent(
            model=self._init_model(),
            description=self.config.description,
            tools=tools,
            add_history_to_messages=self.config.stateful,
            markdown=self.config.markdown,
            instructions=self.config.instructions,
            debug_mode=self.config.debug_mode,
            storage=SqliteAgentStorage(
                table_name="agent_sessions", db_file="storage/agent_sessions.db"
            )
            if self.config.stateful
            else None,
        )

    async def start(self):
        # Initialize agent with tools
        await self._init_agent()
        
        # Setup IO handlers
        await self.setup_io_handlers()

        # Start listening on all input handlers
        input_tasks = []
        for input_handler in self.inputs:
            input_tasks.append(asyncio.create_task(self._listen_input(input_handler)))

        logger.success("Agent started successfully")
        await asyncio.gather(*input_tasks)

    async def _listen_input(self, input_handler: Input):
        """Listen for messages from an input handler"""
        try:
            logger.info(
                f"Listening for messages from {input_handler.__class__.__name__}"
            )
            await asyncio.sleep(0.2)
            async for message in input_handler.listen():
                if isinstance(message, InputMessage):
                    # If it's an InputMessage, use its message field and update context with session_id
                    self.agent.session_id = message.session_id
                    await self.handle_input(message.message, input_handler.context)
                else:
                    # If it's a string, handle it directly
                    await self.handle_input(message, input_handler.context)
        except Exception as e:
            logger.error(f"Error in input handler: {e}")
