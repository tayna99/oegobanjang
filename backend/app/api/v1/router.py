from fastapi import APIRouter
from app.api.v1 import agent, handoff

router = APIRouter()
router.include_router(agent.router)
router.include_router(handoff.router)
