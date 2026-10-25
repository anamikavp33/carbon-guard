from typing import Optional
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from auth_utils import get_current_user
from config import settings
from models.common import ActivityType, Page
from models.submission import SubmissionDetail, SubmissionStatusResponse, SubmissionSummary
from repositories import submissions
from routes.views import to_detail, to_summary
from services import pipeline
from services.image_utils import ImageError

router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.post("", response_model=SubmissionStatusResponse, status_code=201)
def create_submission(
    background: BackgroundTasks,
    activity_type: ActivityType = Form(...),
    latitude: float = Form(..., ge=-90, le=90),
    longitude: float = Form(..., ge=-180, le=180),
    scale_value: float = Form(..., gt=0, description="Trees planted, kW of solar panels, or m³ of water storage"),
    gps_accuracy_m: Optional[float] = Form(None, ge=0),
    gps_is_mocked: Optional[bool] = Form(None, description="Android: location came from a mock-location app"),
    description: Optional[str] = Form(None, max_length=500),
    image: UploadFile = File(..., description="JPEG, PNG or WEBP photo"),
    current_user: dict = Depends(get_current_user),
):
    """Multipart form upload. The checks run in the background: poll GET /submissions/{id}/status."""
    # Read at most the size limit + 1 byte, so a huge upload is rejected without filling memory.
    raw = image.file.read(settings.MAX_IMAGE_MB * 1024 * 1024 + 1)
    try:
        record = pipeline.create_submission(current_user, activity_type, latitude, longitude, gps_accuracy_m, gps_is_mocked,
                                            (description or "").strip() or None, scale_value, raw)
    except ImageError as e:
        raise HTTPException(status_code=400, detail=str(e))
    background.add_task(pipeline.process_submission, record["id"])
    return SubmissionStatusResponse(id=record["id"], status=record["status"], updated_at=record["updated_at"])


@router.get("/me", response_model=Page[SubmissionSummary])
def my_submissions(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
                   current_user: dict = Depends(get_current_user)):
    rows, total = submissions.list_for_user(current_user["id"], skip, limit)
    return Page(items=[to_summary(r) for r in rows], total=total, skip=skip, limit=limit)


def _own(submission_id: str, user: dict) -> dict:
    record = submissions.get(submission_id)
    # 404 (not 403) for other people's submissions, so ids cannot be probed.
    if not record or (record["user_id"] != user["id"] and user["role"] != "admin"):
        raise HTTPException(status_code=404, detail="Submission not found")
    return record


@router.get("/{submission_id}", response_model=SubmissionDetail)
def get_submission(submission_id: str, current_user: dict = Depends(get_current_user)):
    return to_detail(_own(submission_id, current_user))


@router.get("/{submission_id}/status", response_model=SubmissionStatusResponse)
def get_status(submission_id: str, current_user: dict = Depends(get_current_user)):
    r = _own(submission_id, current_user)
    return SubmissionStatusResponse(id=r["id"], status=r["status"], updated_at=r["updated_at"])
