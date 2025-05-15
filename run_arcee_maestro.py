#!/usr/bin/env python
# run_arcee_maestro.py
# Script to run only the arcee-ai/maestro-reasoning model and update pms_questions.json

import os
import json
import time
import re
import pdfplumber
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("OPENROUTER_REFERRER", "http://localhost:8501"),
        "X-Title": os.getenv("OPENROUTER_X_TITLE", "Intelligence Questions App")
    }

    payload = {
        "model": model,
        "messages": prompt_messages,
        "temperature": temperature,
        "max_tokens": max_tokens_override
    }
    if is_json_output and ("gpt" in model or "claude-3.5" in model or "claude-3-" in model):
        payload["response_format"] = {"type": "json_object"}

    print(f"Calling OpenRouter API with model: {model}, Temperature: {temperature}, Max Tokens: {max_tokens_override}")
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=180
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

def create_pms_prompt(market_chapter, pitch_deck_text, market_report_text, context):
    """Create prompt for generating Point of Maximum Skepticism (PMS) questions."""
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

def run_arcee_maestro_only(extracted_data):
    """Run only the arcee-ai/maestro-reasoning model and update pms_questions.json"""
    print("\n--- Running arcee-ai/maestro-reasoning model only ---\n")
    
    # First, check if pms_questions.json already exists, and if so, load it
    existing_data = {}
    if os.path.exists("pms_questions.json"):
        try:
            with open("pms_questions.json", "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                print("Loaded existing pms_questions.json")
        except Exception as e:
            print(f"Error loading existing pms_questions.json: {e}")
            existing_data = {}

    # Prepare the prompt
    prompt_text = create_pms_prompt(
        extracted_data["market_chapter"],
        extracted_data["pitch_deck_text"],
        extracted_data["market_report_text"],
        extracted_data["context"]
    )
    prompt_messages = [{"role": "user", "content": prompt_text}]
    
    # Call the arcee-ai/maestro-reasoning model
    model = "arcee-ai/maestro-reasoning"
    print(f"Calling the {model} model...")
    response_data = call_openrouter_api(model, prompt_messages, temperature=0.7, max_tokens_override=5024)
    
    # Process the response
    if response_data and 'choices' in response_data and response_data['choices']:
        content = response_data['choices'][0]['message']['content']
        questions = extract_questions_from_pms_response(content)
        
        # Update the existing data with the new maestro-reasoning results
        existing_data[model] = questions
        print(f"  ✓ Generated {len(questions)} questions")
        for i, q in enumerate(questions):
            print(f"    {i+1}. {q}")
    else:
        print(f"  ✗ Failed to get response from model {model}")
        existing_data[model] = [f"[Failed to generate question from model {model}]" for _ in range(10)]
    
    # Save the updated data back to pms_questions.json
    with open("pms_questions.json", "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=2)
    
    print(f"\nCompleted: Updated pms_questions.json with results from {model}")
    return existing_data

def main():
    """Main execution function."""
    if not validate_openrouter_api_key():
        return

    print("\n*** Arcee Maestro Reasoning Runner ***")
    
    # Paths for files
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
    
    company_context = input("Enter company context (e.g., 'I am an investor in a USA based Nuclear Power Generating Startup that is pre-revenue and Series C'): ").strip()
    if not company_context:
        company_context = "Test Venture: AI for climate change mitigation, pre-seed."

    extracted_data = {
        "market_chapter": mc_text,
        "pitch_deck_text": pd_text,
        "market_report_text": mr_text,
        "context": company_context
    }
    
    # Run the arcee-ai/maestro-reasoning model and update pms_questions.json
    run_arcee_maestro_only(extracted_data)

if __name__ == "__main__":
    main() 