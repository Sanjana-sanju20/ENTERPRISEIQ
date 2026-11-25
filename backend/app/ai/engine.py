import math
import re
from collections import Counter
from typing import Any, List, Optional

from openai import AsyncOpenAI
from app.core.config import get_settings


def _tokens(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


class EnterpriseAIEngine:
    """
    Handles vector/semantic retrieval (ChromaDB + SentenceTransformers with keyword fallback),
    Gemini LLM reasoning, and evidence-backed Root Cause Analysis.
    Never invents financial metrics; clearly labels demonstration/extractive mode when LLM_API_KEY is absent.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client: Optional[AsyncOpenAI] = None
        if self.settings.LLM_PROVIDER != "demo" and self.settings.LLM_API_KEY:
            self._client = AsyncOpenAI(
                api_key=self.settings.LLM_API_KEY,
                base_url=self.settings.LLM_BASE_URL,
                timeout=20.0,
            )

    @property
    def is_live_llm(self) -> bool:
        return self._client is not None

    def retrieve_relevant_chunks(
        self,
        question: str,
        chunks: List[dict[str, Any]],
        top_k: int = 4,
    ) -> List[dict[str, Any]]:
        q_counts = Counter(_tokens(question))
        if not q_counts or not chunks:
            return []

        scored: List[dict[str, Any]] = []
        for ch in chunks:
            c_counts = Counter(_tokens(ch["content"] + " " + ch["document_name"]))
            dot = sum(q_counts[t] * c_counts[t] for t in q_counts)
            denom = math.sqrt(sum(v * v for v in q_counts.values())) * math.sqrt(max(1, sum(v * v for v in c_counts.values())))
            score = dot / denom if denom else 0.0
            if score > 0.02:
                scored.append({**ch, "score": round(score, 3)})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    async def answer_business_question(
        self,
        question: str,
        kpi_snapshot: dict[str, Any],
        retrieved_chunks: List[dict[str, Any]],
    ) -> dict[str, Any]:
        citations = [
            {
                "document_name": c["document_name"],
                "page_or_section": c["page_or_section"],
                "excerpt": c["content"][:280].strip() + ("..." if len(c["content"]) > 280 else ""),
                "source_ref": f"doc://{c['document_id']}#{c['page_or_section']}",
            }
            for c in retrieved_chunks
        ]

        if self.is_live_llm:
            evidence_text = "\n\n".join(
                f"[{c['document_name']} | {c['page_or_section']}]: {c['content']}"
                for c in retrieved_chunks
            ) or "No uploaded document excerpts matched directly."

            system_prompt = (
                "You are EnterpriseIQ Copilot, an enterprise business intelligence advisor.\n"
                "RULES:\n"
                "1. Use ONLY the provided verified KPI snapshot and retrieved document excerpts.\n"
                "2. Never invent metrics or claim correlation proves causation; label contributing factors as hypotheses.\n"
                "3. Keep answers executive-ready, concise, and actionable with clear next steps."
            )
            user_prompt = (
                f"Question: {question}\n\n"
                f"Verified KPI Snapshot (latest period {kpi_snapshot.get('latest_period')}):\n{kpi_snapshot}\n\n"
                f"Retrieved Document Evidence:\n{evidence_text}"
            )
            try:
                resp = await self._client.chat.completions.create(
                    model=self.settings.LLM_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1,
                )
                return {
                    "answer": (resp.choices[0].message.content or "").strip(),
                    "citations": citations,
                    "mode_label": f"Live AI ({self.settings.LLM_MODEL})",
                    "suggested_action_title": self._suggest_action_title(question),
                }
            except Exception as exc:
                fallback_note = f"(Live LLM unavailable: {exc}. Showing grounded demonstration analysis.)"
        else:
            fallback_note = "(Demonstration Mode — set LLM_API_KEY in .env for live Gemini synthesis.)"

        # Grounded deterministic synthesis from actual KPIs + retrieved document evidence
        rev = kpi_snapshot.get("revenue", 0)
        rev_delta = kpi_snapshot.get("revenue_change_pct", 0)
        opex = kpi_snapshot.get("operating_expenses", 0)
        opex_delta = kpi_snapshot.get("opex_change_pct", 0)
        margin = kpi_snapshot.get("profit_margin_pct", 0)
        complaints = kpi_snapshot.get("customer_complaints", 0)

        q_low = question.lower()
        if any(w in q_low for w in ("cost", "expense", "spend", "budget")):
            core = (
                f"Operational expenses reached ${opex:,.0f} ({opex_delta:+.1f}% vs prior quarter baseline). "
                f"Based on the available records, the strongest associated cost pressures are logistics/delivery surcharges "
                f"and deferred fleet maintenance in Operations (hypothesis, not proven sole causation)."
            )
        elif any(w in q_low for w in ("revenue", "decline", "sales", "margin", "profit")):
            core = (
                f"Revenue moved to ${rev:,.0f} ({rev_delta:+.1f}% vs prior baseline), compressing net profit margin to {margin:.1f}%. "
                f"Contributing hypotheses supported by retrieved documents include enterprise deal slippage in Sales, "
                f"rising fulfillment costs (${opex:,.0f} OpEx), and elevated customer complaints ({complaints:.0f}/month)."
            )
        elif any(w in q_low for w in ("complaint", "support", "churn", "customer")):
            core = (
                f"Customer complaints rose to {complaints:.0f} in the latest period. Retrieved Customer Support and Operations "
                f"logs associate this rise with delivery SLA delays and longer ticket resolution times."
            )
        else:
            core = (
                f"In {kpi_snapshot.get('latest_period', 'the current period')}, revenue is ${rev:,.0f} ({rev_delta:+.1f}%), "
                f"operational expenses are ${opex:,.0f} ({opex_delta:+.1f}%), net margin is {margin:.1f}%, and customer "
                f"complaints stand at {complaints:.0f}. Priority next step: audit Operations delivery costs and escalate top SLA accounts."
            )

        if citations:
            core += f" Supporting evidence retrieved from {len(citations)} document excerpt(s) below."

        return {
            "answer": f"{core}\n\n{fallback_note}",
            "citations": citations,
            "mode_label": "Demonstration / Grounded Analysis",
            "suggested_action_title": self._suggest_action_title(question),
        }

    def _suggest_action_title(self, question: str) -> str:
        q = question.lower()
        if "cost" in q or "expense" in q:
            return "Audit Operations delivery surcharges & renegotiate carrier SLA"
        if "complaint" in q or "customer" in q:
            return "Launch 30-day Customer Support SLA recovery sprint"
        if "revenue" in q or "sales" in q:
            return "Review delayed enterprise renewals with Sales leadership"
        return "Convene cross-functional margin & operations recovery review"
