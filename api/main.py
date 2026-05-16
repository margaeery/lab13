from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from .dependencies import create_orchestrator, get_task_service
from .models import AppointmentRequest, TaskResponse
from .services import TaskService


@asynccontextmanager
async def lifespan(app: FastAPI):
    if getattr(app.state, "skip_orchestrator_lifespan", False):
        yield
        return

    orchestrator = create_orchestrator()
    await orchestrator.connect()
    app.state.orchestrator = orchestrator
    try:
        yield
    finally:
        await orchestrator.disconnect()


app = FastAPI(title="Appointment API", version="1.0.0", lifespan=lifespan)


@app.get("/health", status_code=status.HTTP_200_OK)
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/tasks/appointment",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
)
async def create_appointment(
    request: AppointmentRequest,
    task_service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    try:
        result = await task_service.submit_appointment(request)
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

    if result.error == "timeout":
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="task execution timed out",
        )

    response = TaskResponse(
        task_id=result.task_id,
        success=result.success,
        output=result.output,
        agent_id=result.agent_id,
        error=result.error,
    )

    if not result.success:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=response.model_dump(mode="json"),
        )

    return response