import asyncio
import inspect
import time
from textwrap import dedent

import pyfiglet
from agno.agent import Agent
from agno.storage.agent.sqlite import SqliteAgentStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
from pydantic import BaseModel

from openagent.agent.config import AgentConfig
from openagent.core.tool import Tool


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
        self.shared_context: dict[object, object] = {}
        self.agent = None
        self.scheduler = AsyncIOScheduler()

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

                # Import all concrete implementations of Tool
                for name, obj in inspect.getmembers(module):
                    if (
                        inspect.isclass(obj)
                        and issubclass(obj, Tool)
                        and not inspect.isabstract(obj)
                    ):
                        # Initialize the tool instance
                        tool_instance = obj()

                        # If tool has a config defined in the module, use it
                        config_class = None
                        for config_name, config_obj in inspect.getmembers(module):
                            if (
                                inspect.isclass(config_obj)
                                and issubclass(config_obj, BaseModel)
                                and config_name.endswith("Config")
                            ):
                                config_class = config_obj
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
    async def start(self):
        # Initialize agent with tools
        await self._init_agent()
        logger.success("Agent started successfully")

    async def _init_agent(self):
        """Initialize the agent with model and tools"""
        logger.info("Initializing agent...")
        
        # Initialize model and tools
        model = self._init_model()
        tools = await self._init_tools()
        
        # Create agent instance with all necessary parameters
        self.agent = Agent(
            model=model,
            description=dedent(self.config.description),
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

        # Initialize scheduled tasks if any are configured
        if self.config.tasks:
            self._init_scheduled_tasks()

        logger.success("Agent initialized successfully")

    def _init_scheduled_tasks(self):
        """Initialize and start scheduled tasks from config"""
        logger.info("Initializing scheduled tasks...")
        
        for task_id, task_config in self.config.tasks.items():
            self.scheduler.add_job(
                func=self._run_scheduled_task,
                trigger=IntervalTrigger(seconds=task_config.interval),
                args=[task_config.question],
                id=task_id,
                name=f"Task_{task_id}"
            )
            logger.info(f"Scheduled task '{task_id}' with interval: {task_config.interval} seconds")
        
        # Start the scheduler
        self.scheduler.start()
        logger.success("Scheduler started successfully")

    async def _run_scheduled_task(self, question: str):
        """Execute a scheduled task
        
        Args:
            question (str): The question/prompt to run with the agent
        """
        try:
            logger.info(f"Running scheduled task with question: {question}")
            response = await self.agent.arun(question)
            logger.info(f"Task completed successfully, agent response: {response.content}")
        except Exception as e:
            logger.error(f"Error running scheduled task: {e}")

    def stop_scheduler(self):
        """Stop the task scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Task scheduler stopped")
