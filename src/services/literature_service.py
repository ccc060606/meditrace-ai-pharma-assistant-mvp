"""Literature service — orchestrates PubMed search, dedup, and AI summarization."""
import json
import logging

from src.repositories.literature_repo import LiteratureRepository
from src.llm.base import LLMProvider
from src.literature.pubmed import PubMedClient

logger = logging.getLogger(__name__)


class LiteratureService:
    def __init__(self, repo: LiteratureRepository, llm: LLMProvider = None,
                 pubmed: PubMedClient = None):
        self.repo = repo
        self.llm = llm
        self.pubmed = pubmed or PubMedClient()

    def generate_queries(self, question_text: str) -> dict:
        """Use LLM to generate search queries from a medical question."""
        if self.llm:
            try:
                return self.llm.generate_literature_queries(question_text)
            except Exception as e:
                logger.warning(f"LLM query generation failed: {e}")
        # Fallback: use the question itself
        return {
            "zh_terms": [question_text],
            "en_terms": [question_text],
        }

    def search_and_save(self, question_text: str, report_id: int = None,
                        max_results: int = 10,
                        custom_queries: dict = None) -> dict:
        """Full pipeline: generate queries, search PubMed, save results.

        Args:
            question_text: The medical question to search for
            report_id: Optional daily report ID to link
            max_results: Max number of results to return
            custom_queries: Optional dict with 'zh_terms' and 'en_terms' to use
                           instead of auto-generating via LLM.
        """
        # 1. Generate or use custom queries
        if custom_queries:
            queries = custom_queries
        else:
            queries = self.generate_queries(question_text)

        # 2. Save question
        question = self.repo.save_question(
            question_text=question_text,
            report_id=report_id,
            search_terms_zh=queries.get("zh_terms", []),
            search_terms_en=queries.get("en_terms", []),
        )

        # 3. Search PubMed with English terms (primary)
        all_articles = []
        errors = []
        en_terms = queries.get("en_terms", [])
        if not en_terms:
            en_terms = [question_text]

        # Detect if we're in mock mode
        is_mock = self.llm is not None and getattr(self.llm, 'provider_name', '') == 'mock'

        for term in en_terms[:3]:  # Limit to 3 queries
            try:
                if is_mock:
                    # Use mock provider's built-in PubMed search (offline)
                    results = self.llm.search_pubmed(term, max_results=max(max_results // len(en_terms[:3]), 3))
                else:
                    results = self.pubmed.search(term, max_results=max(max_results // len(en_terms[:3]), 3))
                all_articles.extend(results)
            except Exception as e:
                msg = f"PubMed search failed for '{term}': {e}"
                logger.warning(msg)
                # Try mock fallback if available
                if not is_mock and self.llm and hasattr(self.llm, 'search_pubmed'):
                    try:
                        logger.info("Falling back to mock PubMed search...")
                        results = self.llm.search_pubmed(term, max_results=max(max_results // len(en_terms[:3]), 3))
                        all_articles.extend(results)
                        errors.append(f"PubMed 不可用，已使用 Mock 数据替代 ({term})")
                    except Exception:
                        errors.append(msg)
                else:
                    errors.append(msg)

        # 4. Dedup and save
        saved = []
        seen_pmids = set()
        seen_dois = set()
        for art in all_articles:
            if art.get("pmid") and art["pmid"] in seen_pmids:
                continue
            if art.get("doi") and art["doi"] in seen_dois:
                continue
            if art.get("pmid"):
                seen_pmids.add(art["pmid"])
            if art.get("doi"):
                seen_dois.add(art["doi"])
            art["medical_question_id"] = question.id
            try:
                saved_art = self.repo.upsert_article(art)
                saved.append(saved_art)
            except Exception as e:
                logger.warning(f"Failed to save article: {e}")

        return {
            "question": question,
            "articles": saved,
            "errors": errors,
            "queries": queries,
        }

    def summarize_article(self, article_id: int, article_data: dict) -> str:
        """Generate AI summary for an article."""
        if not self.llm:
            return "[Mock] 请查看原始摘要。"
        try:
            return self.llm.summarize_article(article_data)
        except Exception as e:
            logger.warning(f"Summarize failed for article {article_id}: {e}")
            return f"[AI 总结失败] {e}"

    def get_questions(self):
        return self.repo.get_all_questions()

    def get_articles_for_question(self, question_id: int):
        return self.repo.get_articles_for_question(question_id)

    def get_all_articles(self):
        return self.repo.get_all_articles()
