from fastapi import APIRouter

from app.routers.audit import router as audit_router
from app.routers.audit_log import router as audit_log_router


router = APIRouter()

router.include_router(audit_router, prefix="/audit", tags=["audit"])
router.include_router(audit_log_router, prefix="/log", tags=["log"])
