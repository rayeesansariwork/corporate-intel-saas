import httpx
import json
import logging
from app.config import settings

logger = logging.getLogger("LLMEngine")

class LLMEngine:
    async def analyze(self, company: str, scraped_data: dict, search_context: list) -> dict:
        logger.info(f"🤖 Starting LLM analysis for company: {company}")
        
        context_str = f"WEBSITE CONTENT:\n{scraped_data.get('raw_text', '')}\n\nEXTERNAL SEARCH CONTEXT:\n" + "\n".join(search_context)
        logger.debug(f"Context string length: {len(context_str)} characters")
        
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
            logger.info(f"📡 Sending request to Mistral API (model: {settings.MISTRAL_MODEL})")
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
                
                if resp.status_code != 200:
                    logger.error(f"❌ Mistral API error: {resp.status_code} - {resp.text}")
                    return {}
                    
                data = resp.json()
                content = data['choices'][0]['message']['content']
                parsed_result = json.loads(content)
                
                logger.info(
                    f"✅ LLM analysis complete for {company}. "
                    f"Found {len(parsed_result.get('key_people', []))} people, "
                    f"{len(parsed_result.get('services_offered', []))} services"
                )
                logger.debug(f"Full LLM response: {json.dumps(parsed_result, indent=2)}")
                
                return parsed_result
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse LLM JSON response: {e}", exc_info=True)
            return {}
        except httpx.TimeoutException as e:
            logger.error(f"⏱️ Mistral API timeout after 45s: {e}")
            return {}
        except httpx.HTTPError as e:
            logger.error(f"🚫 HTTP error calling Mistral API: {type(e).__name__} - {e}", exc_info=True)
            return {}
        except Exception as e:
            logger.error(f"❌ Unexpected LLM error: {type(e).__name__} - {e}", exc_info=True)
            return {}