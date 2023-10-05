import json
import traceback
from adapters import register_adapter
from celery import states
from celery.result import AsyncResult
from fastapi import Response
from pydantic import BaseModel

MESSAGES = {
    states.SUCCESS: "Task complete!",
    states.FAILURE: "Task failed!",
    states.PENDING: "Task pending.",
    states.STARTED: "Task started.",
}


class V1CeleryTaskInput(BaseModel):
    placeholder: str


class V1CeleryTaskResponse(BaseModel):
    placeholder: str


@register_adapter(
    name="v1_celery_task",
    input_class=V1CeleryTaskInput,
    result_class=V1CeleryTaskResponse
)
class V1CeleryTaskAdapter:
    """V1 Celery Task Adapter"""
    prefix = "legacy/celery/task"
    methods = ["GET"]

    async def __call__(self, task_id: str) -> Response:
        """
        Get the status and result of a single celery task by task_id.
        """
        # Create AsyncResult instance using task_id
        # Celery always assumes that the task exists
        # If the task does not exist, it's state will be "PENDING"
        result = AsyncResult(task_id)

        state = result.state
        resp = {
            "task_id": task_id,
            "state": state,
            "complete": state in [states.SUCCESS],
            "failed": state in [states.FAILURE],
            "percent": 1 if state in [states.SUCCESS] else 0,
            "message": MESSAGES.get(state, ""),
        }
        status_code = 200
        try:
            if state == states.SUCCESS:
                output = result.result  # This is the return value
                if "__root__" in output:
                    output = output["__root__"]  # Reverse parse for list return
                resp["output"] = output

                # Additional error handling to override state based on output
                if not output["status_code"] == 200:
                    resp["state"] = "FAILURE"
                    resp["failed"] = True
                    resp["message"] = "Task failed!"
            elif state == states.FAILURE:
                resp["output"] = str(result.result)  # This is the exception
                status_code = 500
            elif state == "PROGRESS":
                # Custom state generated by impurity predictor
                resp["percent"] = result.result.get("percent")
                resp["message"] = result.result.get("message")
        except Exception as e:
            resp["error"] = f"Unable to retrieve celery task result, traceback: " \
                            f"{traceback.format_exc()}"
            status_code = 500

        return Response(
            content=json.dumps(resp),
            status_code=status_code,
            media_type="application/json"
        )
