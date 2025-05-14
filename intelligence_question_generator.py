import os
import json
import time
import pdfplumber
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Test mode - when True, only uses 2 LLMs instead of all 10
TEST_MODE = True

# List of LLM models to use for generating questions
LLM_MODELS = [
    "openai/o1-mini",
    "anthropic/claude-3.7-sonnet:thinking",
    "google/gemini-2.5-flash-preview:thinking",
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

# High-reasoning model for consolidation and refinement
HIGH_REASONING_MODEL = "anthropic/claude-3.7-sonnet:thinking"

def extract_text_from_pdf(pdf_path):
    """
    Extract text content from a PDF file.
    
    Args:
        pdf_path (str): Path to the PDF file
        
    Returns:
        str: Extracted text content from the PDF
    """
    try:
        text_content = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_content += text + "\n\n"
        return text_content.strip()
    except Exception as e:
        print(f"Error extracting text from PDF {pdf_path}: {str(e)}")
        return ""

# Replaced by the app.py interface
def get_user_input():
    """
    Get user inputs for the Market Chapter, Context, and PDF file paths.
    
    Returns:
        dict: Dictionary containing user inputs
    """
    print("\n--- Intelligence Questions Generator ---\n")
    
    # Hardcoded file paths
    market_chapter_path = r"C:\Users\felip\OneDrive\Área de Trabalho\Innovera\Pedram intelligence\pedram_intelligence\marketchapter.txt"
    pitch_deck_path = r"C:\Users\felip\OneDrive\Área de Trabalho\Innovera\Pedram intelligence\pedram_intelligence\pitch_deck.pdf"
    market_report_path = r"C:\Users\felip\OneDrive\Área de Trabalho\Innovera\Pedram intelligence\pedram_intelligence\market_report.pdf"
    
    # Read Market Chapter from file
    market_chapter_text = ""
    try:
        with open(market_chapter_path, 'r', encoding='utf-8') as f:
            market_chapter_text = f.read()
        print(f"Successfully loaded Market Chapter from {market_chapter_path}")
    except Exception as e:
        print(f"Error reading Market Chapter file: {str(e)}")
        return None
    
    # Get Context from user
    print("\nStep 1: Enter the Context information")
    print("(This is the framing for the company, e.g., 'Series C Investment for a Nuclear Power Generator Company that is pre-revenue')")
    context = input("Enter context: ").strip()
    
    # Validate PDF paths
    if not os.path.exists(pitch_deck_path):
        print(f"Error: Pitch Deck PDF not found at {pitch_deck_path}")
        return None
    else:
        print(f"Found Pitch Deck at {pitch_deck_path}")
        
    if not os.path.exists(market_report_path):
        print(f"Error: Market Report PDF not found at {market_report_path}")
        return None
    else:
        print(f"Found Market Report at {market_report_path}")
    
    return {
        "market_chapter": market_chapter_text,
        "context": context,
        "pitch_deck_path": pitch_deck_path,
        "market_report_path": market_report_path
    }

def validate_openrouter_api_key():
    """
    Check if OpenRouter API key is available in environment variables.
    
    Returns:
        bool: True if API key is available, False otherwise
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: OpenRouter API key not found in environment variables.")
        print("Please create a .env file in the project directory with the following content:")
        print("OPENROUTER_API_KEY=your_api_key_here")
        return False
    return True

def create_pms_prompt(market_chapter, pitch_deck_text, market_report_text, context):
    """
    Create the prompt for generating Point of Maximum Skepticism (PMS) questions.
    
    Args:
        market_chapter (str): The Market Chapter text
        pitch_deck_text (str): Extracted text from the Pitch Deck PDF
        market_report_text (str): Extracted text from the Market Report PDF
        context (str): The Context information provided by the user
        
    Returns:
        str: The formatted prompt for the LLMs
    """
    prompt = f"""Given the following documents:
1. Market Chapter: {market_chapter}

2. Pitch Deck: {pitch_deck_text}

3. Market Report (Nuclear Power): {market_report_text}

And the following context for evaluation:
Context: {context}

Please act as a highly intelligent and skeptical investor. Your goal is to identify potential weaknesses and critical risks SPECIFICALLY RELATED TO THE MARKET ASPECTS of this venture.

IMPORTANT: Focus ONLY on market-related questions. DO NOT ask about finances, team, operations, go-to-market strategy, or other non-market aspects. These will be addressed in separate sections.

Your questions should focus on:
- Market size, growth, and trends
- Competition and market positioning
- Market barriers and challenges
- Market adoption of the technology
- Regulatory environment affecting the market
- How X-Energy specifically plays within this market
- Market-specific risks

Generate exactly 10 distinct questions that probe the "Point of Maximum Skepticism" (PMS) for the market aspects of the venture described.
The questions should highlight significant market-related risks or reasons the venture might face major challenges or fail due to market factors.

Output only the 10 questions, each on a new line. Do not include preambles or any other text."""
    
    return prompt

def call_openrouter_api(model, prompt):
    """
    Call the OpenRouter API with the given model and prompt.
    
    Args:
        model (str): The OpenRouter model identifier
        prompt (str): The prompt to send to the model
        
    Returns:
        dict: The API response data
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://pedram-intelligence.com"  # Optional but helpful for tracking
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1024
    }
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload
        )
        response.raise_for_status()  # Raise an exception for 4XX/5XX responses
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling OpenRouter API with model {model}: {str(e)}")
        if hasattr(e, 'response') and e.response:
            print(f"Response status code: {e.response.status_code}")
            print(f"Response text: {e.response.text}")
        return None

def extract_questions_from_response(response):
    """
    Extract the 10 questions from the API response.
    
    Args:
        response (dict): The API response data
        
    Returns:
        list: List of extracted questions
    """
    if not response or 'choices' not in response or not response['choices']:
        return []
    
    # Extract the response content
    content = response['choices'][0]['message']['content'].strip()
    
    # Split by newlines and filter out empty lines
    questions = [q.strip() for q in content.split('\n') if q.strip()]
    
    # If the model didn't format as expected, try to extract questions
    if len(questions) != 10:
        # Look for numbered questions (1. Question, 2. Question, etc.)
        import re
        numbered_questions = re.findall(r'\d+[\.\)]\s*(.*?)(?=\n\d+[\.\)]|\Z)', content, re.DOTALL)
        if numbered_questions and len(numbered_questions) >= 10:
            questions = [q.strip() for q in numbered_questions[:10]]
        # If we still don't have 10 questions, just take first 10 lines or pad with placeholders
        if len(questions) < 10:
            if len(questions) == 0:
                questions = [f"[Model failed to generate question {i+1}]" for i in range(10)]
            else:
                questions.extend([f"[Model failed to generate question {i+1}]" for i in range(len(questions), 10)])
        elif len(questions) > 10:
            questions = questions[:10]
    
    return questions

def generate_pms_questions(extracted_data):
    """
    Generate Point of Maximum Skepticism (PMS) questions using LLMs.
    
    Args:
        extracted_data (dict): Dictionary containing the extracted data
        
    Returns:
        dict: Dictionary mapping model names to their generated questions
    """
    # Select which models to use based on test mode
    models_to_use = TEST_LLM_MODELS if TEST_MODE else LLM_MODELS
    
    # Display appropriate message based on mode
    if TEST_MODE:
        print("\n--- Generating PMS Questions (Phase 2 - TEST MODE) ---\n")
        print(f"Running in test mode with {len(models_to_use)} LLMs instead of all 10")
    else:
        print("\n--- Generating PMS Questions (Phase 2) ---\n")
    
    # Create the prompt
    prompt = create_pms_prompt(
        extracted_data["market_chapter"],
        extracted_data["pitch_deck_text"],
        extracted_data["market_report_text"],
        extracted_data["context"]
    )
    
    # Store results for each model
    results = {}
    
    # Call each LLM model
    for i, model in enumerate(models_to_use):
        print(f"Calling model {i+1}/{len(models_to_use)}: {model}...")
        
        # Call the API
        response = call_openrouter_api(model, prompt)
        
        if response:
            # Extract questions from the response
            questions = extract_questions_from_response(response)
            results[model] = questions
            
            # Print a preview of the questions
            print(f"  ✓ Generated {len(questions)} questions")
            print(f"  Preview: \"{questions[0][:100]}...\"")
        else:
            # Handle API call failure
            print(f"  ✗ Failed to get response from model")
            results[model] = [f"[Failed to generate question from model {model}]" for _ in range(10)]
        
        # Add a delay between API calls to avoid rate limiting
        if i < len(models_to_use) - 1:
            print(f"  Waiting before next model call...")
            time.sleep(2)
    
    # Save results to a file
    print("\nSaving generated questions to 'pms_questions.json'...")
    with open("pms_questions.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    total_questions = sum(len(questions) for questions in results.values())
    print(f"\nCompleted Phase 2: Generated {total_questions} questions from {len(results)} models")
    
    return results

def create_consolidation_prompt(all_questions):
    """
    Create the prompt for consolidating and refining the 100 questions.
    
    Args:
        all_questions (dict): Dictionary mapping model names to their generated questions
        
    Returns:
        str: The formatted prompt for the high-reasoning model
    """
    # Flatten all questions into a single list with numbers
    flat_questions = []
    for model, questions in all_questions.items():
        for question in questions:
            if not question.startswith("[Failed"):  # Skip placeholder questions
                flat_questions.append(question)
    
    # Format the questions as a numbered list
    questions_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(flat_questions)])
    
    prompt = f"""You have been provided with questions generated by various AI models. These questions concern a venture, focusing specifically on MARKET-RELATED aspects. Your task is to analyze these questions and produce a final, refined list of the top 5 most critical and insightful market-focused questions.

Follow these steps:
1. **Pattern Recognition & Thematic Grouping:** Read all the questions. Identify recurring themes or areas of concern related to markets (e.g., market size, competition, market barriers, regulatory environment affecting markets, market adoption). Group similar questions, even if phrased differently.
2. **Synthesize or Select Exemplars:** For each major market-focused theme you identify, either:
   a. Craft a new, comprehensive "meta-question" that captures the core concern of the grouped questions.
   b. Or, select the single best-phrased, most impactful question from a group to serve as an exemplar for that theme.
3. **Prioritize for Top 5:** From your synthesized/selected questions, determine the 5 most critical ones. Prioritize questions that highlight fundamental market-related risks or points of maximum skepticism about the market aspects.
4. **Provide Reasoning:** For each of your final 5 questions, write a brief explanation (1-2 sentences) justifying why this question is critical from a market perspective.

IMPORTANT: Focus ONLY on market-related questions. If you find questions about finances, team, operations, or other non-market aspects, ignore them for this analysis.

Output the results in the following format:

Question 1: [The text of the first final question]
Reasoning: [Your justification for this question]

Question 2: [The text of the second final question]
Reasoning: [Your justification for this question]

...and so on for all 5 questions.

Here are the questions to analyze:

{questions_text}"""
    
    return prompt

def extract_final_questions(response):
    """
    Extract the 5 final questions and their reasoning from the API response.
    
    Args:
        response (dict): The API response data
        
    Returns:
        list: List of dictionaries containing the final questions and their reasoning
    """
    if not response or 'choices' not in response or not response['choices']:
        return []
    
    # Extract the response content
    content = response['choices'][0]['message']['content'].strip()
    
    # Parse the final questions and reasoning
    import re
    
    # Look for "Question X:" followed by the question and "Reasoning:" followed by the reasoning
    pattern = r'Question\s+\d+:\s+(.*?)\s*\nReasoning:\s+(.*?)(?=\n\s*Question\s+\d+:|$)'
    matches = re.findall(pattern, content, re.DOTALL)
    
    final_questions = []
    for i, (question, reasoning) in enumerate(matches[:5]):  # Limit to 5 questions
        final_questions.append({
            "question": question.strip(),
            "reasoning": reasoning.strip(),
            "question_number": i + 1
        })
    
    # If we didn't get 5 questions, look for other formats or add placeholders
    if len(final_questions) < 5:
        print(f"Warning: Could only extract {len(final_questions)} questions from the response.")
        # Add placeholders for missing questions
        for i in range(len(final_questions), 5):
            final_questions.append({
                "question": f"[Failed to extract question {i+1}]",
                "reasoning": "[Failed to extract reasoning]",
                "question_number": i + 1
            })
    
    return final_questions

def consolidate_questions(all_questions):
    """
    Consolidate and refine the 100 questions into 5 critical questions using a high-reasoning model.
    
    Args:
        all_questions (dict): Dictionary mapping model names to their generated questions
        
    Returns:
        list: List of dictionaries containing the final questions and their reasoning
    """
    print("\n--- Consolidating Questions (Phase 3) ---\n")
    
    # Create the prompt
    prompt = create_consolidation_prompt(all_questions)
    
    print(f"Calling high-reasoning model ({HIGH_REASONING_MODEL}) to consolidate questions...")
    
    # Call the API
    response = call_openrouter_api(HIGH_REASONING_MODEL, prompt)
    
    if not response:
        print("Error: Failed to get response from high-reasoning model")
        return []
    
    # Extract the final questions
    final_questions = extract_final_questions(response)
    
    # Print the final questions
    print("\nFinal Consolidated Questions:")
    for q in final_questions:
        print(f"\nQuestion {q['question_number']}: {q['question']}")
        print(f"Reasoning: {q['reasoning']}")
    
    # Save results to a file
    print("\nSaving consolidated questions to 'final_questions.json'...")
    with open("final_questions.json", "w", encoding="utf-8") as f:
        json.dump(final_questions, f, indent=2)
    
    print(f"Completed Phase 3: Consolidated to {len(final_questions)} critical questions")
    
    return final_questions

def create_risk_assessment_prompt(final_questions):
    """
    Create the prompt for assessing risks based on the final questions.
    
    Args:
        final_questions (list): List of dictionaries containing the final questions and their reasoning
        
    Returns:
        str: The formatted prompt for the risk assessment
    """
    # Format questions and reasoning
    questions_text = ""
    for q in final_questions:
        questions_text += f"Question {q['question_number']}: {q['question']}\n"
        questions_text += f"Reasoning: {q['reasoning']}\n\n"
    
    prompt = f"""You are an expert risk analyst evaluating a nuclear power startup (X-Energy). I need you to assess and quantify the risks identified in these intelligence questions:

{questions_text}

For each of the 5 questions, please:

1. Identify and categorize the specific type of risk (e.g., Regulatory Risk, Supply Chain Risk, etc.)

2. Score each risk on:
   - Probability (1-5 scale, where 1 = Very Low, 5 = Very High)
   - Impact (1-5 scale, where 1 = Minimal, 5 = Severe)
   - Calculate an Overall Risk Score (Probability × Impact)
   - Classify the risk tier (Low: 1-6, Medium: 7-15, High: 16-25)

3. Provide a brief justification (2-3 sentences) for each scoring decision based on the information provided.

Format your response as a structured JSON object with the following schema:

```
{
  "risks": [
    {
      "question_number": 1,
      "risk_category": "Category name",
      "probability": 1-5,
      "impact": 1-5,
      "risk_score": calculated value,
      "risk_tier": "Low/Medium/High",
      "justification": "Your justification here"
    },
    ...additional risks...
  ]
}
```

Return ONLY valid JSON with no additional text, explanations, or markdown formatting.
"""
    
    return prompt

def extract_risk_assessment(response):
    """
    Extract the risk assessment from the API response.
    
    Args:
        response (dict): The API response data
        
    Returns:
        dict: Dictionary containing the risk assessment
    """
    if not response or 'choices' not in response or not response['choices']:
        return None
    
    # Extract the response content
    content = response['choices'][0]['message']['content'].strip()
    
    # Parse the JSON
    try:
        # Remove any markdown code block indicators if present
        if content.startswith("```json"):
            content = content.replace("```json", "", 1)
        if content.startswith("```"):
            content = content.replace("```", "", 1)
        if content.endswith("```"):
            content = content[:content.rfind("```")]
            
        # Parse the JSON
        risk_assessment = json.loads(content.strip())
        return risk_assessment
    except json.JSONDecodeError as e:
        print(f"Error parsing risk assessment JSON: {str(e)}")
        print(f"Response content: {content}")
        return None

def perform_risk_assessment(final_questions):
    """
    Perform risk assessment on the final questions.
    
    Args:
        final_questions (list): List of dictionaries containing the final questions and their reasoning
        
    Returns:
        dict: Dictionary containing the risk assessment
    """
    print("\n--- Performing Risk Assessment (Phase 4) ---\n")
    
    # Create the prompt
    prompt = create_risk_assessment_prompt(final_questions)
    
    print(f"Calling high-reasoning model ({HIGH_REASONING_MODEL}) to assess risks...")
    
    # Call the API
    response = call_openrouter_api(HIGH_REASONING_MODEL, prompt)
    
    if not response:
        print("Error: Failed to get response from high-reasoning model")
        return None
    
    # Extract the risk assessment
    risk_assessment = extract_risk_assessment(response)
    
    if not risk_assessment:
        print("Error: Failed to parse risk assessment from response")
        return None
    
    # Save results to a file
    print("\nSaving risk assessment to 'risk_assessment.json'...")
    with open("risk_assessment.json", "w", encoding="utf-8") as f:
        json.dump(risk_assessment, f, indent=2)
    
    # Print the risk assessment
    display_risk_assessment(risk_assessment)
    
    print(f"Completed Phase 4: Risk Assessment")
    
    return risk_assessment

def display_risk_assessment(risk_assessment):
    """
    Display the risk assessment in a formatted table.
    
    Args:
        risk_assessment (dict): Dictionary containing the risk assessment
    """
    if not risk_assessment or 'risks' not in risk_assessment:
        print("No risk assessment data to display.")
        return
    
    risks = risk_assessment['risks']
    
    # Sort risks by risk score (highest to lowest)
    risks.sort(key=lambda x: x['risk_score'], reverse=True)
    
    # Print header
    print("\n=== RISK ASSESSMENT SUMMARY ===\n")
    
    # Calculate column widths
    col_q = 1
    col_cat = max(len("Risk Category"), max(len(r['risk_category']) for r in risks))
    col_prob = 4  # "Prob"
    col_imp = 3    # "Imp"
    col_score = 5  # "Score"
    col_tier = max(len("Tier"), max(len(r['risk_tier']) for r in risks))
    
    # Print table header
    header = f"| Q | {' Risk Category'.ljust(col_cat)} | Prob | Imp | Score | {' Tier'.ljust(col_tier)} |"
    separator = f"|{'-'*(col_q+2)}|{'-'*(col_cat+2)}|{'-'*(col_prob+2)}|{'-'*(col_imp+2)}|{'-'*(col_score+2)}|{'-'*(col_tier+2)}|"
    
    print(header)
    print(separator)
    
    # Print table rows
    for risk in risks:
        q_num = risk['question_number']
        category = risk['risk_category']
        probability = risk['probability']
        impact = risk['impact']
        score = risk['risk_score']
        tier = risk['risk_tier']
        
        row = f"| {q_num} | {category.ljust(col_cat)} | {str(probability).center(4)} | {str(impact).center(3)} | {str(score).center(5)} | {tier.ljust(col_tier)} |"
        print(row)
    
    print(separator)
    
    # Print detailed assessments
    print("\n=== DETAILED RISK ASSESSMENTS ===\n")
    
    for risk in risks:
        q_num = risk['question_number']
        category = risk['risk_category']
        probability = risk['probability']
        impact = risk['impact']
        score = risk['risk_score']
        tier = risk['risk_tier']
        justification = risk['justification']
        
        print(f"Risk {q_num}: {category} (Score: {score}, Tier: {tier})")
        print(f"Probability: {probability}/5, Impact: {impact}/5")
        print(f"Justification: {justification}")
        print()

def main():
    """Main execution function"""
    # Check if OpenRouter API key is available
    if not validate_openrouter_api_key():
        return
    
    # Display test mode notice
    if TEST_MODE:
        print("\n*** RUNNING IN TEST MODE ***")
        print("Using only 2 LLMs instead of all 10 for faster testing.")
        print(f"Test LLMs: {', '.join(TEST_LLM_MODELS)}")
    
    # Get user inputs
    user_inputs = get_user_input()
    if user_inputs is None:
        print("Error: Failed to gather required inputs. Exiting.")
        return
    
    # Extract text from PDFs
    print("\nExtracting text from PDFs...")
    
    pitch_deck_text = extract_text_from_pdf(user_inputs["pitch_deck_path"])
    print(f"Extracted {len(pitch_deck_text.split())} words from Pitch Deck PDF")
    
    market_report_text = extract_text_from_pdf(user_inputs["market_report_path"])
    print(f"Extracted {len(market_report_text.split())} words from Market Report PDF")
    
    # Display summary of inputs
    print("\n--- Input Summary ---")
    print(f"Market Chapter: {len(user_inputs['market_chapter'].split())} words")
    print(f"Context: {user_inputs['context']}")
    print(f"Pitch Deck: {len(pitch_deck_text.split())} words")
    print(f"Market Report: {len(market_report_text.split())} words")
    
    # Save extracted data
    extracted_data = {
        "market_chapter": user_inputs["market_chapter"],
        "context": user_inputs["context"],
        "pitch_deck_text": pitch_deck_text,
        "market_report_text": market_report_text
    }
    
    with open("extracted_data.json", "w", encoding="utf-8") as f:
        json.dump(extracted_data, f, indent=2)
    
    print("Completed Phase 1: Input Processing")
    print("Extracted data has been saved to 'extracted_data.json'")
    
    # Phase 2: Generate PMS questions
    pms_questions = None
    
    # Check if we already have generated questions
    if os.path.exists("pms_questions.json"):
        print("\nFound existing PMS questions file.")
        proceed = input("Do you want to use the existing questions? (y/n): ").strip().lower()
        if proceed == 'y':
            try:
                with open("pms_questions.json", "r", encoding="utf-8") as f:
                    pms_questions = json.load(f)
                print(f"Loaded {sum(len(questions) for questions in pms_questions.values())} existing questions.")
            except Exception as e:
                print(f"Error loading existing questions: {str(e)}")
                pms_questions = None
    
    if pms_questions is None:
        # Ask user if they want to proceed to Phase 2
        proceed = input("\nDo you want to proceed to Phase 2 (Generating PMS Questions)? (y/n): ").strip().lower()
        if proceed != 'y':
            print("Exiting. You can run the program again to continue.")
            return
        
        # Generate PMS questions
        pms_questions = generate_pms_questions(extracted_data)
    
    # Phase 3: Consolidate questions
    final_questions = None
    
    # Check if we already have final questions
    if os.path.exists("final_questions.json"):
        print("\nFound existing final questions file.")
        proceed = input("Do you want to use the existing final questions? (y/n): ").strip().lower()
        if proceed == 'y':
            try:
                with open("final_questions.json", "r", encoding="utf-8") as f:
                    final_questions = json.load(f)
                print(f"Loaded {len(final_questions)} existing final questions.")
            except Exception as e:
                print(f"Error loading existing final questions: {str(e)}")
                final_questions = None
    
    if final_questions is None:
        proceed = input("\nDo you want to proceed to Phase 3 (Consolidating Questions)? (y/n): ").strip().lower()
        if proceed != 'y':
            print("Exiting. You can run the program again to continue.")
            return
        
        # Consolidate questions
        final_questions = consolidate_questions(pms_questions)
    
    # Phase 4: Risk Assessment
    if os.path.exists("risk_assessment.json"):
        print("\nFound existing risk assessment file.")
        proceed = input("Do you want to use the existing risk assessment? (y/n): ").strip().lower()
        if proceed == 'y':
            try:
                with open("risk_assessment.json", "r", encoding="utf-8") as f:
                    risk_assessment = json.load(f)
                display_risk_assessment(risk_assessment)
                print("Completed Phase 4: Risk Assessment")
            except Exception as e:
                print(f"Error loading existing risk assessment: {str(e)}")
                risk_assessment = None
    else:
        proceed = input("\nDo you want to proceed to Phase 4 (Risk Assessment)? (y/n): ").strip().lower()
        if proceed != 'y':
            print("Exiting. You can run the program again to continue.")
            return
        
        # Perform risk assessment
        risk_assessment = perform_risk_assessment(final_questions)

if __name__ == "__main__":
    main() 