import time
import os
import re
from typing import Optional
from pydantic import BaseModel, Field
from backend.app.core.prompt import RAG_SYSTEM_PROMPT, format_rag_prompt
from backend.app.registry.plans import get_plan_by_id
from backend.app.core.config import settings
from backend.app.core.logging_config import logger

class SourceCitation(BaseModel):
    source_id: str
    plan_id: str
    plan_name: str
    source_document: str
    section_number: str
    section_title: str
    source_page_start: int
    source_page_end: int
    data_status: str
    snippet: str

class GroundedAnswerResult(BaseModel):
    answer_text: str
    citations: list[SourceCitation]
    contains_unverified_notice: bool = False
    is_clarification: bool = False
    denied_notice: Optional[str] = None
    provider_used: str

class AnswerGenerationService:
    """
    RAG Answer Generator with Citation Validation and multi-provider architecture.
    Supports external LLMs (OpenAI, Gemini, Groq) or a deterministic,
    source-grounded local synthesizer when cloud LLM credentials are not configured.
    """

    def __init__(self):
        self.provider = os.environ.get("LLM_PROVIDER", getattr(settings, "LLM_PROVIDER", "local")).lower()
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        self.gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or getattr(settings, "GEMINI_API_KEY", "")
        self.gemini_model = os.environ.get("GEMINI_MODEL", getattr(settings, "GEMINI_MODEL", "gemini-flash-lite-latest"))
        self.gemini_fallback_model = os.environ.get("GEMINI_FALLBACK_MODEL", getattr(settings, "GEMINI_FALLBACK_MODEL", "gemini-flash-latest"))
        self.groq_key = os.environ.get("GROQ_API_KEY")

        if self.gemini_key and self.provider in ["gemini", "local"]:
            self.provider = "gemini"
        elif self.openai_key and self.provider in ["openai", "local"]:
            self.provider = "openai"
        elif self.groq_key and self.provider in ["groq", "local"]:
            self.provider = "groq"
        else:
            self.provider = "grounded_synthesizer"

        logger.info(f"Initialized AnswerGenerationService with provider: '{self.provider}' (Gemini model: {self.gemini_model})")

    def generate_answer(
        self,
        query: str,
        role: str,
        selected_plan_id: str,
        retrieval_result: dict,
        is_comparison: bool = False,
        clarification_prompt: Optional[str] = None,
        denied_plans: Optional[list[str]] = None,
        conversation_history: Optional[list[dict]] = None
    ) -> GroundedAnswerResult:
        # 1. Handle clarification queries directly
        if clarification_prompt:
            return GroundedAnswerResult(
                answer_text=clarification_prompt,
                citations=[],
                is_clarification=True,
                provider_used=self.provider
            )

        # 2. Handle unauthorized employee plan requests
        denied_notice = None
        if denied_plans:
            denied_notice = "Access to the Executive Employee Insurance Plan (EMP-INS-001) is restricted to authenticated employees. Only authorized customer policy terms are displayed below."

        chunks = retrieval_result.get("chunks", [])
        if not chunks:
            # Check if Gemini is enabled to handle general knowledge / educational / technical questions dynamically
            if self.provider == "gemini" and self.gemini_key:
                empty_retrieval = {
                    "chunks": [],
                    "formatted_context": "No relevant policy documents were retrieved for this query.",
                    "contains_unverified": False
                }
                answer_text, success = self._call_gemini(
                    query, role, selected_plan_id, empty_retrieval, is_comparison, conversation_history
                )
                if success:
                    if denied_notice:
                        answer_text = f"> **Access Restriction Notice:** {denied_notice}\n\n" + answer_text
                    return GroundedAnswerResult(
                        answer_text=answer_text,
                        citations=[],
                        denied_notice=denied_notice,
                        provider_used="gemini"
                    )

            fallback_msg = (
                f"{denied_notice}\n\n" if denied_notice else ""
            ) + "The available policy documents do not provide enough information to answer reliably."
            return GroundedAnswerResult(
                answer_text=fallback_msg,
                citations=[],
                denied_notice=denied_notice,
                provider_used=self.provider
            )

        # 3. Build verified citations strictly from retrieved chunks
        verified_citations = self._build_verified_citations(chunks)
        contains_unverified = retrieval_result.get("contains_unverified", False)

        actual_provider = self.provider
        # 4. Generate answer based on configured provider
        if self.provider == "gemini" and self.gemini_key:
            answer_text, success = self._call_gemini(
                query, role, selected_plan_id, retrieval_result, is_comparison, conversation_history
            )
            actual_provider = "gemini" if success else "gemini_fallback"
        elif self.provider == "openai" and self.openai_key:
            answer_text = self._call_openai(query, role, selected_plan_id, retrieval_result, is_comparison)
            actual_provider = "openai"
        else:
            answer_text = self._synthesize_grounded_answer(query, role, selected_plan_id, chunks, is_comparison)
            actual_provider = "grounded_synthesizer"

        answer_text = self._consolidate_inline_citations(answer_text)

        if denied_notice:
            answer_text = f"> **Access Restriction Notice:** {denied_notice}\n\n" + answer_text

        if contains_unverified and verified_citations:
            # Determine plan-specific unverified banner strictly from retrieved chunks and plan scope
            unverified_plan_ids = {
                c.get("metadata", {}).get("plan_id")
                for c in chunks
                if c.get("metadata", {}).get("data_status") == "illustrative_unverified"
            }
            if not unverified_plan_ids and selected_plan_id:
                unverified_plan_ids.add(selected_plan_id)

            has_existing_notice = any(
                term in answer_text.lower()
                for term in ["illustrative", "demonstration data", "not official", "not an official", "notice:"]
            )
            # Avoid attaching policy disclaimers to pure educational or conversational responses
            has_substantive_terms = any(
                term in answer_text.lower()
                for term in ["benefit", "coverage", "hospital stay", "premium", "payout", "waiting period", "icu", "surgery", "₹"]
            )
            is_conversational_greeting = any(
                g in answer_text.lower()
                for g in ["good morning", "good afternoon", "how can i assist", "how can i help you"]
            ) and len(answer_text.strip().split("\n")) <= 2

            if not has_existing_notice and has_substantive_terms and not is_conversational_greeting:
                if "EMP-INS-001" in unverified_plan_ids:
                    unverified_banner = (
                        "\n\n> **Notice:** The Executive Employee Insurance Plan content cited above is illustrative "
                        "demonstration data and does not constitute an official insurance policy contract."
                    )
                elif "HS-GOLD-001" in unverified_plan_ids:
                    unverified_banner = (
                        "\n\n> **Notice:** The Health Shield – Gold content cited above is illustrative "
                        "demonstration data and does not constitute an official insurance policy contract."
                    )
                else:
                    unverified_banner = (
                        "\n\n> **Notice:** The policy content cited above is illustrative "
                        "demonstration data and does not constitute an official insurance policy contract."
                    )
                answer_text += unverified_banner

        return GroundedAnswerResult(
            answer_text=answer_text,
            citations=verified_citations,
            contains_unverified_notice=contains_unverified,
            denied_notice=denied_notice,
            provider_used=actual_provider
        )

    def _build_verified_citations(self, chunks: list[dict]) -> list[SourceCitation]:
        citations = []
        seen = set()
        for idx, chunk in enumerate(chunks, start=1):
            meta = chunk.get("metadata", {})
            cid = chunk.get("chunk_id", f"SRC-{idx}")
            if cid in seen:
                continue
            seen.add(cid)

            plan_id = meta.get("plan_id", "UNKNOWN")
            plan_info = get_plan_by_id(plan_id)
            plan_name = plan_info.plan_name if plan_info else meta.get("plan_name", plan_id)

            snippet = chunk.get("content", "").strip()[:180] + "..."

            citations.append(SourceCitation(
                source_id=f"SRC-{idx}",
                plan_id=plan_id,
                plan_name=plan_name,
                source_document=meta.get("source_document", ""),
                section_number=str(meta.get("section_number", "")),
                section_title=meta.get("section_title", ""),
                source_page_start=int(meta.get("source_page_start", 1)),
                source_page_end=int(meta.get("source_page_end", 1)),
                data_status=meta.get("data_status", "verified"),
                snippet=snippet
            ))
        return citations

    def _consolidate_inline_citations(self, text: str) -> str:
        """
        Consolidates scattered inline citations (e.g. on individual bullets) into a single,
        compact evidence reference at the end of the answer content (before disclaimers/notices).
        Keeps individual bullet points clean, professional, and legible.
        """
        if not text or not text.strip():
            return text

        citation_pattern = re.compile(
            r"`?\[([A-Za-z0-9\s–—\-,]+(?:Section|pp\.|p\.|Plan|Shield|Executive|Comprehensive)[^\]\n]*)\]`?",
            re.IGNORECASE
        )

        notice_idx = text.find("\n\n> **Notice:**")
        if notice_idx != -1:
            main_content = text[:notice_idx]
            notice_content = text[notice_idx:]
        else:
            main_content = text
            notice_content = ""

        raw_citations = citation_pattern.findall(main_content)
        if not raw_citations:
            return text

        unique_citations = []
        seen = set()
        for cit in raw_citations:
            clean_cit = cit.strip()
            if clean_cit and clean_cit not in seen:
                seen.add(clean_cit)
                unique_citations.append(clean_cit)

        cleaned_content = citation_pattern.sub("", main_content)

        lines = []
        for line in cleaned_content.split("\n"):
            l = re.sub(r"\.\s*\.", ".", line)
            l = re.sub(r"\s+\.", ".", l)
            l = re.sub(r"[ \t]+$", "", l)
            lines.append(l)
        cleaned_main = "\n".join(lines).rstrip()

        if len(unique_citations) == 1:
            consolidated_cit = f"[{unique_citations[0]}]"
        else:
            first = unique_citations[0]
            if "," in first:
                plan_prefix = first.split(",")[0].strip()
                if all(c.startswith(plan_prefix) for c in unique_citations):
                    secs_pages = []
                    for c in unique_citations:
                        parts = c.split(",", 1)
                        if len(parts) > 1:
                            secs_pages.append(parts[1].strip())
                        else:
                            secs_pages.append(c)
                    consolidated_cit = f"[{plan_prefix}, {'; '.join(secs_pages)}]"
                else:
                    consolidated_cit = f"[{'; '.join(unique_citations)}]"
            else:
                consolidated_cit = f"[{'; '.join(unique_citations)}]"

        return f"{cleaned_main}\n\n{consolidated_cit}{notice_content}"

    def _synthesize_grounded_answer(
        self,
        query: str,
        role: str,
        selected_plan_id: str,
        chunks: list[dict],
        is_comparison: bool
    ) -> str:
        """
        Deterministic, high-accuracy extractive grounder.
        Synthesizes factual answers directly from authorized policy evidence
        without hallucination or external dependencies.
        """
        plan_info = get_plan_by_id(selected_plan_id)
        selected_name = plan_info.plan_name if plan_info else selected_plan_id

        # Group chunks by plan
        chunks_by_plan = {}
        for c in chunks:
            pid = c.get("plan_id", selected_plan_id)
            chunks_by_plan.setdefault(pid, []).append(c)

        # 1. Comparison query response
        if is_comparison and len(chunks_by_plan) > 1:
            comparison_lines = [f"### Plan Comparison: {', '.join([get_plan_by_id(p).plan_name if get_plan_by_id(p) else p for p in chunks_by_plan.keys()])}\n"]
            comparison_lines.append("| Plan | Relevant Section | Key Documented Terms & Limits | Citations |")
            comparison_lines.append("|---|---|---|---|")

            for pid, plan_chunks in chunks_by_plan.items():
                pinfo = get_plan_by_id(pid)
                pname = pinfo.plan_name if pinfo else pid
                for c in plan_chunks[:2]:
                    meta = c.get("metadata", {})
                    sec_num = meta.get("section_number", "")
                    sec_title = meta.get("section_title", "")
                    p_start = meta.get("source_page_start", "")
                    p_end = meta.get("source_page_end", "")
                    content_clean = c.get("content", "").replace("\n", " ").strip()
                    summary = content_clean[:140] + ("..." if len(content_clean) > 140 else "")
                    citation = f"[{pname}, Sec {sec_num}, p. {p_start}-{p_end}]"
                    comparison_lines.append(f"| **{pname}** | Section {sec_num}: {sec_title} | {summary} | {citation} |")

            comparison_lines.append("\n**Key Policy Differences Observed:**")
            for pid, plan_chunks in chunks_by_plan.items():
                pinfo = get_plan_by_id(pid)
                pname = pinfo.plan_name if pinfo else pid
                lead_chunk = plan_chunks[0]
                meta = lead_chunk.get("metadata", {})
                first_sentence = lead_chunk.get("content", "").split(".")[0].strip()
                sec_ref = f"[{pname}, Section {meta.get('section_number')}, p. {meta.get('source_page_start')}]"
                comparison_lines.append(f"- **{pname}**: {first_sentence}. {sec_ref}")

            return "\n".join(comparison_lines)

        # 2. Single-plan query response
        plan_chunks = chunks_by_plan.get(selected_plan_id, chunks)
        lead_chunk = plan_chunks[0]
        meta = lead_chunk.get("metadata", {})
        sec_num = meta.get("section_number", "")
        sec_title = meta.get("section_title", "")
        p_start = meta.get("source_page_start", 1)
        p_end = meta.get("source_page_end", 1)
        plan_name = meta.get("plan_name", selected_name)
        citation_str = f"[{plan_name}, Section {sec_num}: {sec_title}, p. {p_start}-{p_end}]"

        answer_parts = [
            f"Policy terms for **{plan_name}** ({citation_str}):\n"
        ]

        # Extract structured content from top chunks
        for idx, c in enumerate(plan_chunks[:3]):
            c_meta = c.get("metadata", {})
            c_text = c.get("content", "").strip()
            c_sec = c_meta.get("section_number", "")
            c_title = c_meta.get("section_title", "")
            c_pages = f"p. {c_meta.get('source_page_start')}-{c_meta.get('source_page_end')}"
            ref = f"[{plan_name}, Section {c_sec}, {c_pages}]"

            paragraphs = [p.strip() for p in c_text.split("\n\n") if p.strip()]
            for p in paragraphs:
                if "|" in p and "---" in p:  # Preserves markdown tables
                    answer_parts.append(f"\n{p}\n{ref}\n")
                elif len(p) > 20:
                    answer_parts.append(f"- {p} {ref}")

        return "\n".join(answer_parts)

    def _call_gemini(
        self,
        query: str,
        role: str,
        plan_id: str,
        retrieval_result: dict,
        is_comparison: bool,
        conversation_history: Optional[list[dict]] = None
    ) -> tuple[str, bool]:
        import httpx
        p_info = get_plan_by_id(plan_id)
        plan_name = p_info.plan_name if p_info else plan_id
        prompt = format_rag_prompt(
            query=query,
            context_text=retrieval_result.get("formatted_context", ""),
            selected_plan_name=plan_name,
            role=role,
            is_comparison=is_comparison,
            conversation_history=conversation_history
        )

        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": self.gemini_key
        }
        payload = {
            "system_instruction": {
                "parts": [{"text": RAG_SYSTEM_PROMPT}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 1024
            }
        }

        models_to_try = [self.gemini_model]
        if self.gemini_fallback_model and self.gemini_fallback_model != self.gemini_model:
            models_to_try.append(self.gemini_fallback_model)

        for model_name in models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code == 429:
                        logger.warning(f"Gemini API rate limit (429) on {model_name}. Waiting 3s and retrying...")
                        time.sleep(3.0)
                        resp = client.post(url, headers=headers, json=payload)

                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts and "text" in parts[0]:
                                logger.info(f"Successfully generated answer with Gemini model '{model_name}'.")
                                return parts[0]["text"].strip(), True
                    else:
                        logger.warning(f"Gemini API ({model_name}) returned HTTP {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                logger.warning(f"Gemini API ({model_name}) call failed: {e}")

        logger.error("All Gemini API models failed. Falling back to deterministic grounded synthesizer.")
        fallback_text = self._synthesize_grounded_answer(query, role, plan_id, retrieval_result.get("chunks", []), is_comparison)
        return fallback_text, False

    def _call_openai(self, query: str, role: str, plan_id: str, retrieval_result: dict, is_comparison: bool) -> str:
        try:
            import httpx
            p_info = get_plan_by_id(plan_id)
            prompt = format_rag_prompt(query, retrieval_result.get("formatted_context", ""), p_info.plan_name if p_info else plan_id, role, is_comparison)
            resp = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.openai_key}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": RAG_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.1
                },
                timeout=30.0
            )
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}. Falling back to grounded synthesizer.")
            return self._synthesize_grounded_answer(query, role, plan_id, retrieval_result.get("chunks", []), is_comparison)
