from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from openagent.database import get_db
from openagent.database.models.agent import Agent, AgentStatus
from openagent.database.models.model import Model
from openagent.database.models.tool import Tool
from openagent.router.error import APIExceptionResponse
from openagent.router.routes.models.auth import Auth
from openagent.router.routes.models.request import CreateAgentRequest
from openagent.router.routes.models.response import (
    AgentListResponse,
    AgentResponse,
    PublicAgentResponse,
    ResponseModel,
)
from openagent.tools.tool_config import ToolConfig
from openagent.agent.yaml_generator import generate_twitter_agent_yaml

auth_handler = Auth()

router = APIRouter(prefix="/agents", tags=["agents"])

# Load environment variables at module initialization
load_dotenv()


def check_tool_configs(
    tool_configs: list[ToolConfig], db: Session
) -> APIExceptionResponse | None:
    # check if the tool_names are unique
    tool_names = []
    for tool_config in tool_configs:
        if tool_config.name in tool_names:
            return APIExceptionResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                error=f"Duplicate tool name: {tool_config.name}",
            )
        tool_names.append(tool_config.name)

    tool_ids = {tool_config.tool_id for tool_config in tool_configs}
    model_ids = {tool_config.model_id for tool_config in tool_configs}

    # check if the tool_ids and model_ids are valid
    existing_tools = db.query(Tool.id).filter(Tool.id.in_(tool_ids)).all()
    existing_tool_ids = {tool.id for tool in existing_tools}
    invalid_tool_ids = tool_ids - existing_tool_ids
    if invalid_tool_ids:
        return APIExceptionResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            error=f"Invalid tool_ids: {invalid_tool_ids}",
        )

    existing_models = db.query(Model.id).filter(Model.id.in_(model_ids)).all()
    existing_model_ids = {model.id for model in existing_models}
    invalid_model_ids = model_ids - existing_model_ids
    if invalid_model_ids:
        return APIExceptionResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            error=f"Invalid model_ids: {invalid_model_ids}",
        )

    return None


@router.post(
    "",
    response_model=ResponseModel[AgentResponse],
    summary="Create a new agent",
    description="Create a new agent with the provided details",
    responses={
        200: {"description": "Successfully created agent"},
        401: {"description": "Invalid signature"},
        500: {"description": "Internal server error"},
    },
)
def create_agent(
    request: CreateAgentRequest,
    wallet_address: str = Depends(auth_handler.auth_wrapper),
    db: Session = Depends(get_db),
) -> ResponseModel[AgentResponse] | APIExceptionResponse:
    try:
        # check if the tool_configs are valid
        if error := check_tool_configs(request.tool_configs, db):
            return error

        agent = Agent(
            name=request.name,
            description=request.description,
            personality=request.personality,
            instruction=request.instruction,
            wallet_address=wallet_address,
            token_image=request.token_image,
            ticker=request.ticker,
            contract_address=request.contract_address,
            pair_address=request.pair_address,
            twitter=request.twitter,
            telegram=request.telegram,
            website=request.website,
            tool_configs=request.get_tool_configs_data(),
            type=request.type,
            status=AgentStatus.PAUSED,  # Set initial status to PAUSED
        )

        db.add(agent)
        db.commit()
        db.refresh(agent)

        # Generate YAML file for Twitter agents
        try:
            # Check if it's a Twitter agent (has Twitter tool)
            is_twitter_agent = any(
                "twitter" in tool_config.name.lower()
                for tool_config in agent.tool_configs_list
            )

            if is_twitter_agent:
                # Generate and save YAML file to current directory
                yaml_path = generate_twitter_agent_yaml(agent)
                print(f"Generated agent YAML file: {yaml_path}")
        except Exception as yaml_error:
            # Log the error but don't fail the agent creation
            print(f"Failed to generate YAML file: {yaml_error}")

        return ResponseModel(
            code=status.HTTP_200_OK,
            message="Agent created successfully",
            data=AgentResponse.model_validate(agent),
        )
    except Exception as error:
        db.rollback()
        return APIExceptionResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, error=error
        )


@router.get(
    "",
    response_model=ResponseModel[AgentListResponse],
    summary="List all agents",
    description="Get a paginated list of all agents",
    responses={
        200: {"description": "Successfully retrieved agents"},
        500: {"description": "Internal server error"},
    },
)
def list_agents(
    page: int = 0, limit: int = 10, db: Session = Depends(get_db)
) -> ResponseModel[dict] | APIExceptionResponse:
    try:
        total = db.query(Agent).count()
        agents = (
            db.query(Agent)
            .order_by(Agent.id.desc())
            .offset(page * limit)
            .limit(limit)
            .all()
        )
        return ResponseModel(
            code=status.HTTP_200_OK,
            data=AgentListResponse(
                agents=[PublicAgentResponse.model_validate(agent) for agent in agents],
                total=total,
            ),
            message=f"Retrieved {len(agents)} agents out of {total}",
        )
    except Exception as error:
        return APIExceptionResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, error=error
        )


@router.get(
    "/{agent_id}",
    response_model=ResponseModel[AgentResponse],
    summary="Get agent by ID",
    description="Get detailed information about a specific agent",
    responses={
        200: {"description": "Successfully retrieved agent"},
        404: {"description": "Agent not found"},
        500: {"description": "Internal server error"},
    },
)
def get_agent(
    agent_id: int,
    wallet_address: str | None = Depends(auth_handler.optional_auth_wrapper),
    db: Session = Depends(get_db),
) -> ResponseModel[AgentResponse] | APIExceptionResponse:
    try:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            return APIExceptionResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error=f"Agent with ID {agent_id} not found",
            )

        # return full agent info if authenticated and wallet addresses match
        if wallet_address and agent.wallet_address.lower() == wallet_address.lower():
            response_data = AgentResponse.model_validate(agent)
        else:
            # return public info for unauthenticated users or non-owners
            response_data = PublicAgentResponse.model_validate(agent)

        return ResponseModel(
            code=status.HTTP_200_OK,
            data=AgentResponse.model_validate(response_data),
            message="Agent retrieved successfully",
        )
    except Exception as error:
        return APIExceptionResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, error=error
        )


@router.put(
    "/{agent_id}",
    response_model=ResponseModel[AgentResponse],
    summary="Update agent",
    description="Update an existing agent's information",
    responses={
        200: {"description": "Successfully updated agent"},
        404: {"description": "Agent not found"},
        500: {"description": "Internal server error"},
    },
)
def update_agent(
    agent_id: int,
    request: CreateAgentRequest,
    wallet_address: str = Depends(auth_handler.auth_wrapper),
    db: Session = Depends(get_db),
) -> ResponseModel[AgentResponse] | APIExceptionResponse:
    try:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            return APIExceptionResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error=f"Agent with ID {agent_id} not found",
            )

        if agent.wallet_address.lower() != wallet_address.lower():
            return APIExceptionResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                error="Not authorized to update this agent",
            )

        # check if the tool_configs are valid
        if error := check_tool_configs(request.tool_configs, db):
            return error

        # convert request to dict and handle tool_configs separately
        update_data = request.model_dump(exclude_unset=True)
        if "tool_configs" in update_data:
            update_data["tool_configs"] = request.get_tool_configs_data()

        # update agent attributes
        for key, value in update_data.items():
            setattr(agent, key, value)

        # Set status to INACTIVE after update
        agent.status = AgentStatus.INACTIVE

        db.commit()
        db.refresh(agent)
        return ResponseModel(
            code=status.HTTP_200_OK,
            data=AgentResponse.model_validate(agent),
            message="Agent updated successfully",
        )
    except Exception as error:
        db.rollback()
        return APIExceptionResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, error=error
        )


@router.delete(
    "/{agent_id}",
    response_model=ResponseModel,
    summary="Delete agent",
    description="Delete an existing agent",
    responses={
        200: {"description": "Successfully deleted agent"},
        404: {"description": "Agent not found"},
        500: {"description": "Internal server error"},
    },
)
def delete_agent(
    agent_id: int,
    wallet_address: str = Depends(auth_handler.auth_wrapper),
    db: Session = Depends(get_db),
) -> ResponseModel:
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found",
        )

    if agent.wallet_address.lower() != wallet_address.lower():
        return APIExceptionResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            error="Not authorized to delete this agent",
        )

    try:
        # Instead of deleting, update status to DELETED
        agent.status = AgentStatus.DELETED
        db.commit()
        return ResponseModel(
            code=status.HTTP_200_OK,
            data=None,
            message="Agent marked as deleted successfully",
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        ) from e


@router.post(
    "/{agent_id}/run",
    response_model=ResponseModel[AgentResponse],
    summary="Run an agent",
    description="Start an agent by setting its status to active",
    responses={
        200: {"description": "Successfully started agent"},
        403: {"description": "Not authorized to run this agent"},
        404: {"description": "Agent not found"},
        500: {"description": "Internal server error"},
    },
)
def run_agent(
    agent_id: int,
    wallet_address: str = Depends(auth_handler.auth_wrapper),
    db: Session = Depends(get_db),
) -> ResponseModel[AgentResponse] | APIExceptionResponse:
    try:
        # get agent
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            return APIExceptionResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error=f"Agent with ID {agent_id} not found",
            )

        # check if the user is authorized to run this agent
        if agent.wallet_address.lower() != wallet_address.lower():
            return APIExceptionResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                error="Not authorized to run this agent",
            )

        # update the agent status to active
        agent.status = AgentStatus.INACTIVE  # Set to INACTIVE when running
        db.commit()
        db.refresh(agent)

        # TODO: start the agent

        return ResponseModel(
            code=status.HTTP_200_OK,
            data=AgentResponse.model_validate(agent),
            message="Agent started successfully",
        )
    except Exception as error:
        db.rollback()
        return APIExceptionResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error=error,
        )


@router.post(
    "/{agent_id}/stop",
    response_model=ResponseModel[AgentResponse],
    summary="Stop an agent",
    description="Stop an agent by setting its status to inactive",
    responses={
        200: {"description": "Successfully stopped agent"},
        403: {"description": "Not authorized to stop this agent"},
        404: {"description": "Agent not found"},
        500: {"description": "Internal server error"},
    },
)
def stop_agent(
    agent_id: int,
    wallet_address: str = Depends(auth_handler.auth_wrapper),
    db: Session = Depends(get_db),
) -> ResponseModel[AgentResponse] | APIExceptionResponse:
    try:
        # get agent
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            return APIExceptionResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error=f"Agent with ID {agent_id} not found",
            )

        # check if the user is authorized to stop this agent
        if agent.wallet_address.lower() != wallet_address.lower():
            return APIExceptionResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                error="Not authorized to stop this agent",
            )

        # update the agent status to inactive
        agent.status = AgentStatus.PAUSED  # Set to PAUSED when stopped
        db.commit()
        db.refresh(agent)

        # TODO: stop any running agent processes

        return ResponseModel(
            code=status.HTTP_200_OK,
            data=AgentResponse.model_validate(agent),
            message="Agent stopped successfully",
        )
    except Exception as error:
        db.rollback()
        return APIExceptionResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error=error,
        )
