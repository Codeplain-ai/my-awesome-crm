import logging
from typing import Any

logger = logging.getLogger(__name__)

def map_streak_contact(streak_record: dict[str, Any]) -> dict[str, Any]:
    """
    Implements :StreakContactMapping: as a pure function.
    Transforms a Streak ContactRecord into a host-standard Contact data dict.
    """
    # 1. external_id
    external_id = streak_record.get("key")

    # 2. full_name derivation
    full_name = ""
    raw_full_name = streak_record.get("fullName")
    if raw_full_name and raw_full_name.strip():
        full_name = raw_full_name.strip()
    else:
        given = (streak_record.get("givenName") or "").strip()
        family = (streak_record.get("familyName") or "").strip()
        joined = f"{given} {family}".strip()
        if joined:
            full_name = joined
        else:
            emails = streak_record.get("emailAddresses")
            if emails and isinstance(emails, list):
                for e in emails:
                    if e and e.strip():
                        full_name = e.strip()
                        break

    # 3. primary_email
    primary_email = None
    emails = streak_record.get("emailAddresses")
    if emails and isinstance(emails, list):
        for e in emails:
            if e and e.strip():
                primary_email = e.strip().lower()
                break

    # 4. job_title
    job_title = streak_record.get("title")
    if job_title == "":
        job_title = None

    # 5. custom_fields (provenance fields)
    custom_fields = {}
    for ts_key in ["creationTimestamp", "lastSavedTimestamp"]:
        if ts_key in streak_record and streak_record[ts_key] is not None:
            custom_fields[ts_key] = streak_record[ts_key]

    return {
        "provider_id": "streak",
        "external_id": external_id,
        "full_name": full_name,
        "primary_email": primary_email,
        "job_title": job_title,
        "company_name": None,
        "custom_fields": custom_fields,
    }