import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# High-reasoning model for risk assessment
HIGH_REASONING_MODEL = "anthropic/claude-3.7-sonnet:thinking"

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
    
    # Load final questions from file
    if not os.path.exists("final_questions.json"):
        print("Error: final_questions.json file not found.")
        print("Please run the main script first to generate the questions.")
        return
    
    try:
        print("Loading final questions from 'final_questions.json'...")
        with open("final_questions.json", "r", encoding="utf-8") as f:
            final_questions = json.load(f)
        print(f"Loaded {len(final_questions)} final questions.")
    except Exception as e:
        print(f"Error loading final questions: {str(e)}")
        return
    
    # Perform risk assessment
    risk_assessment = perform_risk_assessment(final_questions)

if __name__ == "__main__":
    main() 