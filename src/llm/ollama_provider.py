"""Ollama provider — for local LLM via Ollama API."""
import json
import logging
import httpx

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

请严格返回 JSON 数组格式。

原始日报文本：
"""

_SUMMARY_PROMPT = """请根据以下月报统计数据，撰写一段专业的医药业务月报文字总结（中文）。

返回 JSON 格式（不要加 markdown 标记）：
{"progress_summary": "...", "key_issues": "...", "unfinished_items": "...", "next_month_plan": "..."}

统计数据：
"""

_QUERY_PROMPT = """请根据以下医学问题，生成用于检索 PubMed 的中英文检索词。

返回 JSON（不要加 markdown）：
{"zh_terms": ["词1", "词2"], "en_terms": ["term1", "term2"]}

医学问题：
"""


class OllamaProvider:
    provider_name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3",
                 timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def _generate(self, prompt: str, temperature: float = 0.3) -> str:
        """Send generate request to Ollama."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        try:
            resp = httpx.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")
        except httpx.TimeoutException:
            raise RuntimeError(f"Ollama 请求超时 ({self.timeout}s)。请确认 Ollama 正在运行。")
        except httpx.ConnectError:
            raise RuntimeError(f"无法连接 Ollama ({self.base_url})。请确认 Ollama 已启动。")
        except Exception as e:
            raise RuntimeError(f"Ollama 请求失败: {e}")

    def _extract_json(self, text: str) -> any:
        text = text.strip()
        if "```" in text:
            lines = text.split("\n")
            start = 0
            end = len(lines)
            for i, line in enumerate(lines):
                if line.startswith("```"):
                    if start == 0:
                        start = i + 1
                    else:
                        end = i
                        break
            text = "\n".join(lines[start:end]).strip()
        return json.loads(text)

    def test_connection(self) -> bool:
        try:
            resp = httpx.get(f"{self.base_url}/api/tags", timeout=10)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Ollama connection test failed: {e}")
            return False

    def extract_daily_reports(self, text: str) -> list[dict]:
        for attempt in range(2):
            try:
                content = self._generate(_EXTRACTION_PROMPT + text)
                data = self._extract_json(content)
                if isinstance(data, dict):
                    data = [data]
                validated = []
                for item in data:
                    try:
                        DailyReportExtract(**item)
                        validated.append(item)
                    except Exception as e:
                        logger.warning(f"Validation failed: {e}")
                return validated
            except Exception as e:
                logger.warning(f"Ollama extract attempt {attempt + 1}: {e}")
                if attempt == 1:
                    raise RuntimeError(f"Ollama 解析失败: {e}")
        return []

    def generate_monthly_summary(self, context: dict) -> dict:
        ctx_str = json.dumps(context, ensure_ascii=False, indent=2)
        for attempt in range(2):
            try:
                content = self._generate(_SUMMARY_PROMPT + ctx_str)
                data = self._extract_json(content)
                return {
                    "progress_summary": data.get("progress_summary", ""),
                    "key_issues": data.get("key_issues", ""),
                    "unfinished_items": data.get("unfinished_items", ""),
                    "next_month_plan": data.get("next_month_plan", ""),
                }
            except Exception as e:
                logger.warning(f"Ollama summary attempt {attempt + 1}: {e}")
                if attempt == 1:
                    raise RuntimeError(f"Ollama 总结生成失败: {e}")
        return {}

    def generate_literature_queries(self, medical_question: str) -> dict:
        for attempt in range(2):
            try:
                content = self._generate(_QUERY_PROMPT + medical_question)
                data = self._extract_json(content)
                return {
                    "zh_terms": data.get("zh_terms", [medical_question]),
                    "en_terms": data.get("en_terms", []),
                }
            except Exception as e:
                logger.warning(f"Ollama query attempt {attempt + 1}: {e}")
                if attempt == 1:
                    raise RuntimeError(f"检索词生成失败: {e}")
        return {"zh_terms": [medical_question], "en_terms": []}

    def summarize_article(self, article: dict) -> str:
        prompt = f"""请用中文总结以下医学文献摘要（200字以内），保持客观准确。
标题：{article.get('title', '')}
期刊：{article.get('journal', '')} ({article.get('year', '')})
摘要：{article.get('abstract', '')}
请直接输出总结文本。"""
        for attempt in range(2):
            try:
                return self._generate(prompt).strip()
            except Exception as e:
                logger.warning(f"Ollama summarize attempt {attempt + 1}: {e}")
                if attempt == 1:
                    return f"[AI 总结失败] {e}"
        return ""
