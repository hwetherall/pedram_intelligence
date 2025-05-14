import os
import json
import time
import pdfplumber
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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

def get_user_input():
    """
    Get user inputs for the Market Chapter, Context, and PDF file paths.
    
    Returns:
        dict: Dictionary containing user inputs
    """
    print("\n--- Intelligence Questions Generator ---\n")
    
    # Hardcoded file paths
    market_chapter_path = r"C:\Users\hweth\OneDrive\Desktop\Innovera\Logo Project\pedram_intelligence\marketchapter.txt"
    pitch_deck_path = r"C:\Users\hweth\OneDrive\Desktop\Innovera\Logo Project\pedram_intelligence\pitch_deck.pdf"
    market_report_path = r"C:\Users\hweth\OneDrive\Desktop\Innovera\Logo Project\pedram_intelligence\market_report.pdf"
    
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

Please act as a highly intelligent and skeptical investor. Your goal is to identify potential weaknesses and critical risks.
Generate exactly 10 distinct questions that probe the "Point of Maximum Skepticism" (PMS) for the venture described.
Focus your questions on specific, non-generic aspects of the venture, its market, technology, and business model, viewed through the lens of the provided context. The questions should highlight significant risks or reasons the venture might face major challenges or fail.

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
    Generate Point of Maximum Skepticism (PMS) questions using 10 different LLMs.
    
    Args:
        extracted_data (dict): Dictionary containing the extracted data
        
    Returns:
        dict: Dictionary mapping model names to their generated questions
    """
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
    for i, model in enumerate(LLM_MODELS):
        print(f"Calling model {i+1}/10: {model}...")
        
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
        if i < len(LLM_MODELS) - 1:
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

def main():
    """Main execution function"""
    # Check if OpenRouter API key is available
    if not validate_openrouter_api_key():
        return
    
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
    
    # Ask user if they want to proceed to Phase 2
    proceed = input("\nDo you want to proceed to Phase 2 (Generating PMS Questions)? (y/n): ").strip().lower()
    if proceed != 'y':
        print("Exiting. You can run the program again to continue.")
        return
    
    # Generate PMS questions
    pms_questions = generate_pms_questions(extracted_data)
    
    print("\nNext steps will include:")
    print("1. Consolidating and refining the questions with a high-reasoning model (Phase 3)")
    print("2. Applying the risk assessment framework (Phase 4)")

if __name__ == "__main__":
    main() 