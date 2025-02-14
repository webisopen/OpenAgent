import asyncio
import inspect
import time
import threading
from textwrap import dedent

import pyfiglet
from agno.agent import Agent
from agno.storage.agent.sqlite import SqliteAgentStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger
from pydantic import BaseModel
from celery import Celery
from celery.apps.worker import Worker as CeleryWorker
from celery.apps.beat import Beat as CeleryBeat
from celery.beat import PersistentScheduler

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
        model_name = self.config.core_model.name
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
            temperature=self.config.core_model.temperature,
            api_key=self.config.core_model.api_key,
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

                        # Get the tool's generic type parameter for config
                        config_class = None
                        if hasattr(obj, '__orig_bases__'):
                            for base in obj.__orig_bases__:
                                if (hasattr(base, '__origin__') and 
                                    base.__origin__ is Tool and 
                                    hasattr(base, '__args__') and 
                                    len(base.__args__) > 0):
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
            goal=self.config.goal,
            debug_mode=self.config.debug_mode,
            telemetry=False,
            monitoring=False,
            storage=(
                SqliteAgentStorage(
                    table_name="agent_sessions", db_file="storage/agent_sessions.db"
                )
                if self.config.stateful
                else None
            ),
        )

        # Initialize scheduled tasks if any are configured
        if self.config.tasks:
            self._init_scheduled_tasks()

        logger.success("Agent initialized successfully")

    def _init_scheduled_tasks(self):
        """Initialize and start scheduled tasks from config"""
        logger.info("Initializing scheduled tasks...")

        for task_id, task_config in self.config.tasks.items():
            if task_config.schedule.type == "queue":
                self._init_celery_task(task_id, task_config)
            else:
                # Default to local scheduler
                self.scheduler.add_job(
                    func=self._run_scheduled_task,
                    trigger=IntervalTrigger(seconds=task_config.interval),
                    args=[task_config.query],
                    id=task_id,
                    name=f"Task_{task_id}",
                )
                logger.info(
                    f"Scheduled local task '{task_id}' with interval: {task_config.interval} seconds"
                )

        # Start the local scheduler if we have any local tasks
        if any(task.schedule.type == "local" for task in self.config.tasks.values()):
            self.scheduler.start()
            logger.success("Local scheduler started successfully")

    def _init_celery_task(self, task_id: str, task_config):
        """Initialize a Celery task

        Args:
            task_id (str): The ID of the task
            task_config (TaskConfig): The task configuration
        """
        # Create Celery app if not exists
        if not hasattr(self, "celery_app"):
            self.celery_app = Celery(
                "openagent",
                broker=task_config.schedule.broker_url,
                backend=task_config.schedule.result_backend,
            )

            # Configure Celery to run tasks sequentially
            self.celery_app.conf.update(
                task_acks_late=True,  # Tasks are acknowledged after completion
                worker_prefetch_multiplier=1,  # Only prefetch one task at a time
                task_track_started=True,  # Track when tasks are started
                task_serializer="json",
                accept_content=["json"],
                result_serializer="json",
                timezone="UTC",
                enable_utc=True,
            )

            # Start Celery worker and beat in separate threads
            self._start_celery_threads()

        # Use a simple flag to track task execution status
        task_running = False

        @self.celery_app.task(
            name=f"openagent.task.{task_id}",
            bind=True,  # Bind task instance to first argument
            max_retries=0,  # Allow retries on failure
            default_retry_delay=0,  # Wait 0 seconds between retries
        )
        def celery_task(self_task):
            nonlocal task_running

            # If task is already running, skip this execution
            if task_running:
                logger.warning(
                    f"Task {task_id} is already running, skipping this execution"
                )
                return None

            task_running = True
            try:
                # Run the task in the event loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        self._run_scheduled_task(task_config.query)
                    )
                    return result
                finally:
                    loop.close()
            except Exception as exc:
                logger.error(f"Task {task_id} failed: {exc}")
                self_task.retry(exc=exc)
            finally:
                task_running = False

        # Add to Celery beat schedule with additional options
        self.celery_app.conf.beat_schedule = {
            **self.celery_app.conf.beat_schedule,
            task_id: {
                "task": f"openagent.task.{task_id}",
                "schedule": task_config.interval,
                "options": {
                    "queue": "sequential_queue",  # Use a dedicated queue
                    "expires": task_config.interval
                    - 1,  # Task expires before next schedule
                    "ignore_result": True,  # Don't store task results
                },
            },
        }

        logger.info(
            f"Scheduled Celery task '{task_id}' with interval: {task_config.interval} seconds"
        )

    def _start_celery_threads(self):
        """Start Celery worker and beat in separate threads"""

        def start_worker():
            # Configure worker for sequential processing
            worker = CeleryWorker(
                app=self.celery_app,
                queues=["sequential_queue"],  # Only process from sequential queue
                concurrency=1,  # Single worker process
                pool="solo",  # Use solo pool for true sequential processing
            )
            worker.start()
            logger.info("Celery worker started in sequential mode")

        def start_beat():
            beat = CeleryBeat(app=self.celery_app, scheduler_cls=PersistentScheduler)
            beat.run()
            logger.info("Celery beat started")

        # Create and start worker thread
        self.worker_thread = threading.Thread(
            target=start_worker, name="celery_worker_thread", daemon=True
        )
        self.worker_thread.start()

        # Create and start beat thread
        self.beat_thread = threading.Thread(
            target=start_beat, name="celery_beat_thread", daemon=True
        )
        self.beat_thread.start()

        logger.success("Celery worker and beat threads started in sequential mode")

    async def _run_scheduled_task(self, question: str):
        """Execute a scheduled task

        Args:
            question (str): The question/prompt to run with the agent
        """
        try:
            logger.info(f"Running scheduled task with question: {question}")
            response = await self.agent.arun(question)
            logger.info(
                f"Task completed successfully, agent response: {response.content}"
            )
        except Exception as e:
            logger.error(f"Error running scheduled task: {e}")

    def stop_scheduler(self):
        """Stop all schedulers"""
        # Stop local scheduler
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Local task scheduler stopped")

        # Stop Celery app if exists
        if hasattr(self, "celery_app"):
            # Shutdown Celery worker and beat
            self.celery_app.control.shutdown()
            logger.info("Celery worker and beat shutdown initiated")

            # Wait for threads to finish if they exist
            if hasattr(self, "worker_thread"):
                self.worker_thread.join(timeout=5)
            if hasattr(self, "beat_thread"):
                self.beat_thread.join(timeout=5)

            self.celery_app.control.purge()
            logger.info("Celery tasks purged")
