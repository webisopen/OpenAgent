import yaml
from pathlib import Path
from dotenv import load_dotenv
from collections import OrderedDict

from openagent.database.models.agent import Agent


class OrderedYamlDumper(yaml.Dumper):
    """Custom YAML dumper that preserves dictionary order"""

    pass


def _represent_ordereddict(dumper, data):
    """Custom representer for OrderedDict to maintain key order"""
    return dumper.represent_mapping("tag:yaml.org,2002:map", data.items())


OrderedYamlDumper.add_representer(OrderedDict, _represent_ordereddict)


def generate_twitter_agent_yaml(
    agent: Agent, output_dir: str = "agent_deployments"
) -> str:
    """
    Generate a YAML configuration file for a Twitter agent.

    Args:
        agent: The agent database model instance
        output_dir: Directory to save the YAML file (defaults to agent_deployments folder)

    Returns:
        str: Path to the generated YAML file
    """
    # Load environment variables
    load_dotenv()

    # Extract Twitter tool config (assuming it's the first or only tool)
    twitter_config = None
    token_price_config = None

    for tool_config in agent.tool_configs_list:
        if "twitter" in tool_config.name.lower():
            twitter_config = tool_config.parameters.config
        elif "token_price" in tool_config.name.lower():
            token_price_config = True

    if not twitter_config:
        raise ValueError("Twitter tool configuration not found in agent")

    # Get the ticker from agent or use "BTC" as default
    ticker = agent.ticker if hasattr(agent, "ticker") and agent.ticker else "BTC"

    # Generate the query using the agent's ticker
    query = f"Find out the current price of {ticker}, then tweet it."

    # Build the YAML configuration dictionary with exact key ordering as in the example
    yaml_config = OrderedDict(
        [
            ("version", "1.0"),
            ("name", agent.name),
            (
                "description",
                agent.description
                or "you are a help assistant, your could call token price tool to get token price and then call twitter post tool to tweet it.",
            ),
            ("debug_mode", True),
            ("markdown", True),
            ("stateful", True),
            (
                "core_model",
                OrderedDict(
                    [
                        ("provider", "openai"),
                        ("name", "gpt-4o"),
                        ("temperature", 0.7),
                        ("api_key", "${OPENAI_API_KEY}"),
                    ]
                ),
            ),
            (
                "tasks",
                OrderedDict(
                    [
                        (
                            "market_monitoring",
                            OrderedDict(
                                [
                                    (
                                        "schedule",
                                        OrderedDict(
                                            [
                                                (
                                                    "type",
                                                    "local",
                                                )  # This task uses local scheduling
                                            ]
                                        ),
                                    ),
                                    ("interval", 5),
                                    # The delay_variation (in seconds) specifies the maximum random delay that can be added to the interval
                                    ("delay_variation", 2),
                                    ("query", query),
                                ]
                            ),
                        )
                    ]
                ),
            ),
            (
                "tools",
                OrderedDict(
                    [
                        (
                            "twitter/post",
                            OrderedDict(
                                [
                                    (
                                        "credentials",
                                        OrderedDict(
                                            [
                                                (
                                                    "bearer_token",
                                                    "${TWITTER_BEARER_TOKEN}",
                                                ),
                                                ("api_key", "${TWITTER_API_KEY}"),
                                                ("api_secret", "${TWITTER_API_SECRET}"),
                                                (
                                                    "access_token",
                                                    twitter_config.get("access_token"),
                                                ),
                                                (
                                                    "access_token_secret",
                                                    twitter_config.get(
                                                        "access_token_secret"
                                                    ),
                                                ),
                                            ]
                                        ),
                                    )
                                ]
                            ),
                        )
                    ]
                ),
            ),
        ]
    )

    # Add token_price tool if it exists
    if token_price_config:
        yaml_config["tools"]["token_price"] = OrderedDict(
            [("coingecko_api_key", "${COINGECKO_API_KEY}")]
        )

    # Ensure the output directory exists
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Generate the file name using wallet_address and agent_id
    wallet_address = (
        agent.wallet_address
        if hasattr(agent, "wallet_address") and agent.wallet_address
        else "default_wallet"
    )
    agent_id = agent.id if hasattr(agent, "id") and agent.id else "default_id"
    file_name = f"{wallet_address}_{agent_id}.yaml"
    file_path = output_path / file_name

    # Write the YAML file with preserved ordering
    with open(file_path, "w") as f:
        yaml.dump(
            yaml_config,
            f,
            Dumper=OrderedYamlDumper,
            default_flow_style=False,
            sort_keys=False,
        )

    return str(file_path)
