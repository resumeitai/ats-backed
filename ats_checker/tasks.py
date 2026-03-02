from celery import shared_task


@shared_task
def analyze_resume_task(ats_score_id):
    """Analyze a resume against a job description asynchronously."""
    from .services import analyze_resume
    return analyze_resume(ats_score_id)
