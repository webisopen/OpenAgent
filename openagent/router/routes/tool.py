from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import Union

from openagent.db.models.tool import Tool
from openagent.router.routes.models.response import (
    ToolResponse,
    ToolListResponse,
    ResponseModel,
)
from openagent.router.error import APIExceptionResponse
from openagent.db import get_db

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get(
    "",
    response_model=ResponseModel[ToolListResponse],
    summary="List all tools",
    description="Get a paginated list of all tools",
    responses={
        200: {"description": "Successfully retrieved tools"},
        500: {"description": "Internal server error"},
    },
)
def list_tools(
    page: int = 0, limit: int = 10, db: Session = Depends(get_db)
) -> Union[ResponseModel[ToolListResponse], APIExceptionResponse]:
    try:
        total = db.query(Tool).count()
        tools = db.query(Tool).offset(page * limit).limit(limit).all()
        return ResponseModel(
            code=status.HTTP_200_OK,
            data=ToolListResponse(
                tools=[ToolResponse.model_validate(tool) for tool in tools], total=total
            ),
            message=f"Retrieved {len(tools)} tools out of {total}",
        )
    except Exception as error:
        return APIExceptionResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, error=error
        )
