from fastapi import APIRouter

from . import actions, agent, approvals, auth, citations, contact_messages, daily_briefings, documents, evidence, external_delivery, handoff, hiring, proto, workers

router = APIRouter()
router.include_router(proto.router)
router.include_router(auth.router)
router.include_router(agent.router)
router.include_router(daily_briefings.router)
router.include_router(approvals.router)
router.include_router(actions.router)
router.include_router(citations.router)
router.include_router(contact_messages.router)
router.include_router(documents.router)
router.include_router(evidence.router)
router.include_router(external_delivery.router)
router.include_router(handoff.router)
router.include_router(hiring.router)
router.include_router(workers.router)
