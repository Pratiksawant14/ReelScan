def build_intent_prompt(analysis_text: str) -> str:
    return f"""You are an intent classifier for short-form video content.

Given the following detailed analysis of an Instagram Reel, determine:
1. The PRIMARY INTENT of this reel — what is the creator's main goal/topic?
2. The CONTENT CATEGORY it belongs to.

Return ONLY a valid JSON object, no explanation, no markdown, no backticks:

{{
  "primary_intent": "<one sentence describing what this reel is about from the creator's perspective>",
  "category": "<one of: recipe | tech_review | fashion_outfit | skincare_beauty | travel_location | fitness_workout | home_decor | product_unboxing | educational | entertainment | other>",
  "confidence": <0.0 to 1.0>,
  "intent_keywords": ["keyword1", "keyword2", "keyword3"]
}}

Reel Analysis:
{analysis_text}
"""

def build_entity_prompt(analysis_text: str, category: str, primary_intent: str) -> str:
    return f"""You are a smart product and entity extractor for short-form video content.

The following reel has been classified as: "{category}" — "{primary_intent}"

Based on this intent, extract ONLY the entities that are directly relevant to what this reel is about. Focus on what the CREATOR intended to show or discuss. Do NOT extract background items, incidental objects, or things unrelated to the reel's topic.

For each entity, extract as much detail as is visible or inferable from the analysis.

Return ONLY a valid JSON object, no explanation, no markdown, no backticks:

{{
  "intent_category": "{category}",
  "entities": [
    {{
      "id": "<unique string like 'ent_001'>",
      "name": "<specific name of item, be as precise as possible>",
      "brand": "<brand name if visible or mentioned, else null>",
      "type": "<product | ingredient | location | dish | service | person | concept>",
      "sub_category": "<e.g. tops | sneakers | earbuds | spice | hotel | skincare_serum | laptop>",
      "search_query": "<the best Amazon/Flipkart/Google search string to find this exact item>",
      "confidence": <0.0 to 1.0, how certain you are this entity is intentionally shown>,
      "source": "intent_extraction",
      "notes": "<any useful detail: color, size, model number, quantity if mentioned>"
    }}
  ],
  "extraction_summary": "<one sentence explaining what was extracted and why>"
}}

Reel Analysis:
{analysis_text}
"""
