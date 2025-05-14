# Intelligence Questions Generator

This application generates "Intelligence Questions" - the questions that a smart person would ask about a potential venture, with a focus on identifying risks.

## Overview

The application follows these steps:
1. Processing inputs (Market Chapter, PDFs, and Context)
2. Generating 100 "Point of Maximum Skepticism" questions using 10 different LLMs
3. Consolidating and refining these into 5 critical questions
4. Assessing risk for each question
5. (Future) Developing de-risking strategies

## Setup

### Prerequisites
- Python 3.7 or higher
- OpenRouter API key

### Installation

1. Clone this repository
2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the project directory with your OpenRouter API key:
   ```
   OPENROUTER_API_KEY=your_api_key_here
   ```

### Document Setup

The application is currently configured to use specific hardcoded file paths:

- Market Chapter: `C:\Users\hweth\OneDrive\Desktop\Innovera\Logo Project\pedram_intelligence\marketchapter.txt`
- Pitch Deck PDF: `C:\Users\hweth\OneDrive\Desktop\Innovera\Logo Project\pedram_intelligence\pitch_deck.pdf`
- Market Report PDF: `C:\Users\hweth\OneDrive\Desktop\Innovera\Logo Project\pedram_intelligence\market_report.pdf`

To use different files, modify these paths in the `get_user_input()` function in `intelligence_question_generator.py`.

## Usage

Run the main script:
```
python intelligence_question_generator.py
```

The application will:
1. Load the Market Chapter from the specified text file
2. Prompt you to enter the Context information
3. Extract text from the specified PDF files
4. Save the extracted data to `extracted_data.json`
5. Ask if you want to proceed to Phase 2 (generating questions)
6. If yes, call 10 different LLMs through OpenRouter to generate questions
7. Save the generated questions to `pms_questions.json`

## LLM Models Used

The application uses the following 10 LLM models from OpenRouter:

1. openai/o1-mini
2. anthropic/claude-3.7-sonnet:thinking
3. google/gemini-2.5-flash-preview:thinking
4. x-ai/grok-3-beta
5. deepseek/deepseek-chat-v3-0324
6. arcee-ai/maestro-reasoning
7. qwen/qwq-32b
8. perplexity/sonar-reasoning-pro
9. meta-llama/llama-4-maverick
10. mistralai/mistral-medium-3

## Current Status

This is an MVP (Minimum Viable Product) version. Current functionality:
- Phase 1: Input processing and PDF text extraction ✓
- Phase 2: Generating PMS questions using 10 different LLMs via OpenRouter ✓
- Phase 3: Consolidating and refining questions with a high-reasoning model (Not implemented yet)
- Phase 4: Applying the risk assessment framework (Not implemented yet)
- Phase 5: Developing de-risking strategies (Not implemented yet) 
