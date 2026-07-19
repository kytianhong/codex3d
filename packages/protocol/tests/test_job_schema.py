from codex3d_protocol import ErrorCode, Job, JobStatus, JobType


def test_job_status_updates() -> None:
    job = Job(type=JobType.RENDER_PREVIEW, scene_id="scene_demo")

    assert job.status is JobStatus.QUEUED
    job.mark_running()
    assert job.status is JobStatus.RUNNING
    assert job.started_at is not None

    job.mark_succeeded({"preview_path": "renders/preview.png"})
    assert job.status is JobStatus.SUCCEEDED
    assert job.result["preview_path"] == "renders/preview.png"
    assert job.finished_at is not None


def test_job_failure_records_protocol_error() -> None:
    job = Job(type=JobType.VALIDATION)
    job.mark_failed(
        "Render validation failed.",
        code=ErrorCode.VALIDATION_FAILED,
        retryable=True,
    )

    assert job.status is JobStatus.FAILED
    assert job.error is not None
    assert job.error.code is ErrorCode.VALIDATION_FAILED
    assert job.error.retryable is True

