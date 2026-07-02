"""PubMed E-utilities client — independent, testable with mock HTTPX."""
import logging
import time
import xml.etree.ElementTree as ET
import httpx

from src.config import Config

logger = logging.getLogger(__name__)

PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class PubMedClient:
    """Client for PubMed/NLM E-utilities API."""

    def __init__(self, email: str = None, api_key: str = None, timeout: float = 30.0):
        cfg = Config()
        self.email = email or cfg.pubmed_email or "user@example.com"
        self.api_key = api_key or cfg.pubmed_api_key or ""
        self.timeout = timeout

    def _build_url(self, endpoint: str, params: dict) -> str:
        """Build URL with common parameters."""
        params.setdefault("db", "pubmed")
        params.setdefault("retmode", "xml")
        params.setdefault("email", self.email)
        if self.api_key:
            params["api_key"] = self.api_key
        qs = "&".join(f"{k}={_url_encode(v)}" for k, v in params.items())
        return f"{PUBMED_BASE}/{endpoint}?{qs}"

    def search(self, query: str, max_results: int = 10) -> list[dict]:
        """Search PubMed and return article details.
        Steps: esearch → efetch (with abstracts)."""
        # 1. Search for PMIDs
        search_params = {
            "term": query,
            "retmax": str(min(max_results, 100)),
            "sort": "relevance",
        }
        search_url = self._build_url("esearch.fcgi", search_params)

        try:
            resp = httpx.get(search_url, timeout=self.timeout)
            resp.raise_for_status()
        except httpx.TimeoutException:
            raise RuntimeError(f"PubMed 搜索超时 ({self.timeout}s)")
        except httpx.HTTPError as e:
            raise RuntimeError(f"PubMed API 错误: {e}")

        pmids = self._parse_id_list(resp.text)
        if not pmids:
            return []

        # Rate limit respect
        if not self.api_key:
            time.sleep(0.34)  # ~3 requests/sec without API key

        # 2. Fetch details
        fetch_params = {
            "id": ",".join(pmids),
            "rettype": "abstract",
            "retmode": "xml",
        }
        fetch_url = self._build_url("efetch.fcgi", fetch_params)

        try:
            resp = httpx.get(fetch_url, timeout=self.timeout)
            resp.raise_for_status()
        except Exception as e:
            raise RuntimeError(f"PubMed 获取文献详情失败: {e}")

        articles = self._parse_articles(resp.text)
        return articles[:max_results]

    def _parse_id_list(self, xml_text: str) -> list[str]:
        """Parse esearch XML response for PMIDs."""
        try:
            root = ET.fromstring(xml_text)
            return [id_elem.text for id_elem in root.findall(".//Id")]
        except ET.ParseError as e:
            logger.error(f"Failed to parse PubMed search XML: {e}")
            return []

    def _parse_articles(self, xml_text: str) -> list[dict]:
        """Parse efetch XML response for article details."""
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logger.error(f"Failed to parse PubMed fetch XML: {e}")
            return []

        articles = []
        for article_elem in root.findall(".//PubmedArticle"):
            try:
                art = self._parse_single_article(article_elem)
                if art:
                    articles.append(art)
            except Exception as e:
                logger.warning(f"Failed to parse article: {e}")
                continue
        return articles

    def _parse_single_article(self, elem) -> dict:
        """Parse single PubmedArticle element."""
        medline = elem.find(".//MedlineCitation")
        article = medline.find(".//Article") if medline is not None else None
        if article is None:
            return {}

        # PMID
        pmid_elem = medline.find("PMID")
        pmid = pmid_elem.text if pmid_elem is not None else None

        # Title
        title_elem = article.find("ArticleTitle")
        title = title_elem.text or "" if title_elem is not None else ""

        # Abstract
        abstract_parts = []
        abstract_elem = article.find(".//Abstract")
        if abstract_elem is not None:
            for abs_text in abstract_elem.findall("AbstractText"):
                label = abs_text.get("Label", "")
                text = abs_text.text or ""
                if label:
                    abstract_parts.append(f"{label}: {text}")
                else:
                    abstract_parts.append(text)
        abstract = " ".join(abstract_parts)

        # Authors
        authors = []
        author_list = article.find("AuthorList")
        if author_list is not None:
            for author in author_list.findall("Author"):
                last = author.find("LastName")
                fore = author.find("ForeName")
                if last is not None:
                    name = last.text or ""
                    if fore is not None and fore.text:
                        name = f"{name} {fore.text}"
                    authors.append(name)
        authors_str = "; ".join(authors[:10])
        if len(authors) > 10:
            authors_str += " et al."

        # Journal
        journal_elem = article.find("Journal")
        journal_title = ""
        if journal_elem is not None:
            jtitle = journal_elem.find("Title")
            if jtitle is not None:
                journal_title = jtitle.text or ""

        # Year
        year = None
        if journal_elem is not None:
            ji = journal_elem.find("JournalIssue")
            if ji is not None:
                pd = ji.find("PubDate")
                if pd is not None:
                    yr = pd.find("Year")
                    if yr is not None and yr.text:
                        try:
                            year = int(yr.text)
                        except ValueError:
                            pass

        # DOI
        doi = None
        for eid in article.findall(".//ELocationID"):
            if eid.get("EIdType") == "doi":
                doi = eid.text
                break

        # Study type (from PublicationType)
        pub_types = []
        for pt in article.findall(".//PublicationType"):
            if pt.text:
                pub_types.append(pt.text)
        study_type = "; ".join(pub_types[:5])

        # Source URL
        source_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""

        return {
            "pmid": pmid,
            "doi": doi,
            "title": title.strip() if title else "",
            "authors": authors_str,
            "journal": journal_title,
            "year": year,
            "study_type": study_type,
            "abstract": abstract.strip() if abstract else "",
            "source_url": source_url,
        }


def _url_encode(value) -> str:
    """Encode value for URL query string."""
    import urllib.parse
    return urllib.parse.quote(str(value), safe="")
