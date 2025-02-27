from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from openagent.database import get_db
from openagent.database.models.model import Model
from openagent.router.error import APIExceptionResponse
from openagent.router.routes.models.response import (
    ModelListResponse,
    ModelResponse,
    ResponseModel,
)

router = APIRouter(prefix="/models", tags=["models"])


@router.get(
    "",
    response_model=ResponseModel[ModelListResponse],
    summary="List all models",
    description="Get a paginated list of all models",
    responses={
        200: {"description": "Successfully retrieved models"},
        500: {"description": "Internal server error"},
    },
)
def list_models(
    page: int = 0,
    limit: int = 10,
    ids: list[int] | None = Query(default=None),
    db: Session = Depends(get_db),
) -> ResponseModel[ModelListResponse] | APIExceptionResponse:
    try:
        query = db.query(Model)

        # Add filter for model ids if provided
        if ids:
            query = query.filter(Model.id.in_(ids))

        total = query.count()
        models = query.offset(page * limit).limit(limit).all()

        return ResponseModel(
            code=status.HTTP_200_OK,
            data=ModelListResponse(
                models=[ModelResponse.model_validate(model) for model in models],
                total=total,
            ),
            message=f"Retrieved {len(models)} models out of {total}",
        )
    except Exception as error:
        return APIExceptionResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, error=error
        )
