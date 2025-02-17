from textwrap import dedent

from agno.agent import Agent
from agno.storage.agent.sqlite import SqliteAgentStorage
from loguru import logger

from openagent.agent.banner import print_banner
from openagent.agent.config import AgentConfig
from openagent.agent.model_loader import init_model
from openagent.agent.scheduler import SchedulerManager
from openagent.agent.tool_loader import init_tools

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
        self.scheduler_manager = SchedulerManager()

    async def start(self):
        """Start the agent and initialize all components"""
        await self._init_agent()
        logger.success("Agent started successfully")

    async def _init_agent(self):
        """Initialize the agent with model and tools"""
        logger.info("Initializing agent...")

        # Initialize model and tools
        model = init_model(self.config.core_model)
        tools = await init_tools(self.config)

        # Create agent instance
        self.agent = Agent(
            model=model,
            description=dedent(self.config.description),
            tools=tools,
            add_history_to_messages=self.config.stateful,
            markdown=self.config.markdown,
            instructions=self.config.instructions,
            goal=(
                "\n".join(f"{i + 1}. {goal}" for i, goal in enumerate(self.config.goal))
                if self.config.goal
                else None
            ),
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
            self.scheduler_manager.init_scheduled_tasks(
                self.config.tasks, self._run_scheduled_task
            )

        logger.success("Agent initialized successfully")

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

    def stop(self):
        """Stop the agent and all its components"""
        self.scheduler_manager.stop()
