from __future__ import annotations

from fastapi import APIRouter

from backend.routes.apis import router as apis_router
from backend.routes.automations import router as automations_router
from backend.routes.connectors import router as connectors_router
from backend.routes.docs import router as docs_router
from backend.routes.log_tables import router as log_tables_router
from backend.routes.runtime import router as runtime_router
from backend.routes.scripts import router as scripts_router
from backend.routes.settings import router as settings_router
from backend.routes.tools import router as tools_router
from backend.routes.workers import router as workers_router

router = APIRouter()

router.include_router(runtime_router)
router.include_router(automations_router)
router.include_router(docs_router)
router.include_router(log_tables_router)
router.include_router(scripts_router)
router.include_router(settings_router)
router.include_router(workers_router)
router.include_router(connectors_router)
router.include_router(apis_router)
router.include_router(tools_router)
