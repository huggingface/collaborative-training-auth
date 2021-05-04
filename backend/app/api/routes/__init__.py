from fastapi import APIRouter, Depends

from app.api.routes.experiments import router as experiments_router
from app.services.authentication import authenticate


router = APIRouter()

router.include_router(
    experiments_router, prefix="/experiments", tags=["experiments"], dependencies=[Depends(authenticate)]
)
