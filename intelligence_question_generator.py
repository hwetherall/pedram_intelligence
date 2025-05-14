# intelligence_question_generator.py
# intelligence_question_generator.py
# ... (other imports like os, json, etc.)
try:
    import reporting # Or: from reporting import create_final_report
    REPORTING_MODULE_AVAILABLE = True
except ImportError:
    REPORTING_MODULE_AVAILABLE = False
    print("Warning: reporting.py module not found. Final report generation will be skipped.")

# ... (rest of your script) ...
import os
import json
import time
import re # Still useful for initial cleanup if LLM adds non-JSON text
import pdfplumber
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Test mode - when True, only uses a subset of LLMs
TEST_MODE = False # Set to False to use all LLMs

# List of LLM models to use for generating questions
LLM_MODELS_FULL = [
    "openai/o1-mini",
    "anthropic/claude-3.7-sonnet",
    "google/gemini-2.5-flash-preview",
    "x-ai/grok-3-beta",
    "deepseek/deepseek-chat-v3-0324",
    "arcee-ai/maestro-reasoning",
    "qwen/qwq-32b",
    "perplexity/sonar-reasoning-pro",
    "meta-llama/llama-4-maverick",
    "mistralai/mistral-medium-3"
]

# Models to use in test mode - just 2 models for faster testing
TEST_LLM_MODELS = [
    "meta-llama/llama-4-maverick",
    "qwen/qwq-32b"
]

# High-reasoning model for consolidation, risk assessment, and de-risking
# Claude 3.5 Sonnet is a great choice here, or Opus if budget allows
HIGH_REASONING_MODEL = "anthropic/claude-3.7-sonnet:thinking"
# Fallback if Sonnet 3.5 is not available via OpenRouter or for cost:
# HIGH_REASONING_MODEL = "anthropic/claude-3-sonnet-20240229"


# --- Helper Functions ---

def extract_text_from_pdf(pdf_path):
    """Extract text content from a PDF file."""
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at path: {pdf_path}")
        return ""
        
    try:
        text_content = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_content += text + "\n\n"
        if not text_content.strip():
            print(f"Warning: No text content extracted from PDF {pdf_path}")
        return text_content.strip()
    except Exception as e:
        print(f"Error extracting text from PDF {pdf_path}: {str(e)}")
        return ""

def validate_openrouter_api_key():
    """Check if OpenRouter API key is available."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: OpenRouter API key not found in environment variables.")
        print("Please create a .env file with OPENROUTER_API_KEY=your_api_key_here")
        return False
    return True

def call_openrouter_api(model, prompt_messages, temperature=0.5, max_tokens_override=2048, is_json_output=False):
    """
    Call the OpenRouter API.
    Args:
        model (str): The OpenRouter model identifier.
        prompt_messages (list): List of message objects (e.g., [{"role": "user", "content": "..."}]).
        temperature (float): Sampling temperature.
        max_tokens_override (int): Max tokens for the response.
        is_json_output (bool): If True, will add a system message to request JSON (for some models).
    Returns:
        dict: The API response data or None on failure.
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("OPENROUTER_REFERRER", "http://localhost:8501"), # Get from .env or default
        "X-Title": os.getenv("OPENROUTER_X_TITLE", "Intelligence Questions App") # Get from .env or default
    }

    # Some models benefit from an explicit instruction in the messages to output JSON
    # when using response_format feature.
    # For others, simply setting response_format is enough.
    # We'll rely on the prompt itself instructing JSON format.
    payload = {
        "model": model,
        "messages": prompt_messages,
        "temperature": temperature,
        "max_tokens": max_tokens_override
    }
    # For models that support it, explicitly ask for JSON object output
    # This is more reliable than just parsing. Check OpenRouter model docs.
    # Example: OpenAI models support response_format={"type": "json_object"}
    if is_json_output and ("gpt" in model or "claude-3.5" in model or "claude-3-" in model): # Add other models if they support this
        payload["response_format"] = {"type": "json_object"}


    print(f"Calling OpenRouter API with model: {model}, Temperature: {temperature}, Max Tokens: {max_tokens_override}")
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=180 # Increased timeout for potentially long responses
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling OpenRouter API with model {model}: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status code: {e.response.status_code}")
            try:
                print(f"Response text: {e.response.text}")
            except Exception:
                print("Could not print response text.")
        return None

def parse_json_from_llm_response(response_content):
    """
    Safely parses JSON from LLM response content.
    Handles cases where LLM might wrap JSON in markdown ```json ... ```
    """
    if not response_content:
        return None
    
    # Try to find JSON block if markdown is used
    match = re.search(r"```json\s*([\s\S]*?)\s*```", response_content)
    if match:
        json_str = match.group(1)
    else:
        json_str = response_content

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Failed to decode JSON: {e}")
        print(f"Problematic JSON string (first 500 chars): {json_str[:500]}")
        return None

# --- Phase 1: Input Processing (Handled by Streamlit app mostly) ---
# `extract_text_from_pdf` is above.
# `get_user_input` from CLI is removed as Streamlit handles this.

# --- Phase 2: Generating PMS Questions ---

def create_pms_prompt(market_chapter, pitch_deck_text, market_report_text, context):
    """Create prompt for generating Point of Maximum Skepticism (PMS) questions."""
    # This prompt asks for line-separated questions, not JSON, to keep it simple for diverse models.
    # We will parse this line by line.
    return f"""Given the following documents:
1. Market Chapter: {market_chapter[:100000]} 
2. Pitch Deck: {pitch_deck_text[:150000]}
3. Market Report: {market_report_text[:150000]}

And the following context for evaluation:
Context: {context}

Please act as a highly intelligent and skeptical investor. Your goal is to identify potential weaknesses and critical risks SPECIFICALLY RELATED TO THE MARKET ASPECTS of this venture.

IMPORTANT: Focus ONLY on market-related questions. DO NOT ask about finances, team, operations, go-to-market strategy, or other non-market aspects.

Your questions should focus on:
- Market size, growth, and trends
- Competition and market positioning
- Market barriers and challenges
- Market adoption of the technology/solution
- Regulatory environment affecting the market
- How the venture specifically plays within this market
- Market-specific risks

Generate exactly 10 distinct questions that probe the "Point of Maximum Skepticism" (PMS) for the market aspects of the venture described.
The questions should highlight significant market-related risks or reasons the venture might face major challenges or fail due to market factors.

Output only the 10 questions, each on a new line. Do not include preambles, numbering, or any other text. Just the questions.
"""

def extract_questions_from_pms_response(response_content):
    """Extract 10 questions from the PMS API response content."""
    if not response_content:
        return [f"[Model failed to provide content]" for _ in range(10)]
    
    questions = [q.strip() for q in response_content.split('\n') if q.strip()]
    
    # Pad or truncate to ensure exactly 10 questions
    if len(questions) < 10:
        questions.extend([f"[Model provided fewer than 10 questions, placeholder {i+1}]" for i in range(len(questions), 10)])
    elif len(questions) > 10:
        questions = questions[:10]
    return questions

def generate_pms_questions(extracted_data):
    """Generate PMS questions using LLMs."""
    models_to_use = TEST_LLM_MODELS if TEST_MODE else LLM_MODELS_FULL
    
    mode_message = "TEST MODE" if TEST_MODE else "FULL MODE"
    print(f"\n--- Generating PMS Questions (Phase 2 - {mode_message}) ---\n")
    print(f"Using {len(models_to_use)} LLMs: {', '.join(models_to_use)}")
    
    prompt_text = create_pms_prompt(
        extracted_data["market_chapter"],
        extracted_data["pitch_deck_text"],
        extracted_data["market_report_text"],
        extracted_data["context"]
    )
    prompt_messages = [{"role": "user", "content": prompt_text}]
    
    results = {}
    for i, model in enumerate(models_to_use):
        print(f"Calling model {i+1}/{len(models_to_use)}: {model}...")
        # For PMS, temperature can be a bit higher to get diverse questions
        response_data = call_openrouter_api(model, prompt_messages, temperature=0.7, max_tokens_override=5024)
        
        if response_data and 'choices' in response_data and response_data['choices']:
            content = response_data['choices'][0]['message']['content']
            questions = extract_questions_from_pms_response(content)
            results[model] = questions
            print(f"  ✓ Generated {len(questions)} questions. Preview: \"{questions[0][:80]}...\"")
        else:
            print(f"  ✗ Failed to get response from model {model}")
            results[model] = [f"[Failed to generate question from model {model}]" for _ in range(10)]
        
        if i < len(models_to_use) - 1:
            print(f"  Waiting briefly before next model call...")
            time.sleep(3) # Increased sleep
    
    with open("pms_questions.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    total_questions = sum(len(q_list) for q_list in results.values())
    print(f"\nCompleted Phase 2: Generated {total_questions} PMS questions from {len(results)} models.")
    return results

# --- Phase 3: Consolidating Questions ---

def create_consolidation_prompt(all_pms_questions, company_context):
    """Create prompt for consolidating questions, requesting JSON output."""
    flat_questions = []
    for model, questions in all_pms_questions.items():
        for q_text in questions:
            if not q_text.startswith("[Failed") and not q_text.startswith("[Model provided fewer"):
                flat_questions.append(q_text)
    
    questions_text_numbered = "\n".join([f"{i+1}. {q}" for i, q in enumerate(flat_questions)])

    return f"""You are an expert investment analyst. You have been provided with a list of raw questions generated by various AI models about a venture.
Venture Context: {company_context}

Your task is to consolidate these raw questions into the **Top 5 most critical and insightful MARKET-FOCUSED intelligence questions**.

Follow these steps:
1.  **Understand Context & Focus:** All questions should strictly pertain to MARKET aspects (e.g., market size, competition, adoption, regulation impacting markets). Ignore questions about team, finance, operations, etc.
2.  **Thematic Grouping:** Identify recurring themes or areas of concern within the provided questions.
3.  **Synthesize & Select:** For each major theme, either craft a new, comprehensive "meta-question" or select the best-phrased, most impactful existing question that represents that theme.
4.  **Prioritize for Top 5:** From your synthesized/selected questions, determine the 5 most critical ones. Prioritize questions that highlight fundamental market-related risks or points of maximum skepticism.
5.  **Provide Reasoning:** For each of your final 5 questions, write a brief (1-2 sentences) justification explaining why this question is critical from a market perspective for this venture.

**Output Format:**
Return your response as a single, valid JSON object.
This JSON object should contain one key: "final_questions".
The value of "final_questions" should be a list of exactly 5 JSON objects.
Each object in the list must have the following keys:
- "question_number": (integer) The number of the question (1 through 5).
- "question_text": (string) The text of the final consolidated question.
- "reasoning": (string) Your justification for this question's criticality.

Example JSON structure:
{{
  "final_questions": [
    {{
      "question_number": 1,
      "question_text": "What is the true addressable market size considering realistic adoption rates and competitive pressures?",
      "reasoning": "This question challenges optimistic TAM projections and forces a realistic assessment of market penetration potential."
    }},
    // ... up to 5 questions
  ]
}}

Here are the raw questions to analyze:
{questions_text_numbered}

Ensure your entire output is ONLY the JSON object described.
"""

def consolidate_questions(pms_questions_data, extracted_data):
    """Consolidate questions using a high-reasoning model, expecting JSON."""
    print("\n--- Consolidating Questions (Phase 3) ---\n")
    
    prompt_text = create_consolidation_prompt(pms_questions_data, extracted_data["context"])
    prompt_messages = [{"role": "user", "content": prompt_text}]
    
    print(f"Calling high-reasoning model ({HIGH_REASONING_MODEL}) for consolidation...")
    response_data = call_openrouter_api(HIGH_REASONING_MODEL, prompt_messages, temperature=0.3, max_tokens_override=5048, is_json_output=True)
    
    final_questions_list = []
    if response_data and 'choices' in response_data and response_data['choices']:
        content = response_data['choices'][0]['message']['content']
        parsed_json = parse_json_from_llm_response(content)
        if parsed_json and "final_questions" in parsed_json and isinstance(parsed_json["final_questions"], list):
            final_questions_list = parsed_json["final_questions"]
            # Validate structure if needed
            print(f"  ✓ Successfully parsed {len(final_questions_list)} consolidated questions from JSON.")
        else:
            print("  ✗ Failed to parse JSON correctly or 'final_questions' key missing/invalid.")
            final_questions_list = [{"question_number": i+1, "question_text": "[Consolidation Error: Failed to parse]", "reasoning": "N/A"} for i in range(5)]
    else:
        print(f"  ✗ Failed to get response from {HIGH_REASONING_MODEL} for consolidation.")
        final_questions_list = [{"question_number": i+1, "question_text": "[Consolidation Error: No LLM response]", "reasoning": "N/A"} for i in range(5)]

    # Ensure we always have 5, even if with error messages
    if len(final_questions_list) < 5:
        for i in range(len(final_questions_list), 5):
            final_questions_list.append({
                "question_number": i + 1,
                "question_text": f"[Consolidation Error: Missing question {i+1}]",
                "reasoning": "[Error]"
            })
    elif len(final_questions_list) > 5:
        final_questions_list = final_questions_list[:5]


    print("\nFinal Consolidated Questions:")
    for q in final_questions_list:
        print(f"\nQuestion {q.get('question_number')}: {q.get('question_text')}")
        print(f"Reasoning: {q.get('reasoning')}")
        
    with open("final_questions.json", "w", encoding="utf-8") as f:
        json.dump(final_questions_list, f, indent=2)
    
    print(f"\nCompleted Phase 3: Consolidated to {len(final_questions_list)} critical questions.")
    return final_questions_list

# --- Phase 4: Risk Assessment ---

def create_risk_assessment_prompt(final_questions_list, company_context):
    """Create prompt for risk assessment, requesting JSON output."""
    questions_for_prompt = ""
    for q in final_questions_list:
        questions_for_prompt += f"Question {q.get('question_number')}: {q.get('question_text')}\nReasoning for criticality: {q.get('reasoning')}\n\n"

    return f"""You are a senior risk analyst evaluating a venture.
Venture Context: {company_context}

For each of the following 5 critical market-focused questions, provide a risk assessment.
Your assessment for each question should include:
1.  **Risk Category:** A concise category for the risk (e.g., "Market Size & Growth Risk", "Competitive Landscape Risk", "Regulatory & Policy Risk", "Technology Adoption Risk", "Strategic Positioning Risk").
2.  **Probability Score (1-5):**
    1: Very Unlikely, 2: Unlikely, 3: Possible, 4: Likely, 5: Near Certainty
3.  **Impact Score (1-5):**
    1: Minimal, 2: Minor, 3: Moderate, 4: Major, 5: Catastrophic (threatens viability)
4.  **Risk Score (Calculated):** Multiply Probability by Impact (Score range 1-25).
5.  **Risk Tier (Calculated):**
    - High: 15-25
    - Medium: 8-14
    - Low: 1-7
6.  **Justification (2-3 sentences):** Explain your probability and impact scores, referencing the venture context and market dynamics.

**Output Format:**
Return your response as a single, valid JSON object.
This JSON object should contain one key: "risk_assessments".
The value of "risk_assessments" should be a list of exactly 5 JSON objects, one for each question assessed.
Each object in the list must have the following keys:
- "question_number": (integer) The original number of the question being assessed.
- "question_text": (string) The text of the question being assessed.
- "risk_category": (string) Your assigned risk category.
- "probability": (integer) Your probability score (1-5).
- "impact": (integer) Your impact score (1-5).
- "risk_score": (integer) Calculated as probability * impact.
- "risk_tier": (string) "High", "Medium", or "Low".
- "justification": (string) Your detailed justification.

Example for one assessed question:
{{
  "question_number": 1,
  "question_text": "What is the true addressable market size...?",
  "risk_category": "Market Size & Growth Risk",
  "probability": 4,
  "impact": 5,
  "risk_score": 20,
  "risk_tier": "High",
  "justification": "Overestimating TAM is common. If actual market is smaller, it severely impacts revenue potential and scalability."
}}

Here are the questions to assess:
{questions_for_prompt}

Ensure your entire output is ONLY the JSON object described.
"""

def perform_risk_assessment(final_questions_data, extracted_data):
    """Assess risks for final questions, expecting JSON output. Changed from assess_risks for Streamlit name."""
    print("\n--- Performing Risk Assessment (Phase 4) ---\n")
    
    prompt_text = create_risk_assessment_prompt(final_questions_data, extracted_data["context"])
    prompt_messages = [{"role": "user", "content": prompt_text}]
    
    print(f"Calling high-reasoning model ({HIGH_REASONING_MODEL}) for risk assessment...")
    response_data = call_openrouter_api(HIGH_REASONING_MODEL, prompt_messages, temperature=0.2, max_tokens_override=5000, is_json_output=True) # Low temp for factual assessment
    
    risk_assessment_list = []
    if response_data and 'choices' in response_data and response_data['choices']:
        content = response_data['choices'][0]['message']['content']
        parsed_json = parse_json_from_llm_response(content)
        if parsed_json and "risk_assessments" in parsed_json and isinstance(parsed_json["risk_assessments"], list):
            risk_assessment_list = parsed_json["risk_assessments"]
            # Add original question text to each risk item if LLM didn't include it (though prompt asks for it)
            for risk_item in risk_assessment_list:
                original_q = next((q for q in final_questions_data if q.get("question_number") == risk_item.get("question_number")), None)
                if original_q and "question_text" not in risk_item: # Or if it's empty
                    risk_item["question_text"] = original_q.get("question_text")
            print(f"  ✓ Successfully parsed {len(risk_assessment_list)} risk assessments from JSON.")
        else:
            print("  ✗ Failed to parse JSON correctly or 'risk_assessments' key missing/invalid.")
    else:
        print(f"  ✗ Failed to get response from {HIGH_REASONING_MODEL} for risk assessment.")

    # If parsing failed or list is incomplete, create placeholders
    if not risk_assessment_list or len(risk_assessment_list) != len(final_questions_data):
        risk_assessment_list = [] # Reset if partially parsed to avoid mixing
        for q_data in final_questions_data:
            risk_assessment_list.append({
                "question_number": q_data.get("question_number"),
                "question_text": q_data.get("question_text"),
                "risk_category": "[Assessment Error]",
                "probability": 0, "impact": 0, "risk_score": 0, "risk_tier": "Error",
                "justification": "Failed to get or parse assessment from LLM."
            })
    
    # Sort by risk_score descending for output and consistent handling
    risk_assessment_list.sort(key=lambda x: x.get("risk_score", 0), reverse=True)

    print("\nRisk Assessment Results (Sorted by Overall Risk Score):")
    # Display summary (can be enhanced in Streamlit)
    for i, risk in enumerate(risk_assessment_list):
        print(f"Rank {i+1}: Q{risk.get('question_number')} - {risk.get('risk_category')} (Score: {risk.get('risk_score')}, Tier: {risk.get('risk_tier')})")
        print(f"  P: {risk.get('probability')}, I: {risk.get('impact')}")
        print(f"  Justification: {risk.get('justification')}")
        
    with open("risk_assessment.json", "w", encoding="utf-8") as f:
        json.dump(risk_assessment_list, f, indent=2) # Save the list directly
    
    # For Streamlit, it expects a dict with a 'risks' key
    # This function will now return the list, Streamlit app will wrap it if needed or use list directly.
    # For consistency with your app.py, let's return the dict structure it expects.
    num_high = len([r for r in risk_assessment_list if r.get("risk_tier") == "High"])
    num_medium = len([r for r in risk_assessment_list if r.get("risk_tier") == "Medium"])
    num_low = len([r for r in risk_assessment_list if r.get("risk_tier") == "Low"])

    print(f"\nCompleted Phase 4: Risk Assessment. High: {num_high}, Medium: {num_medium}, Low: {num_low}.")
    return {
        "risks": risk_assessment_list,
        "summary_stats": {
            "high_risks": num_high,
            "medium_risks": num_medium,
            "low_risks": num_low,
            "total_risks_assessed": len(risk_assessment_list)
        }
    }

# --- Phase 5: De-risking Strategies ---

def create_derisking_prompt(risk_item, company_context, extracted_docs):
    """Create prompt for generating de-risking strategies, requesting JSON."""
    # Truncate for prompt safety, though you said full docs fit.
    # This ensures robustness if context window estimates are off or model changes.
    max_len = 7000 # Max chars per doc in prompt for de-risking
    market_chapter_excerpt = extracted_docs.get("market_chapter", "")[:max_len]
    pitch_deck_excerpt = extracted_docs.get("pitch_deck_text", "")[:max_len]
    market_report_excerpt = extracted_docs.get("market_report_text", "")[:max_len]

    return f"""You are a strategic advisor tasked with creating de-risking plans.
Venture Context: {company_context}

You are focusing on the following specific market risk:
Risk Details:
- Question Number: {risk_item.get('question_number')}
- Question Text: "{risk_item.get('question_text', 'N/A')}"
- Risk Category: {risk_item.get('risk_category', 'N/A')}
- Probability: {risk_item.get('probability', 'N/A')}/5
- Impact: {risk_item.get('impact', 'N/A')}/5
- Overall Risk Score: {risk_item.get('risk_score', 'N/A')}
- Justification for Risk: {risk_item.get('justification', 'N/A')}

Relevant Background Information (Excerpts from company documents):
Market Chapter Excerpt:
---
{market_chapter_excerpt}
---
Pitch Deck Excerpt:
---
{pitch_deck_excerpt}
---
Market Report Excerpt:
---
{market_report_excerpt}
---

**Your Task:**
For THIS SPECIFIC market risk, propose a de-risking plan. The plan should include strategies categorized under "Research," "Test," and "Act."
For each category, suggest 1-2 specific, actionable strategies. If a category is not highly relevant, provide a brief note or an N/A-like entry.

Each suggested strategy must include:
1.  `action_title`: A concise title (e.g., "Conduct Competitor Regulatory Timeline Analysis").
2.  `description`: A brief explanation of the action.
3.  `mitigation_effect`: How this action helps mitigate the risk (reduce probability or impact).
4.  `effort_level`: Qualitative assessment (e.g., "Low", "Medium (Cost & Time)", "High (Strategic Shift)").
5.  `potential_challenges` (optional): Brief note on potential difficulties.

**Output Format:**
Return your response as a single, valid JSON object. This object should represent the de-risking plan for THIS ONE risk.
The JSON object must have a key "de_risking_plan".
The value of "de_risking_plan" should be an object with three keys: "research_strategies", "test_strategies", and "act_strategies".
Each of these three keys should map to a list of strategy objects (as described above).

Example for the "de_risking_plan" structure:
{{
  "de_risking_plan": {{
    "research_strategies": [
      {{
        "action_title": "Example Research", "description": "...", "mitigation_effect": "...", "effort_level": "Low", "potential_challenges": "..."
      }}
    ],
    "test_strategies": [ /* list of test strategy objects */ ],
    "act_strategies": [ /* list of act strategy objects */ ]
  }}
}}

Focus on practical, market-oriented strategies grounded in the provided context and documents.
Ensure your entire output is ONLY the JSON object described.
"""

def develop_derisking_strategies(risk_assessment_list, extracted_data, company_context):
    """Develops de-risking strategies for high-priority risks, expecting JSON."""
    print("\n--- Developing De-risking Strategies (Phase 5) ---\n")

    # risk_assessment_list is already sorted by risk_score descending from perform_risk_assessment
    
    # Define criteria for "high-priority"
    # Let's take risks with score >= 15 (High tier), up to a maximum of 3 risks.
    high_priority_risks = [r for r in risk_assessment_list if r.get("risk_score", 0) >= 15][:3]

    if not high_priority_risks:
        print("No high-priority risks (Score >= 15) identified for de-risking strategy development.")
        # Return the original list, but ensure all items have a placeholder for de_risking_plan
        for r_item in risk_assessment_list:
            if "de_risking_plan" not in r_item:
                 r_item["de_risking_plan"] = {"status": "Not high priority for strategy generation"}
        return risk_assessment_list

    print(f"Identified {len(high_priority_risks)} high-priority risks for strategy development.")

    # Create a new list to store risks with (potentially) added strategies
    # This ensures we don't modify the input list directly if it's used elsewhere
    updated_risks_with_strategies = [dict(r) for r in risk_assessment_list]


    for risk_item_dict in updated_risks_with_strategies:
        # Check if current risk_item_dict (by question_number) is in our high_priority_risks list
        is_high_priority = any(hp_risk.get("question_number") == risk_item_dict.get("question_number") for hp_risk in high_priority_risks)

        if is_high_priority:
            print(f"\nDeveloping strategies for Risk (Q {risk_item_dict.get('question_number')}, Score: {risk_item_dict.get('risk_score')})...")
            
            # Use the specific risk_item_dict for prompting, as it's from the updated_risks_with_strategies list
            prompt_text = create_derisking_prompt(risk_item_dict, company_context, extracted_data)
            prompt_messages = [{"role": "user", "content": prompt_text}]
            
            # Temperature can be higher for creative strategy generation
            response_data = call_openrouter_api(HIGH_REASONING_MODEL, prompt_messages, temperature=0.6, max_tokens_override=5000, is_json_output=True)
            
            if response_data and 'choices' in response_data and response_data['choices']:
                content = response_data['choices'][0]['message']['content']
                parsed_json = parse_json_from_llm_response(content)
                if parsed_json and "de_risking_plan" in parsed_json:
                    risk_item_dict["de_risking_plan"] = parsed_json["de_risking_plan"]
                    print(f"  ✓ Successfully generated de-risking plan.")
                else:
                    print(f"  ✗ Failed to parse JSON or 'de_risking_plan' key missing.")
                    risk_item_dict["de_risking_plan"] = {"error": "Failed to parse strategies from LLM.", "raw_response_snippet": content[:200]}
            else:
                print(f"  ✗ Failed to get response from {HIGH_REASONING_MODEL} for de-risking.")
                risk_item_dict["de_risking_plan"] = {"error": "No LLM response for strategies."}
            
            time.sleep(3) # Delay between LLM calls for strategy generation
        else:
            # For risks not meeting high-priority, add a note.
            if "de_risking_plan" not in risk_item_dict: # Avoid overwriting if already processed (e.g., from a previous run)
                risk_item_dict["de_risking_plan"] = {"status": "Not high priority for strategy generation this run"}


    output_filename = "detailed_risk_report_with_strategies.json"
    print(f"\nSaving detailed risk report with strategies to '{output_filename}'...")
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(updated_risks_with_strategies, f, indent=2)
            
    num_processed_for_strategies = len([r for r in updated_risks_with_strategies if isinstance(r.get("de_risking_plan"), dict) and "error" not in r["de_risking_plan"] and "status" not in r["de_risking_plan"]])
    print(f"\nCompleted Phase 5: Developed de-risking strategies for {num_processed_for_strategies} high-priority risks.")
    return updated_risks_with_strategies


# --- Main Execution (for CLI testing) ---
def main_cli():
    """Main CLI execution function."""
    if not validate_openrouter_api_key():
        return

    print("\n*** Intelligence Questions Generator CLI ***")
    if TEST_MODE:
        print("*** RUNNING IN TEST MODE ***")
        print("Using only 2 LLMs instead of all 10 for faster testing.")
        print(f"Test LLMs: {', '.join(TEST_LLM_MODELS)}")

    # --- Phase 1: Inputs (Simplified for CLI) ---
    print("\n--- Intelligence Questions Generator ---")
    
    # Updated paths for Hayden's system
    market_chapter_path = r"C:\Users\hweth\OneDrive\Desktop\Innovera\Logo Project\pedram_intelligence\marketchapter.txt"
    pitch_deck_path = r"C:\Users\hweth\OneDrive\Desktop\Innovera\Logo Project\pedram_intelligence\pitch_deck.pdf"
    market_report_path = r"C:\Users\hweth\OneDrive\Desktop\Innovera\Logo Project\pedram_intelligence\market_report.pdf"

    try:
        with open(market_chapter_path, 'r', encoding='utf-8') as f:
            mc_text = f.read()
            print(f"Successfully read Market Chapter from {market_chapter_path}")
    except FileNotFoundError:
        print(f"Error reading Market Chapter file: [Errno 2] No such file or directory: '{market_chapter_path}'")
        mc_text = "Default market chapter text if file not found."
        print("Using placeholder text instead.")

    # Read PDF files
    pd_text = extract_text_from_pdf(pitch_deck_path) 
    if pd_text:
        print(f"Successfully read Pitch Deck from {pitch_deck_path}")
    else:
        print(f"Error reading Pitch Deck file: {pitch_deck_path}")
        pd_text = "Placeholder pitch deck text."
        print("Using placeholder text instead.")
        
    mr_text = extract_text_from_pdf(market_report_path)
    if mr_text:
        print(f"Successfully read Market Report from {market_report_path}")
    else:
        print(f"Error reading Market Report file: {market_report_path}")
        mr_text = "Placeholder market report text."
        print("Using placeholder text instead.")
    
    company_context_cli = input("Enter company context (e.g., 'I am an investor in a USA based Nuclear Power Generating Startup that is pre-revenue and Series'): ").strip()
    if not company_context_cli:
        company_context_cli = "Test Venture: AI for climate change mitigation, pre-seed."

    extracted_data_cli = {
        "market_chapter": mc_text,
        "pitch_deck_text": pd_text,
        "market_report_text": mr_text,
        "context": company_context_cli
    }
    with open("extracted_data.json", "w", encoding="utf-8") as f:
        json.dump(extracted_data_cli, f, indent=2)
    print("Input data prepared and saved to extracted_data.json.")

    # --- Phase 2: Generate PMS Questions ---
    pms_questions_cli = None
    if input("Run Phase 2 (Generate PMS Questions)? (y/n): ").lower() == 'y':
        pms_questions_cli = generate_pms_questions(extracted_data_cli)
    elif os.path.exists("pms_questions.json"):
        if input("Load existing pms_questions.json? (y/n): ").lower() == 'y':
            with open("pms_questions.json", "r", encoding="utf-8") as f:
                pms_questions_cli = json.load(f)
            print("Loaded PMS questions from file.")
    
    if not pms_questions_cli:
        print("Skipping subsequent phases as PMS questions are not available.")
        return

    # --- Phase 3: Consolidate Questions ---
    final_questions_cli = None
    if input("Run Phase 3 (Consolidate Questions)? (y/n): ").lower() == 'y':
        final_questions_cli = consolidate_questions(pms_questions_cli, extracted_data_cli)
    elif os.path.exists("final_questions.json"):
         if input("Load existing final_questions.json? (y/n): ").lower() == 'y':
            with open("final_questions.json", "r", encoding="utf-8") as f:
                final_questions_cli = json.load(f)
            print("Loaded final questions from file.")

    if not final_questions_cli:
        print("Skipping subsequent phases as final questions are not available.")
        return

    # --- Phase 4: Risk Assessment ---
    risk_assessment_output_cli = None # This will be the dict {"risks": [...], "summary_stats": ...}
    if input("Run Phase 4 (Risk Assessment)? (y/n): ").lower() == 'y':
        risk_assessment_output_cli = perform_risk_assessment(final_questions_cli, extracted_data_cli)
    elif os.path.exists("risk_assessment.json"):
        if input("Load existing risk_assessment.json? (y/n): ").lower() == 'y':
            with open("risk_assessment.json", "r", encoding="utf-8") as f:
                # Assuming risk_assessment.json stores the list of risks directly
                loaded_risks = json.load(f)
                # Reconstruct the dict structure perform_risk_assessment would return
                risk_assessment_output_cli = {
                    "risks": loaded_risks,
                    "summary_stats": { # Calculate or estimate stats if loading raw list
                        "high_risks": len([r for r in loaded_risks if r.get("risk_tier") == "High"]),
                        "medium_risks": len([r for r in loaded_risks if r.get("risk_tier") == "Medium"]),
                        "low_risks": len([r for r in loaded_risks if r.get("risk_tier") == "Low"]),
                        "total_risks_assessed": len(loaded_risks)
                    }
                }
            print("Loaded risk assessment from file.")

    if not risk_assessment_output_cli or "risks" not in risk_assessment_output_cli or not risk_assessment_output_cli["risks"]:
        print("Skipping subsequent phases as risk assessment is not available.")
        return

    # --- Phase 5: De-risking Strategies ---
    if input("Run Phase 5 (Develop De-risking Strategies)? (y/n): ").lower() == 'y':
        # develop_derisking_strategies expects a list of risk dicts
        develop_derisking_strategies(risk_assessment_output_cli["risks"], extracted_data_cli, extracted_data_cli["context"])
    elif os.path.exists("detailed_risk_report_with_strategies.json"):
        print("Found existing detailed_risk_report_with_strategies.json. CLI run complete.")


    print("\nCLI Workflow complete!")


# ... (all your existing code up to and including the main_cli() function) ...
# --- Phase 6: Strategic Reflection (I Like, I Wish, I Wonder) ---

def create_strategic_reflection_prompt(company_context, final_questions, risk_assessment_summary, derisking_summary_text, extracted_docs):
    """
    Create the prompt for the 'I Like, I Wish, I Wonder' strategic reflection.
    """
    # Summarize key inputs for the prompt to keep it focused
    # For extracted_docs, we can send snippets or rely on the LLM to pick relevant parts if it's the full text.
    # Given the context window, sending relevant snippets is safer.
    max_doc_snippet_len = 2000 # Max characters per document snippet in this prompt
    
    market_chapter_snippet = extracted_docs.get("market_chapter", "")[:max_doc_snippet_len]
    pitch_deck_snippet = extracted_docs.get("pitch_deck_text", "")[:max_doc_snippet_len]
    market_report_snippet = extracted_docs.get("market_report_text", "")[:max_doc_snippet_len]

    final_questions_text = ""
    if final_questions and isinstance(final_questions, list):
        for i, q in enumerate(final_questions[:5]): # Max 5 questions
            final_questions_text += f"  {i+1}. {q.get('question_text', 'N/A')} (Reasoning: {q.get('reasoning', 'N/A')})\n"
    else:
        final_questions_text = "No final questions provided for summary.\n"

    risk_summary_text = ""
    if risk_assessment_summary and isinstance(risk_assessment_summary.get("risks"), list):
        # Summarize top 2-3 risks
        sorted_risks = sorted(risk_assessment_summary["risks"], key=lambda x: x.get("risk_score", 0), reverse=True)
        for i, r in enumerate(sorted_risks[:3]): # Top 3 risks
            risk_summary_text += f"  - Risk {i+1}: {r.get('risk_category', 'N/A')} (Score: {r.get('risk_score', 'N/A')}, Tier: {r.get('risk_tier', 'N/A')}). Justification: {r.get('justification', 'N/A')[:150]}...\n" # Truncate justification
    else:
        risk_summary_text = "No risk assessment summary provided.\n"


    prompt = f"""You are a seasoned strategic advisor providing a final reflection on a comprehensive market risk analysis for a venture.

**Venture Context:**
{company_context}

**Summary of Analysis Performed:**
The venture's market position has been analyzed based on its market chapter, pitch deck, and a market report. This led to the identification of 5 critical market-focused questions, which were then assessed for risk. De-risking strategies have also been considered for the highest priority risks.

**Key Findings Recap (for your reference):**
*   **Original Document Snippets:**
    *   Market Chapter Snippet: "{market_chapter_snippet}..."
    *   Pitch Deck Snippet: "{pitch_deck_snippet}..."
    *   Market Report Snippet: "{market_report_snippet}..."
*   **Critical Questions Identified:**
{final_questions_text}
*   **Top Identified Risks (Summary):**
{risk_summary_text}
*   **General De-risking Themes Explored:** {derisking_summary_text}

**Your Task: Strategic Reflection (I Like, I Wish, I Wonder)**
Based on all the preceding analysis, provide a holistic strategic reflection using the "I Like, I Wish, I Wonder" framework. Frame your outputs primarily as insightful questions or actionable wonderings that the venture's leadership should consider. Aim for 2-3 points per category.

*   **I Like (Strengths & Opportunities to Build Upon):**
    Identify core market-related strengths, unique advantages, or significant opportunities that have emerged or been reinforced. Phrase these as questions that prompt further leverage.
    *Example: "Given our confirmed unique positioning in industrial heat, how can we further solidify this moat against emerging competitors?"*

*   **I Wish (Strategic Gaps & Desired Shifts):**
    Identify significant strategic gaps, areas needing a fundamental rethink, or desired shifts in market approach. Phrase these as questions that challenge current assumptions or propose a new direction.
    *Example: "Considering the persistent uncertainty in regulatory timelines, what would a robust contingency plan for a 2-year delay look like?"*

*   **I Wonder (Pivotal Uncertainties & Future Explorations):**
    Pose high-level, open-ended "what if" questions or identify pivotal market-related uncertainties crucial for long-term success that warrant ongoing strategic monitoring or deeper future exploration.
    *Example: "I wonder, if green hydrogen production costs plummet unexpectedly, how fundamentally does that alter our value proposition for industrial clients?"*

**Output Format:**
Return your response as a single, valid JSON object.
This JSON object must have three keys: "i_like_reflection", "i_wish_reflection", and "i_wonder_reflection".
Each key should map to a list of strings, where each string is an insightful question or statement as described above.

Example structure:
{{
  "i_like_reflection": [
    "Given [observed strength], how might we further amplify this advantage in our next funding round narrative?",
    "How can we best leverage the [identified opportunity] to accelerate early customer acquisition?"
  ],
  "i_wish_reflection": [
    "If [critical assumption challenged by risk assessment] proves incorrect, what is our Plan B for market entry?",
    "What bold strategic partnership, previously unconsidered, might address the [identified strategic gap]?"
  ],
  "i_wonder_reflection": [
    "What if a disruptive technology not currently on our radar emerges in the [adjacent market], how would that impact our long-term competitive landscape?",
    "To what extent could a significant geopolitical shift in [region] unexpectedly open up (or close down) key market opportunities for us?"
  ]
}}

Ensure your reflections are strategic, forward-looking, and directly informed by the preceding analytical phases. Focus on market aspects.
Your entire output must be ONLY the JSON object described.
"""
    return prompt

def perform_strategic_reflection(company_context, final_questions_data, risk_assessment_data, derisking_data, extracted_data):
    """
    Performs the 'I Like, I Wish, I Wonder' strategic reflection.
    Args:
        company_context (str): The venture's context.
        final_questions_data (list): List of final consolidated questions.
        risk_assessment_data (dict): Output from perform_risk_assessment (contains 'risks' list and 'summary_stats').
        derisking_data (list): List of risks with their de-risking plans (output from develop_derisking_strategies).
        extracted_data (dict): Original extracted documents.
    Returns:
        dict: A dictionary containing the 'I Like, I Wish, I Wonder' reflections, or None on failure.
    """
    print("\n--- Performing Strategic Reflection (Phase 6: I Like, I Wish, I Wonder) ---\n")

    # Prepare a summary of de-risking themes
    derisking_summary_text = "De-risking strategies were developed for high-priority risks, focusing on "
    themes = set()
    if derisking_data and isinstance(derisking_data, list):
        for risk_item in derisking_data:
            plan = risk_item.get("de_risking_plan")
            if plan and isinstance(plan, dict) and "error" not in plan and "status" not in plan:
                if plan.get("research_strategies"): themes.add("further market research and validation")
                if plan.get("test_strategies"): themes.add("pilot programs and hypothesis testing")
                if plan.get("act_strategies"): themes.add("strategic partnerships and policy engagement")
    if themes:
        derisking_summary_text += ", ".join(list(themes)) + "."
    else:
        derisking_summary_text = "De-risking strategies for high-priority risks were considered (details not summarized here)."
        if not derisking_data: # If derisking phase was skipped entirely
             derisking_summary_text = "De-risking strategy development phase was not run or yielded no specific plans."


    prompt_text = create_strategic_reflection_prompt(
        company_context,
        final_questions_data,
        risk_assessment_data, # This is the dict {"risks": [...], "summary_stats": ...}
        derisking_summary_text,
        extracted_data
    )
    prompt_messages = [{"role": "user", "content": prompt_text}]

    print(f"Calling high-reasoning model ({HIGH_REASONING_MODEL}) for strategic reflection...")
    # Temperature can be slightly higher for reflective, strategic thinking
    response_data = call_openrouter_api(HIGH_REASONING_MODEL, prompt_messages, temperature=0.6, max_tokens_override=5048, is_json_output=True)

    strategic_reflection_output = None
    if response_data and 'choices' in response_data and response_data['choices']:
        content = response_data['choices'][0]['message']['content']
        parsed_json = parse_json_from_llm_response(content)
        if parsed_json and \
           "i_like_reflection" in parsed_json and \
           "i_wish_reflection" in parsed_json and \
           "i_wonder_reflection" in parsed_json:
            strategic_reflection_output = parsed_json
            print("  ✓ Successfully generated and parsed strategic reflection.")
            
            # Print the reflection for CLI
            print("\nStrategic Reflection Output:")
            if strategic_reflection_output.get("i_like_reflection"):
                print("\nI Like (Strengths & Opportunities to Build Upon):")
                for item in strategic_reflection_output["i_like_reflection"]: print(f"  - {item}")
            if strategic_reflection_output.get("i_wish_reflection"):
                print("\nI Wish (Strategic Gaps & Desired Shifts):")
                for item in strategic_reflection_output["i_wish_reflection"]: print(f"  - {item}")
            if strategic_reflection_output.get("i_wonder_reflection"):
                print("\nI Wonder (Pivotal Uncertainties & Future Explorations):")
                for item in strategic_reflection_output["i_wonder_reflection"]: print(f"  - {item}")
        else:
            print("  ✗ Failed to parse JSON correctly or required reflection keys missing.")
            print(f"  Raw LLM response snippet: {content[:500]}...")
    else:
        print(f"  ✗ Failed to get response from {HIGH_REASONING_MODEL} for strategic reflection.")

    if strategic_reflection_output:
        with open("strategic_reflection.json", "w", encoding="utf-8") as f:
            json.dump(strategic_reflection_output, f, indent=2)
        print("\nStrategic reflection saved to 'strategic_reflection.json'.")
    
    print("\nCompleted Phase 6: Strategic Reflection.")
    return strategic_reflection_output


# --- Main Execution (for CLI testing) ---
def main_cli():
    """Main CLI execution function."""
    if not validate_openrouter_api_key():
        return

    print("\n*** Intelligence Questions Generator CLI ***")
    if TEST_MODE:
        print("*** RUNNING IN TEST MODE ***")
        print("Using only 2 LLMs instead of all 10 for faster testing.")
        print(f"Test LLMs: {', '.join(TEST_LLM_MODELS)}")
    else:
        print("*** RUNNING IN FULL MODE ***")
        print(f"Using {len(LLM_MODELS_FULL)} LLMs for PMS generation.")


    # --- Phase 1: Inputs (Simplified for CLI) ---
    print("\n--- Intelligence Questions Generator ---")
    
    # Updated paths for Hayden's system (ensure these are correct)
    market_chapter_path = r"C:\Users\hweth\OneDrive\Desktop\Innovera\Logo Project\pedram_intelligence\marketchapter.txt"
    pitch_deck_path = r"C:\Users\hweth\OneDrive\Desktop\Innovera\Logo Project\pedram_intelligence\pitch_deck.pdf"
    market_report_path = r"C:\Users\hweth\OneDrive\Desktop\Innovera\Logo Project\pedram_intelligence\market_report.pdf"

    mc_text = ""
    try:
        with open(market_chapter_path, 'r', encoding='utf-8') as f:
            mc_text = f.read()
            print(f"Successfully read Market Chapter from {market_chapter_path}")
    except FileNotFoundError:
        print(f"Error reading Market Chapter file: [Errno 2] No such file or directory: '{market_chapter_path}'")
        mc_text = "Default market chapter text if file not found."
        print("Using placeholder text instead.")

    pd_text = extract_text_from_pdf(pitch_deck_path) 
    if pd_text:
        print(f"Successfully extracted text from Pitch Deck: {pitch_deck_path}")
    else:
        print(f"Warning/Error reading Pitch Deck file or no text extracted: {pitch_deck_path}")
        pd_text = "Placeholder pitch deck text."
        print("Using placeholder text instead.")
        
    mr_text = extract_text_from_pdf(market_report_path)
    if mr_text:
        print(f"Successfully extracted text from Market Report: {market_report_path}")
    else:
        print(f"Warning/Error reading Market Report file or no text extracted: {market_report_path}")
        mr_text = "Placeholder market report text."
        print("Using placeholder text instead.")
    
    company_context_cli = input("Enter company context (e.g., 'I am an investor in a USA based Nuclear Power Generating Startup that is pre-revenue and Series'): ").strip()
    if not company_context_cli:
        company_context_cli = "Test Venture: AI for climate change mitigation, pre-seed." # Default context

    extracted_data_cli = {
        "market_chapter": mc_text,
        "pitch_deck_text": pd_text,
        "market_report_text": mr_text,
        "context": company_context_cli
    }
    with open("extracted_data.json", "w", encoding="utf-8") as f:
        json.dump(extracted_data_cli, f, indent=2)
    print("Input data prepared and saved to extracted_data.json.")

    # Initialize variables for data passing between phases
    pms_questions_cli = None
    final_questions_cli = None
    risk_assessment_output_cli = None # This will be the dict {"risks": [...], "summary_stats": ...}
    derisking_strategies_cli = None # This will be the list of risks with de_risking_plan

    # --- Phase 2: Generate PMS Questions ---
    if input("\nRun Phase 2 (Generate PMS Questions)? (y/n): ").lower() == 'y':
        pms_questions_cli = generate_pms_questions(extracted_data_cli)
    elif os.path.exists("pms_questions.json"):
        if input("Load existing pms_questions.json? (y/n): ").lower() == 'y':
            try:
                with open("pms_questions.json", "r", encoding="utf-8") as f:
                    pms_questions_cli = json.load(f)
                print("Loaded PMS questions from file.")
            except Exception as e:
                print(f"Error loading pms_questions.json: {e}")
    
    if not pms_questions_cli:
        print("Skipping subsequent phases as PMS questions are not available.")
        return

    # --- Phase 3: Consolidate Questions ---
    if input("\nRun Phase 3 (Consolidate Questions)? (y/n): ").lower() == 'y':
        final_questions_cli = consolidate_questions(pms_questions_cli, extracted_data_cli)
    elif os.path.exists("final_questions.json"):
         if input("Load existing final_questions.json? (y/n): ").lower() == 'y':
            try:
                with open("final_questions.json", "r", encoding="utf-8") as f:
                    final_questions_cli = json.load(f)
                print("Loaded final questions from file.")
            except Exception as e:
                print(f"Error loading final_questions.json: {e}")


    if not final_questions_cli:
        print("Skipping subsequent phases as final questions are not available.")
        return

    # --- Phase 4: Risk Assessment ---
    if input("\nRun Phase 4 (Risk Assessment)? (y/n): ").lower() == 'y':
        risk_assessment_output_cli = perform_risk_assessment(final_questions_cli, extracted_data_cli)
    elif os.path.exists("risk_assessment.json"):
        if input("Load existing risk_assessment.json? (y/n): ").lower() == 'y':
            try:
                with open("risk_assessment.json", "r", encoding="utf-8") as f:
                    loaded_risks = json.load(f) # risk_assessment.json stores the list of risks
                risk_assessment_output_cli = {
                    "risks": loaded_risks,
                    "summary_stats": { 
                        "high_risks": len([r for r in loaded_risks if r.get("risk_tier") == "High"]),
                        "medium_risks": len([r for r in loaded_risks if r.get("risk_tier") == "Medium"]),
                        "low_risks": len([r for r in loaded_risks if r.get("risk_tier") == "Low"]),
                        "total_risks_assessed": len(loaded_risks)
                    }
                }
                print("Loaded risk assessment from file.")
            except Exception as e:
                print(f"Error loading risk_assessment.json: {e}")


    if not risk_assessment_output_cli or "risks" not in risk_assessment_output_cli or not risk_assessment_output_cli["risks"]:
        print("Skipping subsequent phases as risk assessment is not available.")
        return

    # --- Phase 5: De-risking Strategies ---
    if input("\nRun Phase 5 (Develop De-risking Strategies)? (y/n): ").lower() == 'y':
        derisking_strategies_cli = develop_derisking_strategies(
            risk_assessment_output_cli["risks"], 
            extracted_data_cli, 
            extracted_data_cli["context"]
        )
    elif os.path.exists("detailed_risk_report_with_strategies.json"):
        if input("Load existing detailed_risk_report_with_strategies.json? (y/n): ").lower() == 'y':
            try:
                with open("detailed_risk_report_with_strategies.json", "r", encoding="utf-8") as f:
                    derisking_strategies_cli = json.load(f)
                print("Loaded de-risking strategies from file.")
            except Exception as e:
                print(f"Error loading detailed_risk_report_with_strategies.json: {e}")
        else: # User chose not to load, but file exists
             print("Found existing detailed_risk_report_with_strategies.json, but not loaded by user choice.")
    # If derisking_strategies_cli is still None here, it means the phase wasn't run and no file was loaded.
    # This is fine for Phase 6, as it can handle missing de-risking data.

    # --- Phase 6: Strategic Reflection (I Like, I Wish, I Wonder) ---
    if input("\nRun Phase 6 (Strategic Reflection - I Like, I Wish, I Wonder)? (y/n): ").lower() == 'y':
        # Phase 6 needs: company_context, final_questions_data, risk_assessment_data (the dict),
        # derisking_data (the list from Phase 5), and extracted_data.
        perform_strategic_reflection(
            extracted_data_cli["context"],
            final_questions_cli,          # Loaded or generated in Phase 3
            risk_assessment_output_cli,   # Loaded or generated in Phase 4
            derisking_strategies_cli,     # Loaded or generated in Phase 5 (can be None)
            extracted_data_cli            # From Phase 1
        )
    elif os.path.exists("strategic_reflection.json"):
        print("Found existing strategic_reflection.json. CLI run complete.")


    print("\nCLI Workflow complete!")


if __name__ == "__main__":
    main_cli()