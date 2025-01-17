from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Union

from openagent.db.models.agent import Agent, AgentStatus
from openagent.db.models.model import Model
from openagent.db.models.tool import Tool
from openagent.router.routes.models.request import CreateAgentRequest
from openagent.router.routes.models.response import (
    AgentResponse,
    ResponseModel,
    AgentListResponse,
)
from openagent.router.error import APIExceptionResponse
from openagent.tools import ToolConfig
from openagent.db import get_db

router = APIRouter(prefix="/agents", tags=["agents"])


def check_tool_configs(
    tool_configs: List[ToolConfig], db: Session
) -> Optional[APIExceptionResponse]:
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
        500: {"description": "Internal server error"},
    },
)
def create_agent(
    request: CreateAgentRequest, db: Session = Depends(get_db)
) -> Union[ResponseModel[AgentResponse], APIExceptionResponse]:
    try:
        # check if the tool_configs are valid
        if error := check_tool_configs(request.tool_configs, db):
            return error

        agent = Agent(
            name=request.name,
            description=request.description,
            personality=request.personality,
            instruction=request.instruction,
            wallet_address=request.wallet_address,
            token_image=request.token_image,
            ticker=request.ticker,
            contract_address=request.contract_address,
            pair_address=request.pair_address,
            twitter=request.twitter,
            telegram=request.telegram,
            website=request.website,
            tool_configs=request.tool_configs,
            status=AgentStatus.INACTIVE,  # default status
        )

        db.add(agent)
        db.commit()
        db.refresh(agent)

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
) -> Union[ResponseModel[dict], APIExceptionResponse]:
    try:
        total = db.query(Agent).count()
        agents = db.query(Agent).offset(page * limit).limit(limit).all()
        return ResponseModel(
            code=status.HTTP_200_OK,
            data=AgentListResponse(
                agents=[AgentResponse.model_validate(agent) for agent in agents],
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
    agent_id: int, db: Session = Depends(get_db)
) -> Union[ResponseModel[AgentResponse], APIExceptionResponse]:
    try:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            return APIExceptionResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error=f"Agent with ID {agent_id} not found",
            )
        return ResponseModel(
            code=status.HTTP_200_OK,
            data=AgentResponse.model_validate(agent),
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
    agent_id: int, request: CreateAgentRequest, db: Session = Depends(get_db)
) -> Union[ResponseModel[AgentResponse], APIExceptionResponse]:
    try:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            return APIExceptionResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error=f"Agent with ID {agent_id} not found",
            )

        # check if the tool_configs are valid
        if error := check_tool_configs(request.tool_configs, db):
            return error

        for key, value in request.model_dump(exclude_unset=True).items():
            setattr(agent, key, value)

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
def delete_agent(agent_id: int, db: Session = Depends(get_db)) -> ResponseModel:
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found",
        )

    try:
        db.delete(agent)
        db.commit()
        return ResponseModel(
            code=status.HTTP_200_OK, data=None, message="Agent deleted successfully"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
