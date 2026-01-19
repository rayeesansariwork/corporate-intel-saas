import httpx
import json
import logging
from app.config import settings

logger = logging.getLogger("LLMEngine")

class LLMEngine:
    async def analyze(self, company: str, scraped_data: dict, search_context: list) -> dict:
        
        context_str = f"WEBSITE CONTENT:\n{scraped_data.get('raw_text', '')}\n\nEXTERNAL SEARCH CONTEXT:\n" + "\n".join(search_context)
        
        prompt = f"""
        Analyze the company "{company}" based on the data below.
        
        DATA:
        {context_str[:20000]} 

        You must extract strict JSON:
        {{
            "company_profile": {{ "name": "{company}", "description": "...", "industry": "...", "hq_address": "...", "country": "...", "annual_revenue": "..." }},
            "services_offered": ["list of services"],
            "key_people": [{{ "name": "...", "role": "..." }}]
        }}
        
        If revenue or people are not explicitly found, write "Not Found".
        """

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                resp = await client.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.MISTRAL_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": settings.MISTRAL_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "response_format": {"type": "json_object"},
                        "temperature": 0.1
                    }
                )
                data = resp.json()
                content = data['choices'][0]['message']['content']
                return json.loads(content)
        except Exception as e:
            logger.error(f"LLM Error: {e}")
            return {}