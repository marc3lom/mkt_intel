"""
Federal Reserve website scraper for FOMC documents.

This module provides functions for fetching the latest FOMC documents
from the Federal Reserve website.
"""

import logging
import re
from pathlib import Path

import requests

from reports import _paths

logger = logging.getLogger(__name__)

# Federal Reserve FOMC calendar URL
FED_CALENDAR_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"

# Base URL for FOMC documents
FED_BASE_URL = "https://www.federalreserve.gov"

# Headers to mimic browser request
FED_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Document type URL patterns
DOCUMENT_TYPES = {
    "statement": "monetary",
    "minutes": "fomcminutes",
    "projections": "fomcprojtabl",
    "presser": "presconf",
}


def fetch_calendar_page() -> str:
    """Fetch the FOMC calendar page HTML.

    Returns:
        HTML content of the calendar page.

    Raises:
        RuntimeError: If fetch fails.
    """
    logger.info(f"Fetching FOMC calendar from {FED_CALENDAR_URL}")

    try:
        response = requests.get(
            FED_CALENDAR_URL,
            headers=FED_REQUEST_HEADERS,
            timeout=30,
        )
        response.raise_for_status()
        return response.text

    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch FOMC calendar: {e}")


def get_available_documents() -> dict[str, list[dict[str, str]]]:
    """Get list of available FOMC documents from the calendar page.

    Returns:
        Dictionary mapping document types to lists of document info:
        {'statement': [{'date': '20251210', 'url': '...'}], ...}

    Raises:
        RuntimeError: If parsing fails.
    """
    html = fetch_calendar_page()

    documents: dict[str, list[dict[str, str]]] = {
        "statement": [],
        "minutes": [],
        "projections": [],
        "presser": [],
    }

    # Find all PDF links
    pdf_pattern = r'href="(/monetarypolicy/files/[^"]+\.pdf)"'
    matches = re.findall(pdf_pattern, html)

    for url_path in matches:
        url = FED_BASE_URL + url_path
        filename = url_path.split("/")[-1]

        # Determine document type and extract date
        for doc_type, pattern in DOCUMENT_TYPES.items():
            if pattern in filename.lower():
                # Extract date (YYYYMMDD)
                date_match = re.search(r"(\d{8})", filename)
                if date_match:
                    documents[doc_type].append(
                        {
                            "date": date_match.group(1),
                            "url": url,
                            "filename": filename,
                        }
                    )
                break

    # Sort each list by date (descending)
    for doc_type in documents:
        documents[doc_type].sort(key=lambda x: x["date"], reverse=True)

    return documents


def download_document(
    url: str,
    output_path: Path | None = None,
    filename: str | None = None,
) -> Path:
    """Download a document from the Federal Reserve website.

    Args:
        url: Full URL to the document.
        output_path: Directory to save the file. Defaults to input/committee_meeting_docs.
        filename: Override filename. Defaults to original filename from URL.

    Returns:
        Path to the downloaded file.

    Raises:
        RuntimeError: If download fails.
    """
    if output_path is None:
        output_path = _paths.FED_DOCS / "committee_meeting_docs"

    output_path.mkdir(parents=True, exist_ok=True)

    if filename is None:
        filename = url.split("/")[-1]

    file_path = output_path / filename

    logger.info(f"Downloading {filename} from {url}")

    try:
        response = requests.get(
            url,
            headers=FED_REQUEST_HEADERS,
            timeout=60,
        )
        response.raise_for_status()

        with open(file_path, "wb") as f:
            f.write(response.content)

        logger.info(f"Saved to {file_path}")
        return file_path

    except requests.RequestException as e:
        raise RuntimeError(f"Failed to download document: {e}")


def fetch_latest_documents(
    doc_types: list[str] | None = None,
    force: bool = False,
) -> dict[str, Path | None]:
    """Fetch the latest FOMC documents that aren't already downloaded.

    Args:
        doc_types: List of document types to fetch.
                  Options: 'statement', 'minutes', 'projections', 'presser'.
                  Defaults to all types.
        force: If True, download even if file already exists.

    Returns:
        Dictionary mapping document types to downloaded file paths.
    """
    if doc_types is None:
        doc_types = list(DOCUMENT_TYPES.keys())

    available = get_available_documents()
    local_path = _paths.FED_DOCS / "committee_meeting_docs"

    results: dict[str, Path | None] = {}

    for doc_type in doc_types:
        if doc_type not in available:
            results[doc_type] = None
            continue

        docs = available[doc_type]
        if not docs:
            results[doc_type] = None
            continue

        # Get the latest document
        latest = docs[0]
        filename = latest["filename"]
        file_path = local_path / filename

        if file_path.exists() and not force:
            logger.info(f"Already have latest {doc_type}: {filename}")
            results[doc_type] = file_path
        else:
            try:
                results[doc_type] = download_document(latest["url"])
            except RuntimeError as e:
                logger.error(f"Failed to download {doc_type}: {e}")
                results[doc_type] = None

    return results


def check_for_updates() -> dict[str, bool]:
    """Check if there are new documents available since last download.

    Returns:
        Dictionary mapping document types to whether new docs are available.
    """
    available = get_available_documents()
    local_path = _paths.FED_DOCS / "committee_meeting_docs"

    updates: dict[str, bool] = {}

    for doc_type, docs in available.items():
        if not docs:
            updates[doc_type] = False
            continue

        latest = docs[0]
        file_path = local_path / latest["filename"]
        updates[doc_type] = not file_path.exists()

    return updates


def sync_all_documents(since_date: str = "20200101") -> dict[str, int]:
    """Download all missing documents since a given date.

    Args:
        since_date: Only download documents from this date onwards (YYYYMMDD).

    Returns:
        Dictionary with count of documents downloaded per type.
    """
    available = get_available_documents()
    local_path = _paths.FED_DOCS / "committee_meeting_docs"

    counts: dict[str, int] = {}

    for doc_type, docs in available.items():
        count = 0
        for doc in docs:
            if doc["date"] < since_date:
                continue

            file_path = local_path / doc["filename"]
            if not file_path.exists():
                try:
                    download_document(doc["url"])
                    count += 1
                except RuntimeError as e:
                    logger.error(f"Failed to download {doc['filename']}: {e}")

        counts[doc_type] = count
        if count > 0:
            logger.info(f"Downloaded {count} new {doc_type} document(s)")

    return counts
