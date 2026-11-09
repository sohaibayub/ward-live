"""WARD rule set with element capture.

The detection logic is the one used for the five-country census
(ward/ward_civil_chunk_json.py in the replication package). Nothing in the
conditions has been changed, so counts here equal counts there. The only
addition is that each issue carries the offending element (a short HTML
snippet and a locator) so the demo can show it and turn it into a task unit.
test_parity.py checks the equality against the original class on live pages.
"""

import re
import time
import warnings
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Tag

warnings.filterwarnings("ignore")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
]

# The four criteria WCAG 2.2 introduced (as evaluated by WARD) and the one it removed.
NEW22 = {"2.4.11", "3.2.6", "3.3.7", "3.3.8"}
REMOVED22 = {"4.1.1"}

# Official W3C conformance levels (the paper uses these, not the tool's own label).
LEVEL_A = {"1.1.1", "1.3.1", "1.4.1", "2.1.1", "2.4.1", "2.4.2", "2.4.4", "2.5.3",
           "3.1.1", "3.2.6", "3.3.7", "4.1.1", "4.1.2"}

# Everything WARD can evaluate, by version.
CRITERIA_21 = {"1.1.1", "1.3.1", "1.3.4", "1.3.5", "1.4.1", "1.4.4", "1.4.10", "1.4.12", "1.4.13",
               "2.1.1", "2.4.1", "2.4.2", "2.4.4", "2.4.6", "2.5.3", "3.1.1", "4.1.1", "4.1.2"}
CRITERIA_22 = (CRITERIA_21 - REMOVED22) | NEW22


def locator(el):
    """Short, human-readable locator for an element."""
    if not isinstance(el, Tag):
        return ""
    parts = []
    node = el
    depth = 0
    while isinstance(node, Tag) and node.name not in ("[document]", "html") and depth < 4:
        p = node.name
        if node.get("id"):
            p += "#" + str(node.get("id"))
            parts.append(p)
            break
        cls = node.get("class")
        if cls:
            p += "." + ".".join(str(c) for c in cls[:2])
        parts.append(p)
        node = node.parent
        depth += 1
    return " > ".join(reversed(parts))


def snippet(el, limit=220):
    if not isinstance(el, Tag):
        return ""
    s = str(el)
    s = re.sub(r"\s+", " ", s).strip()
    return s if len(s) <= limit else s[:limit] + "..."


def issue(criterion, level, text, el=None):
    return {"criterion": criterion, "level": level, "issue": text,
            "element": snippet(el), "locator": locator(el)}


class WARDLive:
    def __init__(self, timeout=15, max_retries=2, retry_delay=1.5):
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    # Fetch layer, as in the census tool.
    def _variants(self, url):
        url = url.strip().rstrip("/")
        if not url.startswith("http"):
            url = "https://" + url
        parsed = urlparse(url)
        host = parsed.netloc
        scheme = parsed.scheme
        variants = [url]
        if host.startswith("www."):
            alt = url.replace(host, host[4:], 1)
        else:
            alt = url.replace(host, "www." + host, 1)
        variants.append(alt)
        opp = "http" if scheme == "https" else "https"
        variants.append(url.replace(scheme + "://", opp + "://", 1))
        variants.append(alt.replace(scheme + "://", opp + "://", 1))
        return list(dict.fromkeys(variants))

    def fetch(self, url):
        variants = self._variants(url)
        last_err = None
        attempts = []
        for attempt in range(self.max_retries):
            target = variants[attempt % len(variants)]
            headers = {"User-Agent": USER_AGENTS[attempt % len(USER_AGENTS)]}
            t0 = time.time()
            try:
                r = requests.get(target, headers=headers, timeout=self.timeout,
                                 verify=False, allow_redirects=True)
                r.raise_for_status()
                attempts.append({"url": target, "status": r.status_code, "ms": int((time.time() - t0) * 1000)})
                return r.text, r.url, None, attempts
            except requests.exceptions.Timeout:
                last_err = "Timeout"
            except requests.exceptions.SSLError:
                last_err = "SSL Error"
            except requests.exceptions.ConnectionError as e:
                last_err = f"Connection: {str(e)[:60]}"
            except requests.exceptions.HTTPError as e:
                last_err = f"HTTP {e.response.status_code}"
                attempts.append({"url": target, "status": e.response.status_code, "ms": int((time.time() - t0) * 1000)})
                if e.response.status_code in (403, 404, 410):
                    break
                attempts.pop()
            except Exception as e:
                last_err = f"Error: {str(e)[:60]}"
            attempts.append({"url": target, "status": None, "error": last_err, "ms": int((time.time() - t0) * 1000)})
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay * (2 ** attempt))
        return None, url, last_err, attempts

    # Rules. Conditions identical to the census tool; element capture added.
    def _check_2_0(self, soup):
        issues = []
        for img in soup.find_all("img"):
            if img.get("alt") is None and img.get("role") != "presentation":
                issues.append(issue("1.1.1", "A", "Image missing alt attribute", img))

        headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
        levels = [int(h.name[1]) for h in headings]
        for i in range(1, len(levels)):
            if levels[i] - levels[i - 1] > 1:
                issues.append(issue("1.3.1", "A", f"Heading skip h{levels[i-1]}->h{levels[i]}", headings[i]))
                break
        for inp in soup.find_all(["input", "select", "textarea"]):
            if inp.get("type", "text") in ["hidden", "submit", "button", "image", "reset"]:
                continue
            iid = inp.get("id")
            labelled = bool(soup.find("label", {"for": iid})) if iid else False
            if not labelled and not inp.get("aria-label") and not inp.get("aria-labelledby") and not inp.get("title"):
                issues.append(issue("1.3.1", "A", "Form input missing label", inp))

        for a in soup.find_all("a"):
            style = a.get("style", "")
            if ("text-decoration:none" in style.replace(" ", "") or "text-decoration: none" in style) and not a.get("class"):
                issues.append(issue("1.4.1", "A", "Link may rely on color alone", a))

        for s in soup.find_all("style"):
            if s.string and re.search(r"font-size:\s*\d+px", s.string):
                issues.append(issue("1.4.4", "AA", "Fixed pixel font size detected", s))
                break

        for el in soup.find_all(attrs={"onclick": True}):
            if el.name not in ["a", "button", "input", "select", "textarea"]:
                if not el.get("onkeypress") and not el.get("onkeydown") and not el.get("tabindex"):
                    issues.append(issue("2.1.1", "A", "onclick without keyboard handler", el))

        skip = soup.find("a", href=re.compile(r"^#(main|content|skip)", re.I))
        nav = soup.find(["nav", "main"]) or soup.find(attrs={"role": re.compile(r"(navigation|main)", re.I)})
        if not skip and not nav:
            issues.append(issue("2.4.1", "A", "No skip link or landmark regions", soup.find("body")))

        title = soup.find("title")
        if not title or not (title.string or "").strip():
            issues.append(issue("2.4.2", "A", "Page title missing or empty", soup.find("head")))

        for a in soup.find_all("a"):
            txt = a.get_text(strip=True).lower()
            if txt in ["click here", "here", "read more", "more", "link", "learn more"]:
                if not a.get("aria-label") and not a.get("title"):
                    issues.append(issue("2.4.4", "A", f'Non-descriptive link text: "{txt}"', a))

        h1s = soup.find_all("h1")
        if not h1s:
            issues.append(issue("2.4.6", "AA", "No h1 heading found", soup.find("body")))
        elif len(h1s) > 1:
            issues.append(issue("2.4.6", "AA", f"Multiple h1 headings ({len(h1s)})", h1s[1]))

        html_tag = soup.find("html")
        if html_tag and not html_tag.get("lang"):
            issues.append(issue("3.1.1", "A", "HTML lang attribute missing", None))

        ids = [(el.get("id"), el) for el in soup.find_all(id=True)]
        seen, reported = set(), set()
        for id_val, el in ids:
            if id_val in seen and id_val not in reported:
                issues.append(issue("4.1.1", "A", f"Duplicate ID: {id_val}", el))
                reported.add(id_val)
            seen.add(id_val)

        for el in soup.find_all(["div", "span"], attrs={"onclick": True}):
            if not el.get("role") and not el.get("tabindex"):
                issues.append(issue("4.1.2", "A", "Interactive element without role/ARIA", el))

        return issues

    def _check_2_1(self, soup):
        issues = []
        meta = soup.find("meta", attrs={"name": "viewport"})
        if meta:
            content = meta.get("content", "")
            if "user-scalable=no" in content or "user-scalable=0" in content:
                issues.append(issue("1.3.4", "AA", "Viewport locks user scaling", meta))

        personal = ["name", "email", "tel", "street-address", "postal-code", "country", "cc-name", "cc-number"]
        for inp in soup.find_all("input"):
            name = (inp.get("name", "") + inp.get("id", "")).lower()
            if any(p in name for p in personal) and not inp.get("autocomplete"):
                issues.append(issue("1.3.5", "AA", "Personal data input missing autocomplete", inp))

        styles = soup.find_all("style")
        style_txt = " ".join(s.string or "" for s in styles)
        if "overflow-x:scroll" in style_txt.replace(" ", ""):
            issues.append(issue("1.4.10", "AA", "CSS may force horizontal scrolling", styles[0] if styles else None))

        if "!important" in style_txt and ("line-height" in style_txt or "letter-spacing" in style_txt):
            issues.append(issue("1.4.12", "AA", "CSS !important may block text spacing adjustment", styles[0] if styles else None))

        for el in soup.find_all(attrs={"title": True}):
            if len(el.get("title", "")) > 50:
                issues.append(issue("1.4.13", "AA", "Long title attribute hides content on hover", el))

        return issues

    def _check_2_2(self, soup):
        issues = []
        styles = soup.find_all("style")
        style_txt = " ".join(s.string or "" for s in styles)
        if re.search(r"position\s*:\s*(sticky|fixed)", style_txt):
            issues.append(issue("2.4.11", "AA", "Sticky/fixed element may obscure focused component", styles[0] if styles else None))

        for btn in soup.find_all(["button", "a"], attrs={"aria-label": True}):
            visible = btn.get_text(strip=True).lower()
            aria = btn.get("aria-label", "").lower()
            if visible and aria and visible not in aria and aria not in visible:
                issues.append(issue("2.5.3", "AA", "aria-label does not contain visible button text", btn))

        help_pattern = re.compile(r"(contact|help|support|faq)", re.I)
        nav_links = [a.get_text(strip=True) for a in soup.find_all("a")]
        if not any(help_pattern.search(t) for t in nav_links):
            issues.append(issue("3.2.6", "AA", "No contact/help link found in navigation", soup.find("nav")))

        inputs = soup.find_all("input", type="text")
        names = [i.get("name", "").lower() for i in inputs]
        if names.count("name") > 1 or names.count("email") > 1:
            issues.append(issue("3.3.7", "AA", "Potential redundant data entry in form", soup.find("form")))

        captcha_markers = soup.find_all(class_=re.compile(r"captcha|recaptcha|hcaptcha", re.I))
        if captcha_markers:
            has_audio = bool(soup.find(string=re.compile(r"audio.*captcha|listen|sound", re.I)))
            if not has_audio:
                issues.append(issue("3.3.8", "AA", "CAPTCHA with no accessible alternative detected", captcha_markers[0]))

        return issues

    def analyze_html(self, html):
        soup = BeautifulSoup(html, "html.parser")
        ext = self._check_2_0(soup) + self._check_2_1(soup) + self._check_2_2(soup)
        for i in ext:
            i["level"] = "A" if i["criterion"] in LEVEL_A else "AA"
        title = soup.find("title")
        page_title = (title.string or "").strip() if title and title.string else ""
        return ext, page_title

    def analyze(self, url):
        t0 = time.time()
        html, final_url, error, attempts = self.fetch(url)
        fetch_ms = int((time.time() - t0) * 1000)
        if error or not html:
            return {"url": url, "final_url": final_url, "status": "error", "error": error,
                    "attempts": attempts, "fetch_ms": fetch_ms}
        t1 = time.time()
        ext, page_title = self.analyze_html(html)
        return {"url": url, "final_url": final_url, "status": "tested", "error": None,
                "page_title": page_title, "html_bytes": len(html.encode("utf-8", "ignore")),
                "attempts": attempts, "fetch_ms": fetch_ms, "analyze_ms": int((time.time() - t1) * 1000),
                "issues_extended": ext}
