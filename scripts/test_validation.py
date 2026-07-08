from pydantic import ValidationError

from app.models.request_models import OutreachRequest


try:
    OutreachRequest(
        profile_url="not-a-url",
        product_description="short",
        tone="random",
    )
except ValidationError as e:
    print(e)