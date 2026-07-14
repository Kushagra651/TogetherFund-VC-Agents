SYSTEM = """You are a VC due diligence analyst at Together Fund, an operator-led AI-first fund 
backed by Girish Mathrubootham (Freshworks) and Manav Garg (Eka Software). 
Be precise, skeptical, and evidence-based. Never hallucinate — if data is absent, say so."""

def next_query_prompt(company: str, description: str, founder_linkedin: str,
                      step: int, findings_so_far: str) -> str:
    return f"""Company: {company}
Description: {description}
Founder LinkedIn: {founder_linkedin}
Step: {step}/5
Findings so far:
{findings_so_far}

Based on the findings so far, generate ONE precise DuckDuckGo search query (max 8 words) 
to investigate next. Focus areas by step:
1 → competitors and market players
2 → funding rounds and investors
3 → founder background and credibility
4 → TAM/market size
5 → recent news, red flags, or traction signals

Respond with ONLY the search query string, nothing else."""

def synthesis_prompt(company: str, description: str, all_findings: str) -> str:
    return f"""Company: {company}
Description: {description}

All research findings:
{all_findings}

Write a structured due diligence memo as JSON with exactly these keys:
- market: 2-3 sentences on market size and opportunity
- competition: 2-3 sentences on competitive landscape
- founder: 2-3 sentences on founder credibility and background  
- traction: 2-3 sentences on traction signals found (or lack thereof)
- red_flags: 2-3 sentences on risks or concerns (say "None identified" if clean)
- verdict: 3-4 sentences with overall investment signal and reasoning
- confidence: one of "High", "Medium", or "Low" based on data availability
- sources: list of search queries used as evidence strings

Return ONLY valid JSON. No markdown, no explanation."""