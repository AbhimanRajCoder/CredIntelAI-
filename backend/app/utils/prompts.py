"""
LLM prompts for Intelli-Credit agents.
"""

# ─── Data Ingestor Prompts ────────────────────────────────────────────────────

FINANCIAL_EXTRACTION_PROMPT = """You are a financial data extraction specialist working for a credit appraisal team.

Analyze the following extracted document text and identify key financial metrics.

**Document Text:**
{document_text}

**Extract the following metrics (in INR where applicable):**
1. Revenue / Turnover (annual)
2. Net Profit / PAT
3. Total Debt (long-term + short-term)
4. Operating Cash Flow
5. Bank Loans / Credit Facilities
6. Litigation Mentions (count any references to legal cases, disputes, NCLT, etc.)
7. Debt-to-Equity Ratio
8. Current Ratio
9. Interest Coverage Ratio
10. Net Profit Margin (%)
11. Return on Equity (%)

**Instructions:**
- Extract ONLY from the provided text. Do not fabricate numbers.
- If a metric is not found, set it to null.
- Convert all amounts to INR (Indian Rupees).
- For percentages, provide as decimal (e.g., 15% = 15.0).
- Count litigation mentions carefully.

**Respond ONLY in valid JSON format:**
{{
    "revenue": <number or null>,
    "profit": <number or null>,
    "debt": <number or null>,
    "cashflow": <number or null>,
    "bank_loans": <number or null>,
    "litigation_mentions": <integer>,
    "debt_to_equity_ratio": <number or null>,
    "current_ratio": <number or null>,
    "interest_coverage_ratio": <number or null>,
    "net_profit_margin": <number or null>,
    "return_on_equity": <number or null>,
    "promoter_names": ["<Full Name 1>", "<Full Name 2>", ...]
}}
"""

# ─── Risk Analysis Prompts ────────────────────────────────────────────────────

RISK_ANALYSIS_PROMPT = """You are a senior credit risk analyst at a leading Indian bank.

Analyze the following data and provide a comprehensive credit risk assessment.

**Company:** {company_name}
**Sector:** {sector}

**Financial Metrics:**
{financial_metrics}

**Research Signals:**
{research_signals}

**Due Diligence Notes:**
{due_diligence_notes}

**Your Analysis Must Include:**

1. **Risk Score** (0-100, where 0 = lowest risk, 100 = highest risk)
2. **Risk Grade** (AAA, AA, A, BBB, BB, B, CCC, CC, C, D)
   - AAA-A: Investment grade (low risk)
   - BBB-BB: Moderate risk
   - B-CCC: High risk
   - CC-D: Very high / default risk
3. **Key Risks** (list top 5 risk factors)
4. **Strengths** (list top 5 positive factors)
5. **Explanation** (detailed 200-word analysis)

**Risk Scoring Guidelines:**
- Debt-to-Equity > 2.0: +15 points
- Negative profit: +20 points
- Litigation mentions > 3: +10 points
- Negative news count > 2: +10 points
- Promoter risk = "high": +15 points
- Sector risk = "high": +10 points
- Low current ratio (< 1.0): +10 points

**Respond ONLY in valid JSON format:**
{{
    "risk_score": <number 0-100>,
    "risk_grade": "<grade>",
    "key_risks": ["<risk1>", "<risk2>", ...],
    "strengths": ["<strength1>", "<strength2>", ...],
    "explanation": "<detailed explanation>"
}}
"""

# ─── CAM Generator Prompts ────────────────────────────────────────────────────

CAM_COMPANY_OVERVIEW_PROMPT = """You are a credit analyst writing a Credit Appraisal Memo (CAM).

Write a professional **Company Overview** section for:

**Company:** {company_name}
**Sector:** {sector}
**Financial Summary:** {financial_summary}
**Research Information:** {research_info}

Write 200-300 words covering:
- Company background and nature of business
- Key products/services
- Market position
- Years in operation (if known)

Write in formal banking language. Do not fabricate facts - only use information from the provided data.
"""

CAM_PROMOTER_BACKGROUND_PROMPT = """You are a credit analyst writing a Credit Appraisal Memo (CAM).

Write a professional **Promoter Background** section for:

**Company:** {company_name}
**Research Findings:** {research_info}
**Due Diligence Notes:** {due_diligence_notes}

Write 150-250 words covering:
- Promoter/director profiles
- Track record and experience
- Any adverse findings
- Corporate governance indicators

Write in formal banking language. Only use provided information.
"""

CAM_FINANCIAL_ANALYSIS_PROMPT = """You are a credit analyst writing a Credit Appraisal Memo (CAM).

Write a professional **Financial Analysis** section for:

**Company:** {company_name}
**Financial Metrics:**
{financial_metrics}

Write 250-350 words covering:
- Revenue and profitability trends
- Debt structure and leverage
- Cash flow adequacy
- Key financial ratios analysis
- Comparison with industry benchmarks (if available)

Use specific numbers from the data. Write in formal banking language.
"""

CAM_INDUSTRY_OUTLOOK_PROMPT = """You are a credit analyst writing a Credit Appraisal Memo (CAM).

Write a professional **Industry Outlook** section for:

**Sector:** {sector}
**Research Findings:** {research_info}

Write 150-250 words covering:
- Current industry trends
- Growth prospects
- Key risks and challenges
- Regulatory environment
- Competitive landscape

Write in formal banking language. Only use provided information.
"""

CAM_RISK_ASSESSMENT_PROMPT = """You are a credit analyst writing a Credit Appraisal Memo (CAM).

Write a professional **Risk Assessment** section for:

**Company:** {company_name}
**Risk Analysis:**
{risk_analysis}
**Financial Metrics:**
{financial_metrics}
**Research Signals:**
{research_signals}

Write 200-300 words covering:
- Overall risk profile
- Credit risk factors
- Market and operational risks
- Mitigation measures available
- Risk-reward evaluation

Write in formal banking language.
"""

CAM_RECOMMENDATION_PROMPT = """You are a senior credit committee member at an Indian bank.

Based on the following comprehensive analysis, provide a **Lending Recommendation**.

**Company:** {company_name}
**Sector:** {sector}
**Loan Amount Requested:** {loan_amount} INR

**Risk Analysis:**
{risk_analysis}

**Financial Metrics:**
{financial_metrics}

**Research Signals:**
{research_signals}

**Due Diligence Notes:**
{due_diligence_notes}

**Provide your recommendation in the following JSON format:**
{{
    "decision": "APPROVE" or "REJECT" or "CONDITIONAL_APPROVE",
    "suggested_loan_limit": <amount in INR or null>,
    "suggested_interest_rate": <percentage or null>,
    "explanation": "<detailed 200-word explanation of the decision>",
    "conditions": ["<condition1>", "<condition2>", ...]
}}

**Decision Guidelines:**
- APPROVE: Risk score < 40, strong financials, no major red flags
- CONDITIONAL_APPROVE: Risk score 40-65, acceptable with conditions
- REJECT: Risk score > 65, significant red flags, weak financials

**Interest Rate Guidelines (based on risk grade):**
- AAA-AA: 8.5% - 10%
- A-BBB: 10% - 13%
- BB-B: 13% - 16%
- Below B: Reject or 16%+

Respond ONLY in valid JSON.
"""
# ─── Research Agent Prompts ───────────────────────────────────────────────────

SIGNAL_EXTRACTION_PROMPT = """You are a corporate credit intelligence analyst.

Analyze the following news snippets and search results about **{company_name}** ({sector}).

**Articles / Snippets:**
{snippets}

**Your task:**
Extract structured risk signals and highlights from the text. 

**Priority 1: Company-Specific Highlights**
- Focus on {company_name}'s specific performance: deposit growth, loan growth, branch expansion, digital adoption, new products, or strategic hires.
- AVOID general sector news (e.g., "The Indian banking sector is growing") unless it explicitly links to {company_name}.

**Priority 2: Risk Signals**
Extract risk signals in these categories:
- promoter_controversy (CRITICAL: focus on fraud, debarment, or integrity issues of promoters/directors),
- fraud, litigation, regulatory_penalty, debt_restructuring, insolvency_filing, sector_slowdown.

For each signal:
- type: category above
- severity: "low", "medium", or "high"
- description: one-sentence summary
- source: snippet source name
- date: YYYY-MM or YYYY

**Respond ONLY in valid JSON:**
{{
    "signals": [
        {{
            "type": "<category>",
            "severity": "<low|medium|high>",
            "description": "<one-sentence summary>",
            "source": "<source name or null>",
            "date": "<date or null>"
        }}
    ],
    "positive_highlights": ["<specific positive finding about {company_name}>"],
    "negative_highlights": ["<specific negative finding about {company_name}>"]
}}
"""

PROMOTER_ANALYSIS_PROMPT = """You are a senior due diligence investigator.
Analyze these snippets regarding the promoters of **{company_name}**.

**Snippets:**
{snippets}

**Task:**
1. Evaluate reputation, track record, and previous associations.
2. Identify specific controversies or regulatory flags.
3. Assign a **Promoter Reputation Score** (0-100). 
   - 90-100: Pristine, global reputation, no flags.
   - 70-80: Strong record, minor historical noise.
   - 50-60: Mixed record or limited history.
   - Below 40: Significant controversies, penalties, or criminal investigations.

**Respond in JSON:**
{{
    "promoter_reputation_score": <number>,
    "controversies": ["<controversy 1>", ...],
    "previous_companies": ["<company 1>", ...],
    "risk_level": "<low|moderate|high>",
    "summary": "<formal 150-word investigative summary>"
}}
"""

SECTOR_ANALYSIS_PROMPT = """You are a sector specialist analyst.
Analyze snippets about the **{sector}** sector in India.

**Snippets:**
{snippets}

**Task:**
Identify industry headwinds, tailwinds, and specific regulatory risks relevant to a lender.

**Respond in JSON:**
{{
    "sector_outlook": "<positive|moderate|negative>",
    "regulatory_risk": "<low|medium|high>",
    "industry_headwinds": ["<headwind 1>", ...],
    "industry_tailwinds": ["<tailwind 1>", ...],
    "summary": "<formal 150-word sector overview>"
}}
"""
