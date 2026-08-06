from app.models.request_models import BatchRequest
from app.models.response_models import BatchResponse
from app.agent.tools import generate_outreach


def process_batch(batch: BatchRequest) -> BatchResponse:
    """
    Process multiple outreach requests.
    """

    results = []

    for request in batch.requests:
        try:
            message = generate_outreach.invoke(
                {
                    "profile_name": request.profile_name,
                    "headline": request.headline,
                    "about": request.about,
                    "recent_activity": request.recent_activity,
                    "product_description": request.product_description,
                    "tone": request.tone,
                }
            )

            results.append(message)

        except Exception as e:
            print(f"Failed for {request.profile_name}: {e}")

    return BatchResponse(results=results)