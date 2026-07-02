"""OpenAI-compatible provider — supports any OpenAI-compatible API endpoint."""
import json
import logging
import httpx
from typing import Any

from src.models.daily_report import DailyReportExtract

logger = logging.getLogger(__name__)

_EXTRACTION_PROMPT = """你是一名医药业务助理。请从以下医药代表日报文本中提取结构化信息。

对每条日报记录，提取以下字段（未知的留空字符串 ""，不要编造）：
- date: 沟通日期，格式 YYYY-MM-DD
- department: 科室名称
- customer_id: 客户编号（如 C001）
- topic: 沟通主题
- feedback: 客户反馈
- follow_up_task: 后续任务
- task_deadline: 任务截止日期 YYYY-MM-DD
- follow_up_status: 跟进状态 (pending/completed/cancelled)
- medical_question: 客户提出的医学问题
- activity_name: 相关活动名称

请严格返回 JSON 数组格式：
[{"date": "...", "department": "...", ...}]

原始日报文本：
"""

_SUMMARY_PROMPT = """你是一名医药学术专员。请根据以下月报统计数据，撰写一段专业的医药业务月报文字总结。

返回 JSON 格式：
{
  "progress_summary": "本月工作进展概述",
  "key_issues": "本月重点医学问题及分析",
  "unfinished_items": "未完成事项说明",
  "next_month_plan": "下月工作计划"
}

统计数据：
"""

_QUERY_PROMPT = """你是一名医学信息专家。请根据以下医学问题，生成用于检索 PubMed 的中英文检索词。

返回 JSON 格式：
{
  "zh_terms": ["中文检索词1", "中文检索词2"],
  "en_terms": ["english term 1", "english term 2"]
}

医学问题：
"""

_SUMMARIZE_PROMPT = """你是一名医学学术编辑。请用中文总结以下医学文献摘要（200字以内），保持客观准确。如摘要为空，请说明无法总结。

文献信息：
标题：{title}
作者：{authors}
期刊：{journal} ({year})
摘要：{abstract}

请直接输出总结文本，不要加前缀。"""


class OpenAICompatibleProvider:
    provider_name = "openai_compatible"

    def __init__(self, base_url: str = "", api_key: str = "", model: str = "gpt-4o-mini",
                 timeout: float = 60.0):
        self.base_url = base_url.rstrip("/") if base_url else "https://api.openai.com/v1"
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def _chat(self, messages: list[dict], temperature: float = 0.3) -> str:
        """Send chat completion request."""
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except httpx.TimeoutException:
            raise RuntimeError(f"模型请求超时 ({self.timeout}s)。请检查网络或增加超时时间。")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RuntimeError("模型接口限流，请稍后重试。")
            raise RuntimeError(f"模型接口返回错误 {e.response.status_code}: {e.response.text[:200]}")
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise RuntimeError(f"模型返回格式异常: {e}")

    def _extract_json(self, text: str) -> Any:
        """Extract JSON object/array from LLM response text."""
        text = text.strip()
        # Remove markdown code fences
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:]) if len(lines) > 1 else text
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        return json.loads(text)

    def test_connection(self) -> bool:
        try:
            self._chat([{"role": "user", "content": "Hello, respond with 'OK'."}], temperature=0)
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def _validate_extracts(self, items: list[dict]) -> list[dict]:
        """Validate through Pydantic, skip invalid entries."""
        validated = []
        for item in items:
            try:
                DailyReportExtract(**item)
                validated.append(item)
            except Exception as e:
                logger.warning(f"Validation failed for item, skipping: {e}")
        return validated

    def extract_daily_reports(self, text: str) -> list[dict]:
        for attempt in range(2):
            try:
                content = self._chat([
                    {"role": "user", "content": _EXTRACTION_PROMPT + text}
                ])
                data = self._extract_json(content)
                if isinstance(data, dict):
                    data = [data]
                validated = self._validate_extracts(data)
                return validated
            except Exception as e:
                logger.warning(f"Extraction attempt {attempt + 1} failed: {e}")
                if attempt == 1:
                    raise RuntimeError(f"AI 解析失败（已重试）: {e}")
        return []

    def generate_monthly_summary(self, context: dict) -> dict:
        ctx_str = json.dumps(context, ensure_ascii=False, indent=2)
        for attempt in range(2):
            try:
                content = self._chat([
                    {"role": "user", "content": _SUMMARY_PROMPT + ctx_str}
                ])
                data = self._extract_json(content)
                return {
                    "progress_summary": data.get("progress_summary", ""),
                    "key_issues": data.get("key_issues", ""),
                    "unfinished_items": data.get("unfinished_items", ""),
                    "next_month_plan": data.get("next_month_plan", ""),
                }
            except Exception as e:
                logger.warning(f"Summary attempt {attempt + 1} failed: {e}")
                if attempt == 1:
                    raise RuntimeError(f"AI 总结生成失败: {e}")
        return {}

    def generate_literature_queries(self, medical_question: str) -> dict:
        for attempt in range(2):
            try:
                content = self._chat([
                    {"role": "user", "content": _QUERY_PROMPT + medical_question}
                ])
                data = self._extract_json(content)
                return {
                    "zh_terms": data.get("zh_terms", [medical_question]),
                    "en_terms": data.get("en_terms", []),
                }
            except Exception as e:
                logger.warning(f"Query generation attempt {attempt + 1} failed: {e}")
                if attempt == 1:
                    raise RuntimeError(f"检索词生成失败: {e}")
        return {"zh_terms": [medical_question], "en_terms": []}

    def summarize_article(self, article: dict) -> str:
        prompt = _SUMMARIZE_PROMPT.format(
            title=article.get("title", ""),
            authors=article.get("authors", ""),
            journal=article.get("journal", ""),
            year=article.get("year", ""),
            abstract=article.get("abstract", ""),
        )
        for attempt in range(2):
            try:
                content = self._chat([
                    {"role": "user", "content": prompt}
                ])
                return content.strip()
            except Exception as e:
                logger.warning(f"Summarize attempt {attempt + 1} failed: {e}")
                if attempt == 1:
                    return f"[AI 总结失败] {e}"
        return ""
