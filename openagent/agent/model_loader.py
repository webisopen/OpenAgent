from loguru import logger
from typing import Any, Dict, Tuple

# Model class mapping
MODEL_CLASS_MAP: Dict[str, Tuple[str, str]] = {
    "deepseek": ("agno.models.deepseek", "DeepSeek"),
    "gpt": ("agno.models.openai", "OpenAIChat"),
    "claude": ("agno.models.anthropic", "Claude"),
}


def init_model(model_config: Any) -> Any:
    """Initialize the language model based on config

    Args:
        model_config: The model configuration object

    Returns:
        Any: Initialized model instance
    """
    logger.info("Initializing language model...")
    model_name = model_config.name
    logger.info(f"Using model: {model_name}")

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
        temperature=model_config.temperature,
        api_key=model_config.api_key,
    )
    logger.success("Model initialized successfully")
    return model
