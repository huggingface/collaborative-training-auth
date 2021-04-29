from fastapi import APIRouter, Depends

from app.api.routes.experiments import router as experiments_router

# from app.api.routes.users import router as users_router
from app.services.authentication import authenticate


router = APIRouter()

router.include_router(
    experiments_router, prefix="/experiments", tags=["experiments"], dependencies=[Depends(authenticate)]
)
# router.include_router(
#     users_router,
#     prefix="/users",
#     tags=["users"],
#     dependencies=[Depends(authenticate)],
# )
