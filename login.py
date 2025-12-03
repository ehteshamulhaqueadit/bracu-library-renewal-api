import cloudscraper
import re
from typing import Dict, Any, List
from lxml import html as lxml_html

def login_kotha(userid, password):
    scraper = cloudscraper.create_scraper()

    # Step 1: fetch login page (Cloudflare solved automatically)
    scraper.get("https://library.bracu.ac.bd/opac")

    # Step 2: submit login (no CSRF required)
    payload = {
        "koha_login_context": "opac",
        "userid": userid,
        "password": password
    }
    response = scraper.post(
        "https://library.bracu.ac.bd/cgi-bin/koha/opac-user.pl",
        data=payload
    )

    return scraper, response.text

def parse_opac_login_html(html: str) -> Dict[str, Any]:
    """Parse Koha OPAC user page HTML using lxml.html (XPath) for efficiency.

    Returns a dictionary with keys:
    - status: "success" or "error"
    - error: optional error message if status == "error"
    - user: { name: str } if success
    - checkouts: [ { title, author, due_date, call_number, renewals_remaining, fines, biblionumber, item_id } ]
    """

    result: Dict[str, Any] = {"status": "error", "error": "Unknown state"}

    # Parse once with lxml.html; it is faster and lightweight
    doc = lxml_html.fromstring(html)

    # Detect login page
    if doc.xpath("//*[@id='opac-login-page']") or doc.xpath("//title[contains(., 'Log in to your account')]"):
        result["status"] = "error"
        result["error"] = "Invalid credentials or not logged in"
        return result

    # Must be on user page
    if not (doc.xpath("//*[@id='opac-user']") or doc.xpath("//*[@id='opac-user-checkouts']")):
        return result

    result["status"] = "success"

    # User name
    name = None
    user_nodes = doc.xpath("//span[contains(@class,'userlabel')]")
    if user_nodes:
        text = user_nodes[0].text_content().strip()
        name = re.sub(r"^Welcome,\s*", "", text, flags=re.I)
    # Borrower ID from hidden input
    borrower_id = None
    borrower_val = doc.xpath("//input[@type='hidden' and @name='borrowernumber']/@value")
    if borrower_val:
        try:
            borrower_id = int(borrower_val[0])
        except ValueError:
            borrower_id = borrower_val[0]
    result["user"] = {"name": name, "borrower_id": borrower_id}

    # Checkouts
    checkouts: List[Dict[str, Any]] = []
    rows = doc.xpath("//table[@id='checkoutst']/tbody/tr")
    for tr in rows:
        # Title
        title = None
        title_span = tr.xpath(".//td[contains(@class,'title')]//span[contains(@class,'biblio-title')]")
        if title_span:
            title = title_span[0].text_content().strip().strip(" /")
        else:
            title_td = tr.xpath(".//td[contains(@class,'title')]")
            if title_td:
                title = title_td[0].text_content().strip()

        # Author
        author = None
        author_td = tr.xpath(".//td[contains(@class,'author')]")
        if author_td:
            author = author_td[0].text_content().strip()

        # Due date
        due_date = None
        due_td = tr.xpath(".//td[contains(@class,'date_due')]")
        if due_td:
            m = re.search(r"(\d{2}/\d{2}/\d{4})", due_td[0].text_content())
            if m:
                due_date = m.group(1)

        # Call number
        call_number = None
        call_td = tr.xpath(".//td[contains(@class,'call_no')]")
        if call_td:
            call_number = call_td[0].text_content().strip()

        # Renewals
        renewals_remaining = None
        renewals_total = None
        renew_td = tr.xpath(".//td[contains(@class,'renew')]")
        if renew_td:
            m = re.search(r"(\d+)\s+of\s+(\d+)\s+renewals remaining", renew_td[0].text_content(), re.I)
            if m:
                renewals_remaining = int(m.group(1))
                renewals_total = int(m.group(2))

        # Fines
        fines = None
        fines_td = tr.xpath(".//td[contains(@class,'fines')]")
        if fines_td:
            fines = fines_td[0].text_content().strip()

        # biblionumber
        biblionumber = None
        detail_link = tr.xpath(".//td[contains(@class,'title')]//a[contains(@href,'opac-detail.pl?biblionumber=')]/@href")
        if detail_link:
            m = re.search(r"biblionumber=(\d+)", detail_link[0])
            if m:
                biblionumber = int(m.group(1))

        # item id
        item_id = None
        renew_link = tr.xpath(".//td[contains(@class,'renew')]//a[contains(@href,'opac-renew.pl')]/@href")
        if renew_link:
            m = re.search(r"item=(\d+)", renew_link[0])
            if m:
                item_id = int(m.group(1))
        if item_id is None:
            checkbox_val = tr.xpath(".//td[contains(@class,'renew')]//input[@name='item']/@value")
            if checkbox_val:
                try:
                    item_id = int(checkbox_val[0])
                except ValueError:
                    pass

        if any([title, author, due_date, call_number, biblionumber, item_id]):
            checkouts.append({
                "title": title,
                "author": author,
                "due_date": due_date,
                "call_number": call_number,
                "renewals_remaining": renewals_remaining,
                "renewals_total": renewals_total,
                "fines": fines,
                "biblionumber": biblionumber,
                "item_id": item_id,
            })

    result["checkouts"] = checkouts
    return result




def login(userid, password):
    scraper, html = login_kotha(userid, password)
    output = parse_opac_login_html(html)
    return scraper, output

# outputs {'status': 'error', 'error': 'Invalid credentials or not logged in'} if failed
# or outputs  {'status': 'success', 'error': 'Unknown state', 'user': {'name': 'EHTESHAMUL HAQUE ADIT'}, 'checkouts': [{'title': 'Economics', 'author': 'Parkin, Michael,', 'due_date': '07/12/2025', 'call_number': 'Call number:\n                                                        330 PAR', 'renewals_remaining': 24, 'renewals_total': 30, 'fines': 'Fines:\n                                                            \n                                                                No', 'biblionumber': 37405, 'item_id': 58734}]} if success
