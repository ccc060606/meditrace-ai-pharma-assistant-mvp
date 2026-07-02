"""Tests for literature dedup and PubMed client."""
import pytest
import httpx
from unittest.mock import patch, MagicMock
from src.repositories.literature_repo import LiteratureRepository, _normalize_title
from src.literature.pubmed import PubMedClient


class TestTitleNormalization:
    def test_lowercase_and_strip(self):
        assert _normalize_title("  HELLO World  ") == "hello world"

    def test_remove_punctuation(self):
        result = _normalize_title("Title: Subtitle? With! Punctuation.")
        assert result == "title subtitle with punctuation"

    def test_collapse_whitespace(self):
        assert _normalize_title("hello    world") == "hello world"


class TestArticleDedup:
    def test_dedup_by_pmid(self, test_db):
        repo = LiteratureRepository(test_db)
        a1 = repo.upsert_article({"pmid": "12345", "title": "First"})
        a2 = repo.upsert_article({"pmid": "12345", "title": "Updated Title"})
        assert a1.id == a2.id
        assert a2.title == "Updated Title"

    def test_dedup_by_doi(self, test_db):
        repo = LiteratureRepository(test_db)
        a1 = repo.upsert_article({"doi": "10.1234/test", "title": "Original"})
        a2 = repo.upsert_article({"doi": "10.1234/test", "title": "Same DOI"})
        assert a1.id == a2.id

    def test_dedup_by_title(self, test_db):
        repo = LiteratureRepository(test_db)
        a1 = repo.upsert_article({"title": "A Study on Diabetes"})
        a2 = repo.upsert_article({"title": "A Study on Diabetes!"})
        assert a1.id == a2.id

    def test_different_articles_not_deduped(self, test_db):
        repo = LiteratureRepository(test_db)
        a1 = repo.upsert_article({"pmid": "111", "title": "Study A"})
        a2 = repo.upsert_article({"pmid": "222", "title": "Study B"})
        assert a1.id != a2.id

    def test_pmid_priority_over_doi(self, test_db):
        """PMID match should take priority even if DOI differs."""
        repo = LiteratureRepository(test_db)
        a1 = repo.upsert_article({"pmid": "111", "doi": "10.1/a", "title": "First"})
        a2 = repo.upsert_article({"pmid": "111", "doi": "10.2/b", "title": "Updated"})
        assert a1.id == a2.id
        assert a2.doi == "10.2/b"  # Updated


class TestPubMedClient:
    def test_parse_id_list(self):
        client = PubMedClient(email="test@test.com")
        xml = """<?xml version="1.0"?>
        <eSearchResult>
            <IdList>
                <Id>12345</Id>
                <Id>67890</Id>
            </IdList>
        </eSearchResult>"""
        ids = client._parse_id_list(xml)
        assert ids == ["12345", "67890"]

    def test_parse_empty_id_list(self):
        client = PubMedClient(email="test@test.com")
        xml = """<?xml version="1.0"?>
        <eSearchResult>
            <IdList></IdList>
        </eSearchResult>"""
        ids = client._parse_id_list(xml)
        assert ids == []

    def test_parse_single_article(self):
        """Test parsing a minimal PubmedArticle XML element."""
        import xml.etree.ElementTree as ET
        xml = """<?xml version="1.0"?>
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation Status="Publisher">
                    <PMID>12345</PMID>
                    <Article>
                        <Journal>
                            <Title>Test Journal</Title>
                            <JournalIssue>
                                <PubDate><Year>2025</Year></PubDate>
                            </JournalIssue>
                        </Journal>
                        <ArticleTitle>Test Article Title</ArticleTitle>
                        <Abstract>
                            <AbstractText>This is the abstract text.</AbstractText>
                        </Abstract>
                        <AuthorList>
                            <Author><LastName>Smith</LastName><ForeName>John</ForeName></Author>
                        </AuthorList>
                        <PublicationType>Journal Article</PublicationType>
                        <ELocationID EIdType="doi">10.1234/test</ELocationID>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>"""
        root = ET.fromstring(xml)
        articles = PubMedClient(email="test@test.com")._parse_articles(xml)
        assert len(articles) == 1
        art = articles[0]
        assert art["pmid"] == "12345"
        assert art["title"] == "Test Article Title"
        assert art["journal"] == "Test Journal"
        assert art["year"] == 2025
        assert "abstract text" in art["abstract"].lower()
        assert art["authors"] == "Smith John"
        assert art["doi"] == "10.1234/test"
        assert "pubmed.ncbi.nlm.nih.gov/12345" in art["source_url"]

    def test_parse_invalid_xml(self):
        client = PubMedClient(email="test@test.com")
        result = client._parse_articles("<not>valid</xml>")
        assert result == []


class TestMockProviderLiteratureQueries:
    def test_generate_queries(self):
        from src.llm.mock_provider import MockProvider
        provider = MockProvider()
        result = provider.generate_literature_queries("糖尿病药物治疗安全性")
        assert "zh_terms" in result
        assert "en_terms" in result
        assert len(result["en_terms"]) >= 1

    def test_summarize_article(self):
        from src.llm.mock_provider import MockProvider
        provider = MockProvider()
        summary = provider.summarize_article({
            "title": "Test Article",
            "abstract": "This is a long abstract about diabetes treatment efficacy.",
        })
        assert "[Mock AI 总结]" in summary
