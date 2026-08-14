"""
FastAPI routes for OutreachIQ V2.

Endpoints
---------

POST /generate
  JSON body with profile_url or profile_text + product_description + tone.
  Returns OutreachMessage.

POST /generate-batch
  JSON body with a list of OutreachRequest objects.
  Returns BatchResponse.

POST /generate-from-pdf
  multipart/form-data with profile_pdf (UploadFile), product_description, tone.
  Returns OutreachMessage.
  The uploaded PDF is written to a secure temporary file, processed, then
  deleted — it is never persisted to disk beyond the request lifetime.

API design decision
-------------------
PDF upload uses a separate endpoint (/generate-from-pdf) with
multipart/form-data.  Mixing JSON and multipart in a single endpoint
would require Form() fields for all parameters and would break the clean
JSON contract of /generate.  Two focused endpoints are cleaner.
"""

from __future__ import annotations

import logging
import os
import tempfile
from fastapi import APIRouter, Form, HTTPException, UploadFile, File

from app.agent.agent_core import generate_outreach
from app.config import settings
from app.models.request_models import BatchRequest, OutreachRequest, Tone
from app.models.response_models import BatchResponse, OutreachMessage, BatchPDFResult, BatchPDFItemResult
from app.scraper.acquisition import ProfileInput
from app.scraper.exceptions import ProfileAcquisitionError
from app.scraper.profile_scraper import ProfileScraper
from app.scraper.adapters import FixtureProfileAdapter
from app.scraper.cache import ProfileCache
from app.scraper.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="",
    tags=["Outreach"],
)

# Default scraper instance for the PDF endpoint
# (reuses the same fixture-adapter scraper — acquire_from_input bypasses it)
_scraper = ProfileScraper(
    acquisition=FixtureProfileAdapter(),
    rate_limiter=RateLimiter(min_delay_seconds=0.0, max_delay_seconds=0.0),
    cache=ProfileCache(ttl_seconds=300),
)


@router.post("/generate", response_model=OutreachMessage)
async def generate(request: OutreachRequest):
    """
    Generate a personalized outreach message.

    Accepts either:
    - profile_url: for fixture-based profile lookup
    - profile_text: for user-pasted profile text

    At least one must be provided.
    """
    try:
        return generate_outreach(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-batch", response_model=BatchResponse)
async def generate_batch(request: BatchRequest):
    """
    Generate outreach messages for a batch of requests.

    Each request in the batch must supply either profile_url or profile_text.
    Failures for individual items are logged and skipped; the batch does not
    fail completely.
    """
    results: list[OutreachMessage] = []

    for outreach_request in request.requests:
        try:
            result = generate_outreach(outreach_request)
            results.append(result)
        except Exception as e:
            source = outreach_request.profile_url or "(text input)"
            logger.warning(
                "Failed to process request for %s: %s", source, e
            )
            continue

    return BatchResponse(results=results)


@router.post("/generate-from-pdf", response_model=OutreachMessage)
async def generate_from_pdf(
    profile_pdf: UploadFile,
    product_description: str = Form(..., min_length=20, max_length=1000),
    tone: str = Form(default="casual"),
):
    """
    Generate a personalized outreach message from a PDF profile upload.

    The PDF must be a text-based profile document (e.g., a LinkedIn
    "Save to PDF" export or a manually created profile PDF).

    The uploaded file is:
    - Written to a secure temporary file
    - Processed (text extracted, parsed, normalized)
    - Deleted immediately after processing

    The PDF is never stored permanently and its contents are not logged.

    Raises:
        422: Invalid request (missing fields, bad tone value)
        400: PDF validation or extraction failure
        500: Unexpected pipeline failure
    """
    # Validate tone
    try:
        tone_enum = Tone(tone.lower())
    except ValueError:
        valid = [t.value for t in Tone]
        raise HTTPException(
            status_code=422,
            detail=f"Invalid tone {tone!r}. Valid values: {valid}",
        )

    # Validate file extension
    filename = profile_pdf.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=422,
            detail="Uploaded file must have a .pdf extension.",
        )

    # Enforce file size limit
    max_size = settings.PDF_MAX_FILE_SIZE_MB * 1024 * 1024
    content = await profile_pdf.read()
    if len(content) == 0:
        raise HTTPException(status_code=422, detail="Uploaded PDF is empty.")
    if len(content) > max_size:
        raise HTTPException(
            status_code=422,
            detail=(
                f"PDF file is too large ({len(content) / 1024 / 1024:.1f} MB). "
                f"Maximum allowed size is {settings.PDF_MAX_FILE_SIZE_MB} MB."
            ),
        )

    # Write to a temporary file, process, then delete
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        logger.info(
            "PDF upload received: %d bytes, processing via PDFProfileAdapter",
            len(content),
        )

        profile_input = ProfileInput(
            source_type="pdf",
            pdf_path=tmp_path,
        )

        profile = _scraper.acquire_from_input(profile_input)

        # Build an OutreachRequest from the extracted profile
        # Use the extracted name as context; the agent will use the ScrapedProfile
        request = OutreachRequest(
            profile_text=(
                f"Name: {profile.name}\n"
                f"Headline: {profile.headline}\n"
                f"About:\n{profile.about}\n"
                f"Recent Activity:\n"
                + "\n".join(f"- {a}" for a in profile.recent_activity)
            ),
            product_description=product_description,
            tone=tone_enum,
        )

        return generate_outreach(request, pre_scraped_profile=profile)

    except ProfileAcquisitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("PDF pipeline error: %s", type(exc).__name__, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        # Always delete the temporary file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
                logger.debug("Deleted temporary PDF: %s", tmp_path)
            except OSError as exc:
                logger.warning("Could not delete temporary PDF: %s", exc)


@router.post("/generate-batch-from-pdf", response_model=BatchPDFResult)
async def generate_batch_from_pdf(
    files: list[UploadFile] = File(...),
    product_description: str = Form(..., min_length=20, max_length=1000),
    tone: str = Form(default="casual"),
):
    """
    Generate outreach messages for a batch of PDF profile uploads.
    """
    if len(files) > settings.PROFILE_MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=422,
            detail=f"Exceeded maximum batch size of {settings.PROFILE_MAX_BATCH_SIZE}.",
        )
    
    try:
        tone_enum = Tone(tone.lower())
    except ValueError:
        valid = [t.value for t in Tone]
        raise HTTPException(
            status_code=422,
            detail=f"Invalid tone {tone!r}. Valid values: {valid}",
        )

    results = []
    successful = 0
    failed = 0

    max_size = settings.PDF_MAX_FILE_SIZE_MB * 1024 * 1024

    for file in files:
        filename = file.filename or "unknown.pdf"
        
        if not filename.lower().endswith(".pdf"):
            results.append(BatchPDFItemResult(
                filename=filename,
                status="error",
                error="Uploaded file must have a .pdf extension."
            ))
            failed += 1
            continue

        content = await file.read()
        if len(content) == 0:
            results.append(BatchPDFItemResult(
                filename=filename,
                status="error",
                error="Uploaded PDF is empty."
            ))
            failed += 1
            continue
            
        if len(content) > max_size:
            results.append(BatchPDFItemResult(
                filename=filename,
                status="error",
                error=f"PDF file is too large ({len(content) / 1024 / 1024:.1f} MB)."
            ))
            failed += 1
            continue

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            logger.info("[BatchPDF] %s -> acquisition started", filename)
            profile_input = ProfileInput(source_type="pdf", pdf_path=tmp_path)
            profile = _scraper.acquire_from_input(profile_input)
            
            logger.info("[BatchPDF] %s -> profile=%s", filename, profile.name)

            request = OutreachRequest(
                profile_text=(
                    f"Name: {profile.name}\n"
                    f"Headline: {profile.headline}\n"
                    f"About:\n{profile.about}\n"
                    f"Recent Activity:\n"
                    + "\n".join(f"- {a}" for a in profile.recent_activity)
                ),
                product_description=product_description,
                tone=tone_enum,
            )

            result = generate_outreach(request, pre_scraped_profile=profile)
            logger.info("[BatchPDF] %s -> generation succeeded", filename)
            
            results.append(BatchPDFItemResult(
                filename=filename,
                status="success",
                result=result
            ))
            successful += 1

        except ProfileAcquisitionError as exc:
            logger.warning("[BatchPDF] %s -> acquisition failed: %s", filename, exc)
            results.append(BatchPDFItemResult(
                filename=filename,
                status="error",
                error=str(exc)
            ))
            failed += 1
        except Exception as exc:
            logger.error("[BatchPDF] %s -> unexpected error: %s", filename, exc)
            results.append(BatchPDFItemResult(
                filename=filename,
                status="error",
                error=str(exc)
            ))
            failed += 1
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    return BatchPDFResult(
        total=len(files),
        successful=successful,
        failed=failed,
        results=results
    )


from fastapi.responses import StreamingResponse
import io

@router.post("/export-csv")
async def export_csv(messages: list[OutreachMessage]):
    """
    Export a list of OutreachMessages to CSV format.
    """
    from app.export.csv_exporter import export_to_csv_string
    csv_str = export_to_csv_string(messages)
    return StreamingResponse(
        io.StringIO(csv_str),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=outreach_messages.csv"}
    )