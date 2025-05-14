import streamlit as st
import json
import os
from intelligence_question_generator import (
    extract_text_from_pdf,
    generate_pms_questions,
    consolidate_questions,
    perform_risk_assessment,
    display_risk_assessment
)

# EXECUTE: python -m streamlit run app.py 
# to run the app

# Set page config
st.set_page_config(
    page_title="Intelligence Questions Generator",
    page_icon="🤖",
    layout="wide"
)

# Initialize session state
if 'extracted_data' not in st.session_state:
    st.session_state.extracted_data = None
if 'pms_questions' not in st.session_state:
    st.session_state.pms_questions = None
if 'final_questions' not in st.session_state:
    st.session_state.final_questions = None
if 'risk_assessment' not in st.session_state:
    st.session_state.risk_assessment = None
if 'processing_phase' not in st.session_state:
    st.session_state.processing_phase = None

# Title and description
st.title("🤖 Intelligence Questions Generator")
st.markdown("""
This application helps generate and analyze intelligence questions based on market data, pitch decks, and market reports.
The process is divided into 4 phases:
1. Input Processing
2. Generating PMS Questions
3. Consolidating Questions
4. Risk Assessment
""")

# Hardcoded file paths
MARKET_CHAPTER_PATH = "marketchapter.txt"
PITCH_DECK_PATH = "pitch_deck.pdf"
MARKET_REPORT_PATH = "market_report.pdf"

# Sidebar for context input
with st.sidebar:
    st.header("📝 Context Input")
    
    # Context input
    context = st.text_area(
        "Context",
        help="Enter the framing for the company (e.g., 'Series C Investment for a Nuclear Power Generator Company that is pre-revenue')",
        height=150  # Set initial height, will expand if needed
    )

# Main content area
if context:
    # Phase 1: Input Processing
    st.header("Phase 1: Input Processing")
    if st.session_state.processing_phase == "phase1":
        with st.spinner("Processing inputs..."):
            st.write("")
    if st.session_state.extracted_data is None:
        if st.button("Process Inputs", disabled=st.session_state.processing_phase is not None):
            st.session_state.processing_phase = "phase1"
            try:
                # Read Market Chapter
                with open(MARKET_CHAPTER_PATH, 'r', encoding='utf-8') as f:
                    market_chapter = f.read()
                # Extract text from PDFs
                pitch_deck_text = extract_text_from_pdf(PITCH_DECK_PATH)
                market_report_text = extract_text_from_pdf(MARKET_REPORT_PATH)
                # Save extracted data
                st.session_state.extracted_data = {
                    "market_chapter": market_chapter,
                    "context": context,
                    "pitch_deck_text": pitch_deck_text,
                    "market_report_text": market_report_text
                }
                st.success("Input processing completed!")
                st.json({
                    "Market Chapter Words": len(market_chapter.split()),
                    "Context": context,
                    "Pitch Deck Words": len(pitch_deck_text.split()),
                    "Market Report Words": len(market_report_text.split())
                })
            except Exception as e:
                st.error(f"Error processing inputs: {str(e)}")
            finally:
                st.session_state.processing_phase = None
                st.rerun()
    else:
        st.success("Input processing completed!")
        st.json({
            "Market Chapter Words": len(st.session_state.extracted_data["market_chapter"].split()),
            "Context": st.session_state.extracted_data["context"],
            "Pitch Deck Words": len(st.session_state.extracted_data["pitch_deck_text"].split()),
            "Market Report Words": len(st.session_state.extracted_data["market_report_text"].split())
        })

    # Phase 2: Generate PMS Questions
    st.header("Phase 2: Generate PMS Questions")
    if st.session_state.processing_phase == "phase2":
        with st.spinner("Generating questions..."):
            st.write("")
    if st.session_state.pms_questions is None:
        if st.button("Generate PMS Questions", 
                    disabled=st.session_state.processing_phase is not None or st.session_state.extracted_data is None):
            st.session_state.processing_phase = "phase2"
            try:
                st.session_state.pms_questions = generate_pms_questions(st.session_state.extracted_data)
                st.success("Questions generated successfully!")
            except Exception as e:
                st.error(f"Error generating questions: {str(e)}")
            finally:
                st.session_state.processing_phase = None
                st.rerun()
    else:
        st.success("Questions generated successfully!")
        for model, questions in st.session_state.pms_questions.items():
            with st.expander(f"Questions from {model}"):
                for i, q in enumerate(questions, 1):
                    st.write(f"{i}. {q}")

    # Phase 3: Consolidate Questions
    st.header("Phase 3: Consolidate Questions")
    if st.session_state.processing_phase == "phase3":
        with st.spinner("Consolidating questions..."):
            st.write("")
    if st.session_state.final_questions is None:
        if st.button("Consolidate Questions", 
                    disabled=st.session_state.processing_phase is not None or st.session_state.pms_questions is None):
            st.session_state.processing_phase = "phase3"
            try:
                st.session_state.final_questions = consolidate_questions(st.session_state.pms_questions)
                st.success("Questions consolidated successfully!")
            except Exception as e:
                st.error(f"Error consolidating questions: {str(e)}")
            finally:
                st.session_state.processing_phase = None
                st.rerun()
    else:
        st.success("Questions consolidated successfully!")
        for q in st.session_state.final_questions:
            with st.expander(f"Question {q['question_number']}"):
                st.write(f"Question: {q['question']}")
                st.write(f"Reasoning: {q['reasoning']}")

    # Phase 4: Risk Assessment
    st.header("Phase 4: Risk Assessment")
    if st.session_state.processing_phase == "phase4":
        with st.spinner("Performing risk assessment..."):
            st.write("")
    if st.session_state.risk_assessment is None:
        if st.button("Perform Risk Assessment", 
                    disabled=st.session_state.processing_phase is not None or st.session_state.final_questions is None):
            st.session_state.processing_phase = "phase4"
            try:
                st.session_state.risk_assessment = perform_risk_assessment(st.session_state.final_questions)
                st.success("Risk assessment completed!")
            except Exception as e:
                st.error(f"Error performing risk assessment: {str(e)}")
            finally:
                st.session_state.processing_phase = None
                st.rerun()
    else:
        st.success("Risk assessment completed!")
        if st.session_state.risk_assessment and 'risks' in st.session_state.risk_assessment:
            risks = st.session_state.risk_assessment['risks']
            risks.sort(key=lambda x: x['risk_score'], reverse=True)
            st.subheader("Risk Assessment Summary")
            summary_data = {
                "Question": [r['question_number'] for r in risks],
                "Risk Category": [r['risk_category'] for r in risks],
                "Probability": [r['probability'] for r in risks],
                "Impact": [r['impact'] for r in risks],
                "Risk Score": [r['risk_score'] for r in risks],
                "Risk Tier": [r['risk_tier'] for r in risks]
            }
            st.dataframe(summary_data)
            st.subheader("Detailed Risk Assessments")
            for risk in risks:
                with st.expander(f"Risk {risk['question_number']}: {risk['risk_category']}"):
                    st.write(f"Probability: {risk['probability']}/5")
                    st.write(f"Impact: {risk['impact']}/5")
                    st.write(f"Risk Score: {risk['risk_score']}")
                    st.write(f"Risk Tier: {risk['risk_tier']}")
                    st.write(f"Justification: {risk['justification']}")


else:
    st.info("Please enter the context information in the sidebar to begin.") 