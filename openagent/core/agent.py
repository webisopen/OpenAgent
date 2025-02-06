import asyncio
import inspect
from typing import List, Dict, Any

import pyfiglet
from agno.agent import Agent
from loguru import logger

from openagent.core.config import AgentConfig
from openagent.core.input import Input
from openagent.core.output import Output


def print_banner():
    """Print the OpenAgent ASCII banner"""
    banner = pyfiglet.figlet_format("OpenAgent", font="slant")
    version = "v0.2.0"
    print("\n" + banner)
    print(f"{' ' * 45}version {version}\n", flush=True)


# Print banner at module level
print_banner()


class OpenAgent:
    def __init__(self, config_path: str):
        """Initialize OpenAgent with a yaml config file"""
        logger.info("Initializing OpenAgent...")
        self.config = AgentConfig.from_yaml(config_path)

        self.name = self.config.name
        self.description = self.config.description
        logger.info(f"Agent Name: {self.name}")

        # Initialize components
        logger.info("Setting up components...")
        self.model = self._init_model()
        self.tools = self._init_tools()

        # Shared context between inputs and outputs
        self.shared_context: Dict[str, Any] = {}

        self.agent = Agent(
            model=self.model,
            description=self.config.llm.system_prompt or self.description,
            tools=self.tools,
            markdown=True,
        )
        logger.success("Agent initialization completed")

        # Initialize input/output handlers
        self.inputs: List[Input] = []
        self.outputs: List[Output] = []

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

    def _init_tools(self):
        """Initialize tool functions based on config"""
        logger.info("Loading tools...")
        tools = []

        for tool_name in self.config.tools:
            try:
                module = __import__(f"openagent.tools.{tool_name}", fromlist=["*"])

                # Import all non-private functions from the module
                for name, obj in inspect.getmembers(module):
                    if inspect.isfunction(obj) and not name.startswith("_"):
                        tools.append(obj)
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

    async def start(self):
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
            await asyncio.sleep(0.5)
            logger.info(
                f"Listening for messages from {input_handler.__class__.__name__}"
            )

            async for message in input_handler.listen():
                # Pass input handler's context to handle_input
                await self.handle_input(message, input_handler.context)
        except Exception as e:
            logger.error(f"Error in input handler: {e}")
