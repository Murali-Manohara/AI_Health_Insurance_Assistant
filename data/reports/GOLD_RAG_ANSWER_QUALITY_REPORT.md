# Health Shield – Gold (HS-GOLD-001) RAG Retrieval & Answer Quality Evaluation Report

**Evaluation Date:** 2026-10-23T19:00:09Z  
**Plan ID:** `HS-GOLD-001` (Health Shield – Gold)  
**LLM Provider Used:** `gemini` (`gemini-flash-lite-latest`)  
**Average Overall Match Score:** **98.06%**  

---

## 1. Executive Summary & Quality Scorecard

| Question ID | Question | Retrieval (30%) | Factual (35%) | Citations (15%) | NL Quality (10%) | Data Status (10%) | Overall Match | Critical Failure |
|---|---|---:|---:|---:|---:|---:|---:|:---:|
| **GOLD-Q1** | What is the Daily Hospital Cash benefit,... | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | **100.0%** | ✅ NO |
| **GOLD-Q2** | What is the ICU limit per day and per ye... | 100.0% | 83.33% | 100.0% | 100.0% | 100.0% | **94.17%** | ✅ NO |
| **GOLD-Q3** | What is the payout for Major Surgery Cat... | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | **100.0%** | ✅ NO |

---

## 2. Root Cause Analysis of Diagnosed Issues

### A. Greeting Handling (`Hello`)
- **Issue Identified:** A simple `Hello` triggered a full vector and BM25 search against the 119-chunk collection. BM25 found 0 matches, and dense vector distance exceeded 1.04, selecting 5 unrelated tables (Sections 13, 14, 17, 12, 16) and dumping benefit tables into the chat.
- **Root Cause:** Absence of conversational intent / greeting handling in `ScopeResolver`.
- **Correction Implemented:** Added conversational intent recognition in `ScopeResolver` (`is_greeting: bool = True`) and immediate natural greeting response in `RAGOrchestrator` without triggering vector search, citations, or policy disclaimers.

### B. Cross-Section Table Duplication (Sections 13 & 14)
- **Issue Identified:** `Table 2: Benefit Combination / Status` appeared in Section 12, Section 13, and Section 14.
- **Root Cause:** In `document_structure.py`, tables were mapped to sections purely using page bounds (`p_start <= tbl.page_start <= p_end`). Because Section 12, 13, and 14 all overlap Page 8 of `health_shield_gold.pdf`, Table 2 was associated with all three sections during initial ingestion.
- **Correction Implemented:**
  1. Cleaned `data/staging/parent_store.json` so Section 13 and Section 14 only contain their actual source content and child chunks (Table 2 legitimately belongs solely to Section 12).
  2. Added chunk text normalization deduplication in `retrieval_service._reciprocal_rank_fusion` and `retrieval_service._build_context` to guarantee identical content blocks are never repeated.
  3. Replaced duplicate raw parent markdown dumps with concise `--- Document Structure Reference ---` headers.

### C. Disclaimer Isolation & Gold Notice
- **Issue Identified:** A Gold conversation previously received the `Executive Employee Insurance Plan` notice.
- **Root Cause:** In `generation_service.py`, any unverified chunk flagged `contains_unverified=True`, which triggered a hardcoded banner mentioning the Executive Employee Insurance Plan.
- **Correction Implemented:** Replaced hardcoded notice with strict plan-isolated disclaimers in `generation_service.py`. Gold queries now strictly receive: `The Health Shield – Gold content cited above is illustrative demonstration data and does not constitute an official insurance policy contract.`

### D. Gemini Invocation & Natural Language Generation
- **Issue Identified:** Chatbot was outputting raw markdown bullet dumps of chunk text instead of natural-language answers.
- **Root Cause:** The `google.generativeai` package was missing from the virtual environment, causing silent failure and fallback to `_synthesize_grounded_answer()` which literally formatted raw markdown tables and text.
- **Correction Implemented:** Replaced the uninstalled library with a direct, robust `httpx` REST caller in `_call_gemini` connecting to `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent` using `gemini-flash-lite-latest` and `gemini-flash-latest` fallback, enforcing the 16-point grounding prompt.

---

## 3. Question-by-Question Deep Dive & Evaluation
### Question: GOLD-Q1 — What is the Daily Hospital Cash benefit, and what are its limits?

#### Expected Answer Reference
> Health Shield – Gold provides an illustrative Daily Hospital Cash benefit of ₹5,000 per day for eligible hospitalizations exceeding 24 hours. The maximum benefit is 20 days per policy year and 20 days over the illustrative policy period. For example, four eligible payable days would result in an illustrative benefit of ₹20,000 (₹5,000 × 4 days). These are illustrative demonstration values and must not be represented as verified real insurance coverage.

#### Actual Gemini Answer Generated
```text
Based on your selected plan, Health Shield – Gold, here are the details regarding the Daily Hospital Cash benefit and its limits:

* **Daily Hospital Cash Amount:** The illustrative Daily Hospital Cash benefit is **₹5,000** [Health Shield – Gold | Section 3: HOSPITAL CASH BENEFIT, pp. 2–3].
* **Minimum Hospitalization Duration:** Hospitalization must last **more than 24 hours** to qualify [Health Shield – Gold | Section 3: HOSPITAL CASH BENEFIT, pp. 2–3].
* **Maximum Benefit Days:** 
  * Maximum Benefit Days Per Policy Year: **20 days** [Health Shield – Gold | Section 3: HOSPITAL CASH BENEFIT, pp. 2–3].
  * Maximum Benefit Days Over the Illustrative Policy Period: **20 days** [Health Shield – Gold | Section 3: HOSPITAL CASH BENEFIT, pp. 2–3].
* **Calculation Example:** If an eligible hospitalization qualifies for 4 payable days, the illustrative benefit is calculated as: 
  $$\text{₹5,000} \times 4 \text{ days} = \text{₹20,000}$$ 
  [Health Shield – Gold | Section 3: HOSPITAL CASH BENEFIT, pp. 2–3].

*Please note: The policy figures and benefits provided in the Health Shield – Gold plan are illustrative demonstration values and not official verified coverage [Health Shield – Gold | Section 3: HOSPITAL CASH BENEFIT, pp. 2–3].*

> **Notice:** The Health Shield – Gold content cited above is illustrative demonstration data and does not constitute an official insurance policy contract.
```

**Provider Used:** `gemini` | **Overall Match Score:** **100.0%**

#### Detailed Dimension Breakdown
- **Retrieval Evidence Coverage (100.0%):** Retrieved 6 of 6 required evidence items.
- **Answer Factual Correctness (100.0%):** Earned 6.0 / 6.0 points.
- **Citation Correctness (100.0%):** Plan match: `True`, Section match: `True`, Citations count: `5`.
- **Natural-Language Quality (100.0%):** Word count: 216, Raw dump: `False`.
- **Data-Status Compliance (100.0%):** Illustrative status respected: `True`.

---
### Question: GOLD-Q2 — What is the ICU limit per day and per year?

#### Expected Answer Reference
> The Gold plan document specifies an illustrative ICU benefit of ₹10,000 per day. However, it does not define the maximum number of ICU benefit days or a separate annual ICU limit. The ICU eligibility conditions are also not officially defined, and whether the ICU benefit can be combined with Hospital Cash depends on approved policy terms. Therefore, the daily benefit is specified, but the annual ICU limit cannot be confirmed from the document.

#### Actual Gemini Answer Generated
```text
Based on your Health Shield – Gold plan, here are the details regarding the ICU benefit limits:

* **Daily ICU Benefit:** The illustrative daily ICU benefit is **₹10,000** per day when an eligible insured person is admitted to an Intensive Care Unit (ICU) [Health Shield – Gold, Section 4: ICU BENEFIT, p. 3]. 
* **Maximum ICU Benefit Days (Per Year / Total):** The maximum ICU benefit days are **not defined** in the available policy documents [Health Shield – Gold, Section 4: ICU BENEFIT, p. 3].
* **ICU Eligibility Conditions:** The eligibility conditions are **not officially defined** [Health Shield – Gold, Section 4: ICU BENEFIT, p. 3].

*Note: Please be aware that the figures provided for the Health Shield – Gold plan are illustrative demonstration values and not official verified coverage [Health Shield – Gold, Section 4: ICU BENEFIT, p. 3].*

> **Notice:** The Health Shield – Gold content cited above is illustrative demonstration data and does not constitute an official insurance policy contract.
```

**Provider Used:** `gemini` | **Overall Match Score:** **94.17%**

#### Detailed Dimension Breakdown
- **Retrieval Evidence Coverage (100.0%):** Retrieved 6 of 6 required evidence items.
- **Answer Factual Correctness (83.33%):** Earned 5.0 / 6.0 points.
- **Citation Correctness (100.0%):** Plan match: `True`, Section match: `True`, Citations count: `5`.
- **Natural-Language Quality (100.0%):** Word count: 163, Raw dump: `False`.
- **Data-Status Compliance (100.0%):** Illustrative status respected: `True`.

---
### Question: GOLD-Q3 — What is the payout for Major Surgery Category 2?

#### Expected Answer Reference
> The Gold plan specifies an illustrative Major Surgery Benefit basis of ₹5,00,000. The proposed payout for Category 2 is 60% of that basis: ₹5,00,000 × 60% = ₹3,00,000. The document describes these as illustrative payout values. The actual surgery list and category mapping have not been officially defined, so a particular operation's category cannot be confirmed without the applicable approved policy terms.

#### Actual Gemini Answer Generated
```text
Under the Health Shield – Gold plan, the illustrative payout for Major Surgery Category 2 is **₹3,00,000**, which represents 60% of the illustrative Gold Benefit Basis of ₹5,00,000 [Health Shield – Gold, Section 5, pp. 3-4].

Please note that these figures are illustrative demonstration values and not official verified coverage, and the surgery list and category mapping are not officially defined [Health Shield – Gold, Section 5, pp. 3-4].

> **Notice:** The Health Shield – Gold content cited above is illustrative demonstration data and does not constitute an official insurance policy contract.
```

**Provider Used:** `gemini` | **Overall Match Score:** **100.0%**

#### Detailed Dimension Breakdown
- **Retrieval Evidence Coverage (100.0%):** Retrieved 5 of 5 required evidence items.
- **Answer Factual Correctness (100.0%):** Earned 6.0 / 6.0 points.
- **Citation Correctness (100.0%):** Plan match: `True`, Section match: `True`, Citations count: `5`.
- **Natural-Language Quality (100.0%):** Word count: 92, Raw dump: `False`.
- **Data-Status Compliance (100.0%):** Illustrative status respected: `True`.

---