import json, os, time
from datetime import datetime
from typing import Generator
from groq import Groq
from dotenv import load_dotenv

from .tools import search, format_results
from .prompts import SYSTEM, next_query_prompt, synthesis_prompt
from .memo_schema import DDMemo
from .logging_utils import log_event

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def _llm(prompt: str) -> str:
    start = time.time()
    msg = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        max_tokens=1024,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt}
        ],
    )
    content = msg.choices[0].message.content.strip()
    log_event("groq_llm", prompt, len(content), (time.time() - start) * 1000,
               model="llama-3.1-8b-instant")
    return content

def run_agent(company: str, description: str, founder_linkedin: str) -> Generator[dict, None, None]:
    """
    Yields log events: {"type": "step"|"memo"|"error", "step": int, "query": str,
                        "results": str, "memo": DDMemo}
    """
    findings_log = []

    for step in range(1, 6):
        try:
            findings_so_far = "\n".join(
                f"Step {f['step']}: {f['query']} → {f['snippet']}"
                for f in findings_log
            )
            query = _llm(next_query_prompt(company, description, founder_linkedin,
                                           step, findings_so_far))
            results = search(query)
            formatted = format_results(results)
            snippet = formatted[:300]

            findings_log.append({"step": step, "query": query, "snippet": snippet,
                                  "full": formatted})
            yield {"type": "step", "step": step, "query": query, "results": formatted}

        except Exception as e:
            yield {"type": "error", "step": step, "message": str(e)}
            continue

    # Synthesis
    all_findings = "\n\n".join(
        f"[Step {f['step']}] Query: {f['query']}\nFindings:\n{f['full']}"
        for f in findings_log
    )
    try:
        raw = _llm(synthesis_prompt(company, description, all_findings))
        raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        memo = DDMemo(**json.loads(raw))

        session = {
            "company": company, "description": description,
            "founder_linkedin": founder_linkedin,
            "timestamp": datetime.utcnow().isoformat(),
            "findings": findings_log, "memo": memo.model_dump()
        }
        session_path = os.path.join(
            os.path.dirname(__file__), "..", "sessions",
            f"{company.replace(' ','_')}_{int(time.time())}.json"
        )
        with open(session_path, "w") as f:
            json.dump(session, f, indent=2)

        yield {"type": "memo", "memo": memo}

    except Exception as e:
        yield {"type": "error", "step": 6, "message": f"Synthesis failed: {e}"}