import login
import re
from typing import Dict, Any, List
from urllib.parse import urlparse, parse_qs
from lxml import html as lxml_html

def _parse_renew_html(html_text: str) -> Dict[str, Any]:
    """Parse HTML returned after a renew attempt.

    Handles two main cases:
    - User page with renewed flag in the renew column
    - Login page (renewal requires login)
    """
    result: Dict[str, Any] = {"status": "unknown"}
    if not html_text:
        return result

    doc = lxml_html.fromstring(html_text)

    # Case: login/auth page (renew requires login)
    if doc.xpath("//*[@id='opac-login-page']"):
        item_val = doc.xpath("//input[@type='hidden' and @name='item']/@value")
        borrower_val = doc.xpath("//input[@type='hidden' and @name='borrowernumber']/@value")
        item_id = int(item_val[0]) if item_val and item_val[0].isdigit() else (item_val[0] if item_val else None)
        borrower_id = int(borrower_val[0]) if borrower_val and borrower_val[0].isdigit() else (borrower_val[0] if borrower_val else None)
        return {
            "status": "error",
            "error": "Renewal failed: not logged in",
            "error_code": "renewal_requires_login",
            "renewal": {
                "status": "failed",
                "reason": "not_logged_in",
                "item_id": item_id,
                "borrower_id": borrower_id,
            },
        }

    # Case: user page - detect renewed
    if doc.xpath("//*[@id='opac-user']"):
        renewed_ids: List[int] = []
        rows = doc.xpath("//table[@id='checkoutst']/tbody/tr")
        for tr in rows:
            renew_td = tr.xpath(".//td[contains(@class,'renew')]")
            if not renew_td:
                continue
            td_text = renew_td[0].text_content()
            renewed = bool(re.search(r"\bRenewed!\b", td_text, re.I))
            if renewed:
                # Prefer checkbox value for item id, else pick from renew link
                checkbox_val = tr.xpath(".//input[@name='item']/@value")
                item_id = None
                if checkbox_val:
                    item_id = int(checkbox_val[0]) if checkbox_val[0].isdigit() else checkbox_val[0]
                else:
                    link = tr.xpath(".//a[contains(@href,'opac-renew.pl')]/@href")
                    if link:
                        m = re.search(r"item=(\d+)", link[0])
                        if m:
                            item_id = int(m.group(1))
                if item_id is not None:
                    try:
                        renewed_ids.append(int(item_id))
                    except Exception:
                        pass
        if renewed_ids:
            return {"status": "success", "renewal": {"status": "success", "item_ids": renewed_ids}}
        # If no explicit renewed labels, still return user page status
        return {"status": "success", "renewal": {"status": "unknown"}}

    return result


def _process_renew_response(response) -> Dict[str, Any]:
    """Normalize Koha renewal HTTP response to a structured result.

    - If a redirect with Location to opac-user.pl?renewed=<id>, treat as success.
    - If HTML login page for opac-renew, treat as failed (not logged in).
    - Else parse user page and detect renewed items via the "Renewed!" label.
    """
    # Redirect success case
    if response is not None and response.is_redirect or (
        getattr(response, "status_code", None) in (301, 302, 303, 307, 308)
    ):
        loc = response.headers.get("Location") or response.headers.get("location")
        if loc:
            parsed = urlparse(loc)
            qs = parse_qs(parsed.query)
            renewed = qs.get("renewed", [])
            if renewed:
                try:
                    item_id = int(renewed[0])
                except Exception:
                    item_id = renewed[0]
                return {"status": "success", "renewal": {"status": "success", "item_ids": [item_id]}, "next": loc}
            # If redirect but no renewed param, fall through and attempt to parse body

    # Non-redirect or no renewed param: parse HTML
    html_text = getattr(response, "text", "")
    return _parse_renew_html(html_text)


def renew_item(scraper, item_id: int, borrower_id: int) -> Dict[str, Any]:
    """
    Perform a direct renewal using an existing cloudscraper session.
    Returns a structured dict describing the renewal outcome.
    """
    url = "https://library.bracu.ac.bd/cgi-bin/koha/opac-renew.pl"
    params = {
        "from": "opac_user",
        "item": item_id,
        "borrowernumber": borrower_id,
    }

    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept-language": "en-US,en;q=0.9",
        "referer": "https://library.bracu.ac.bd/cgi-bin/koha/opac-user.pl",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    }

    # Do not auto-follow redirects so we can inspect the Location header
    response = scraper.get(url, params=params, headers=headers, allow_redirects=False)
    return _process_renew_response(response)


def get_book_info(userid: str, password: str):

    scraper, login_output = login(userid, password)

    if login_output["status"] == "success":
        items = [{"item_id": checkout["item_id"],"due_date": checkout["due_date"]} for checkout in login_output["checkouts"]]
        return {"status": "success", "items": items}
    elif login_output["status"] == "error":
        error_message = login_output.get("error", "Unknown error during login")
        return {"status": "error", "error": error_message}


def renew_book(userid: str, password: str, item_id: int) -> Dict[str, Any]:
    scraper, login_output = login(userid, password)
    if login_output.get("status") != "success":
        return {"status": "error", "error": login_output.get("error", "Login failed")}
    borrower_id = login_output.get("user", {}).get("borrower_id")
    if borrower_id is None:
        return {"status": "error", "error": "Missing borrower_id"}

    result = renew_item(scraper, item_id, borrower_id)
    return result
    


