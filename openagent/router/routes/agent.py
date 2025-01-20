import binascii

from eth_utils import remove_0x_prefix, to_checksum_address
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import List, Optional, Union

from openagent.database.models.agent import Agent, AgentStatus
from openagent.database.models.model import Model
from openagent.database.models.tool import Tool
from openagent.router.routes.models.request import CreateAgentRequest
from openagent.router.routes.models.response import (
    AgentResponse,
    ResponseModel,
    AgentListResponse,
)
from openagent.router.error import APIExceptionResponse
from openagent.tools import ToolConfig
from openagent.database import get_db
from eth_account.messages import encode_defunct
from web3 import Web3
from typing import Annotated

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


async def verify_wallet_auth(
    wallet_address: Annotated[str, Header()],
    signature: Annotated[str, Header()],
    nonce: Annotated[str, Header()],
) -> str:
    """Dependency function to verify wallet authentication"""
    try:
        # Create the message
        message = f"Sign this message to authenticate with nonce: {nonce}"

        # Decode signature
        try:
            sig_bytes = bytes.fromhex(remove_0x_prefix(signature))
        except binascii.Error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature format",
            )

        # Adjust v value in signature
        if sig_bytes[64] >= 27:
            sig_bytes = sig_bytes[:64] + bytes([sig_bytes[64] - 27])

        # Recover public key
        w3 = Web3()
        try:
            recovered_address = w3.eth.account.recover_message(
                encode_defunct(text=message), signature=sig_bytes
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Failed to recover address: {str(e)}",
            )

        # Compare addresses
        if to_checksum_address(recovered_address) != to_checksum_address(
            wallet_address
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature"
            )

        return wallet_address

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
        )


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
    verified_address: str = Depends(verify_wallet_auth),
    db: Session = Depends(get_db),
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
            wallet_address=verified_address,
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
    agent_id: int,
    verified_address: str = Depends(verify_wallet_auth),
    db: Session = Depends(get_db),
) -> Union[ResponseModel[AgentResponse], APIExceptionResponse]:
    try:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            return APIExceptionResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error=f"Agent with ID {agent_id} not found",
            )

        if agent.wallet_address.lower() != verified_address.lower():
            return APIExceptionResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                error="Not authorized to query this agent",
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
    agent_id: int,
    request: CreateAgentRequest,
    verified_address: str = Depends(verify_wallet_auth),
    db: Session = Depends(get_db),
) -> Union[ResponseModel[AgentResponse], APIExceptionResponse]:
    try:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            return APIExceptionResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                error=f"Agent with ID {agent_id} not found",
            )

        if agent.wallet_address.lower() != verified_address.lower():
            return APIExceptionResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                error="Not authorized to update this agent",
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
def delete_agent(
    agent_id: int,
    request: CreateAgentRequest,
    verified_address: str = Depends(verify_wallet_auth),
    db: Session = Depends(get_db),
) -> ResponseModel:
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found",
        )

    if agent.wallet_address.lower() != verified_address.lower():
        return APIExceptionResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            error="Not authorized to delete this agent",
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
