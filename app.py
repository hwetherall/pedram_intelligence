import streamlit as st
import json
import os
from intelligence_question_generator import (
    extract_text_from_pdf,
    generate_pms_questions,
    consolidate_questions,
    perform_risk_assessment,
    develop_derisking_strategies,
    perform_strategic_reflection
)

# EXECUTE: python -m streamlit run app.py 
# to run the app

# Set page config
st.set_page_config(
    page_title="Intelligence Questions Generator",
    page_icon="🤖",
    layout="wide"
)

# File paths for saved state
EXTRACTED_DATA_PATH = "extracted_data.json"
PMS_QUESTIONS_PATH = "pms_questions.json"
FINAL_QUESTIONS_PATH = "final_questions.json"
RISK_ASSESSMENT_PATH = "risk_assessment.json"
DERISKING_STRATEGIES_PATH = "detailed_risk_report_with_strategies.json"
STRATEGIC_REFLECTION_PATH = "strategic_reflection.json"

# Initialize session state for reset control
if 'reset_trigger' not in st.session_state:
    st.session_state.reset_trigger = False
if 'reset_phase' not in st.session_state:
    st.session_state.reset_phase = None

# Initialize session state for data
if 'extracted_data' not in st.session_state or st.session_state.reset_trigger:
    if st.session_state.reset_phase == "all" or st.session_state.reset_phase == "phase1":
        st.session_state.extracted_data = None
    elif os.path.exists(EXTRACTED_DATA_PATH) and st.session_state.extracted_data is None:
        try:
            with open(EXTRACTED_DATA_PATH, "r", encoding="utf-8") as f:
                st.session_state.extracted_data = json.load(f)
        except Exception:
            st.session_state.extracted_data = None

if 'pms_questions' not in st.session_state or st.session_state.reset_trigger:
    if st.session_state.reset_phase in ["all", "phase1", "phase2"]:
        st.session_state.pms_questions = None
    elif os.path.exists(PMS_QUESTIONS_PATH) and st.session_state.pms_questions is None:
        try:
            with open(PMS_QUESTIONS_PATH, "r", encoding="utf-8") as f:
                st.session_state.pms_questions = json.load(f)
        except Exception:
            st.session_state.pms_questions = None

if 'final_questions' not in st.session_state or st.session_state.reset_trigger:
    if st.session_state.reset_phase in ["all", "phase1", "phase2", "phase3"]:
        st.session_state.final_questions = None
    elif os.path.exists(FINAL_QUESTIONS_PATH) and st.session_state.final_questions is None:
        try:
            with open(FINAL_QUESTIONS_PATH, "r", encoding="utf-8") as f:
                st.session_state.final_questions = json.load(f)
        except Exception:
            st.session_state.final_questions = None

if 'risk_assessment' not in st.session_state or st.session_state.reset_trigger:
    if st.session_state.reset_phase in ["all", "phase1", "phase2", "phase3", "phase4"]:
        st.session_state.risk_assessment = None
    elif os.path.exists(RISK_ASSESSMENT_PATH) and st.session_state.risk_assessment is None:
        try:
            with open(RISK_ASSESSMENT_PATH, "r", encoding="utf-8") as f:
                loaded_risks = json.load(f)
                if isinstance(loaded_risks, list):
                    st.session_state.risk_assessment = {
                        "risks": loaded_risks,
                        "summary_stats": {
                            "high_risks": len([r for r in loaded_risks if r.get("risk_tier") == "High"]),
                            "medium_risks": len([r for r in loaded_risks if r.get("risk_tier") == "Medium"]),
                            "low_risks": len([r for r in loaded_risks if r.get("risk_tier") == "Low"]),
                            "total_risks_assessed": len(loaded_risks)
                        }
                    }
                else:
                    st.session_state.risk_assessment = loaded_risks
        except Exception:
            st.session_state.risk_assessment = None

if 'derisking_strategies' not in st.session_state or st.session_state.reset_trigger:
    if st.session_state.reset_phase in ["all", "phase1", "phase2", "phase3", "phase4", "phase5"]:
        st.session_state.derisking_strategies = None
    elif os.path.exists(DERISKING_STRATEGIES_PATH) and st.session_state.derisking_strategies is None:
        try:
            with open(DERISKING_STRATEGIES_PATH, "r", encoding="utf-8") as f:
                st.session_state.derisking_strategies = json.load(f)
        except Exception:
            st.session_state.derisking_strategies = None

if 'strategic_reflection' not in st.session_state or st.session_state.reset_trigger:
    if st.session_state.reset_phase in ["all", "phase1", "phase2", "phase3", "phase4", "phase5", "phase6"]:
        st.session_state.strategic_reflection = None
    elif os.path.exists(STRATEGIC_REFLECTION_PATH) and st.session_state.strategic_reflection is None:
        try:
            with open(STRATEGIC_REFLECTION_PATH, "r", encoding="utf-8") as f:
                st.session_state.strategic_reflection = json.load(f)
        except Exception:
            st.session_state.strategic_reflection = None

if 'processing_phase' not in st.session_state:
    st.session_state.processing_phase = None

# Reset the reset trigger at the end of loading
if st.session_state.reset_trigger:
    st.session_state.reset_trigger = False
    st.session_state.reset_phase = None

# Helper functions to save and load state
def save_state_to_file(data, file_path):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving to {file_path}: {str(e)}")
        return False

def load_state_from_file(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading from {file_path}: {str(e)}")
    return None

# Helper function for reset buttons
def reset_state(phase):
    st.session_state.reset_trigger = True
    st.session_state.reset_phase = phase
    st.rerun()

# Title and description
st.title("🤖 Intelligence Questions Generator")
st.markdown("""
This application helps generate and analyze intelligence questions based on market data, pitch decks, and market reports.
The process is divided into 6 phases:
1. Input Processing
2. Generating PMS Questions
3. Consolidating Questions
4. Risk Assessment
5. De-Risking Strategies
6. Strategic Reflection (I Like, I Wish, I Wonder)
""")

# Hardcoded file paths
MARKET_CHAPTER_PATH = "marketchapter.txt"
PITCH_DECK_PATH = "pitch_deck.pdf"
MARKET_REPORT_PATH = "market_report.pdf"

# Sidebar for context input and reset controls
with st.sidebar:
    st.header("📝 Context Input")
    
    # Context input
    context = st.text_area(
        "Context",
        value=st.session_state.extracted_data["context"] if st.session_state.extracted_data is not None else "",
        help="Enter the framing for the company (e.g., 'Series C Investment for a Nuclear Power Generator Company that is pre-revenue')",
        height=150  # Set initial height, will expand if needed
    )
    
    # Reset controls section
    st.header("🔄 Reset Controls")
    st.caption("Clear specific phases to rerun them")
    
    reset_cols = st.columns(2)
    
    with reset_cols[0]:
        if st.button("Reset All Phases"):
            reset_state("all")
            
        if st.button("Reset Phase 2+"):
            reset_state("phase2")
            
        if st.button("Reset Phase 3+"):
            reset_state("phase3")
            
    with reset_cols[1]:
        if st.button("Reset Phase 4+"):
            reset_state("phase4")
            
        if st.button("Reset Phase 5+"):
            reset_state("phase5")
            
        if st.button("Reset Phase 6"):
            reset_state("phase6")
            
        # Load Demo Data option
        if st.button("Load Demo Data"):
            # This would load any saved demo data for quick presentations
            demo_loaded = False
            for path in [EXTRACTED_DATA_PATH, PMS_QUESTIONS_PATH, FINAL_QUESTIONS_PATH, RISK_ASSESSMENT_PATH, DERISKING_STRATEGIES_PATH, STRATEGIC_REFLECTION_PATH]:
                if os.path.exists(path):
                    demo_loaded = True
            
            if demo_loaded:
                st.session_state.extracted_data = load_state_from_file(EXTRACTED_DATA_PATH) if os.path.exists(EXTRACTED_DATA_PATH) else None
                st.session_state.pms_questions = load_state_from_file(PMS_QUESTIONS_PATH) if os.path.exists(PMS_QUESTIONS_PATH) else None
                st.session_state.final_questions = load_state_from_file(FINAL_QUESTIONS_PATH) if os.path.exists(FINAL_QUESTIONS_PATH) else None
                
                if os.path.exists(RISK_ASSESSMENT_PATH):
                    loaded_risks = load_state_from_file(RISK_ASSESSMENT_PATH)
                    if loaded_risks:
                        if isinstance(loaded_risks, list):
                            st.session_state.risk_assessment = {
                                "risks": loaded_risks,
                                "summary_stats": {
                                    "high_risks": len([r for r in loaded_risks if r.get("risk_tier") == "High"]),
                                    "medium_risks": len([r for r in loaded_risks if r.get("risk_tier") == "Medium"]),
                                    "low_risks": len([r for r in loaded_risks if r.get("risk_tier") == "Low"]),
                                    "total_risks_assessed": len(loaded_risks)
                                }
                            }
                        else:
                            st.session_state.risk_assessment = loaded_risks
                
                st.session_state.derisking_strategies = load_state_from_file(DERISKING_STRATEGIES_PATH) if os.path.exists(DERISKING_STRATEGIES_PATH) else None
                st.session_state.strategic_reflection = load_state_from_file(STRATEGIC_REFLECTION_PATH) if os.path.exists(STRATEGIC_REFLECTION_PATH) else None
                st.success("Demo data loaded!")
                st.rerun()
            else:
                st.error("No demo data files found.")

# Main content area
if context:
    # Update context in extracted_data if it changed
    if st.session_state.extracted_data is not None and st.session_state.extracted_data.get("context") != context:
        st.session_state.extracted_data["context"] = context
        save_state_to_file(st.session_state.extracted_data, EXTRACTED_DATA_PATH)

    # Phase 1: Input Processing
    st.header("Phase 1: Input Processing")
    if st.session_state.processing_phase == "phase1":
        with st.spinner("Processing inputs..."):
            st.write("")
    
    phase1_col1, phase1_col2 = st.columns([3, 1])
    with phase1_col1:
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
                    # Save to file for future loading
                    save_state_to_file(st.session_state.extracted_data, EXTRACTED_DATA_PATH)
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
    
    with phase1_col2:
        if st.session_state.extracted_data is not None:
            if st.button("📂 Load Saved Inputs", key="load_extracted_data"):
                if os.path.exists(EXTRACTED_DATA_PATH):
                    loaded_data = load_state_from_file(EXTRACTED_DATA_PATH)
                    if loaded_data:
                        # Keep current context but load other data
                        loaded_data["context"] = context
                        st.session_state.extracted_data = loaded_data
                        st.success("Loaded saved inputs!")
                        st.rerun()
                else:
                    st.error("No saved input data found.")

    # Phase 2: Generate PMS Questions
    st.header("Phase 2: Generate PMS Questions")
    if st.session_state.processing_phase == "phase2":
        with st.spinner("Generating questions..."):
            st.write("")
    
    phase2_col1, phase2_col2 = st.columns([3, 1])
    with phase2_col1:
        if st.session_state.pms_questions is None:
            if st.button("Generate PMS Questions", 
                        disabled=st.session_state.processing_phase is not None or st.session_state.extracted_data is None):
                st.session_state.processing_phase = "phase2"
                try:
                    st.session_state.pms_questions = generate_pms_questions(st.session_state.extracted_data)
                    # Save to file for future loading
                    save_state_to_file(st.session_state.pms_questions, PMS_QUESTIONS_PATH)
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
    
    with phase2_col2:
        if st.session_state.extracted_data is not None:
            if st.button("📂 Load Saved Questions", key="load_pms_questions"):
                if os.path.exists(PMS_QUESTIONS_PATH):
                    loaded_questions = load_state_from_file(PMS_QUESTIONS_PATH)
                    if loaded_questions:
                        st.session_state.pms_questions = loaded_questions
                        st.success("Loaded saved questions!")
                        st.rerun()
                else:
                    st.error("No saved questions found.")

    # Phase 3: Consolidate Questions
    st.header("Phase 3: Consolidate Questions")
    if st.session_state.processing_phase == "phase3":
        with st.spinner("Consolidating questions..."):
            st.write("")
    
    phase3_col1, phase3_col2 = st.columns([3, 1])
    with phase3_col1:
        if st.session_state.final_questions is None:
            if st.button("Consolidate Questions", 
                        disabled=st.session_state.processing_phase is not None or st.session_state.pms_questions is None):
                st.session_state.processing_phase = "phase3"
                try:
                    st.session_state.final_questions = consolidate_questions(st.session_state.pms_questions, st.session_state.extracted_data)
                    # Save to file for future loading
                    save_state_to_file(st.session_state.final_questions, FINAL_QUESTIONS_PATH)
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
                    st.write(f"Question: {q['question_text']}")
                    st.write(f"Reasoning: {q['reasoning']}")
    
    with phase3_col2:
        if st.session_state.pms_questions is not None:
            if st.button("📂 Load Saved Consolidated Questions", key="load_final_questions"):
                if os.path.exists(FINAL_QUESTIONS_PATH):
                    loaded_final_questions = load_state_from_file(FINAL_QUESTIONS_PATH)
                    if loaded_final_questions:
                        st.session_state.final_questions = loaded_final_questions
                        st.success("Loaded saved consolidated questions!")
                        st.rerun()
                else:
                    st.error("No saved consolidated questions found.")

    # Phase 4: Risk Assessment
    st.header("Phase 4: Risk Assessment")
    if st.session_state.processing_phase == "phase4":
        with st.spinner("Performing risk assessment..."):
            st.write("")
    
    phase4_col1, phase4_col2 = st.columns([3, 1])
    with phase4_col1:
        if st.session_state.risk_assessment is None:
            if st.button("Perform Risk Assessment", 
                        disabled=st.session_state.processing_phase is not None or st.session_state.final_questions is None):
                st.session_state.processing_phase = "phase4"
                try:
                    st.session_state.risk_assessment = perform_risk_assessment(st.session_state.final_questions, st.session_state.extracted_data)
                    # Save to file for future loading (list format for compatibility)
                    save_state_to_file(st.session_state.risk_assessment['risks'], RISK_ASSESSMENT_PATH)
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
    
    with phase4_col2:
        if st.session_state.final_questions is not None:
            if st.button("📂 Load Saved Risk Assessment", key="load_risk_assessment"):
                if os.path.exists(RISK_ASSESSMENT_PATH):
                    loaded_risks = load_state_from_file(RISK_ASSESSMENT_PATH)
                    if loaded_risks:
                        # Convert to expected format if needed
                        if isinstance(loaded_risks, list):
                            st.session_state.risk_assessment = {
                                "risks": loaded_risks,
                                "summary_stats": {
                                    "high_risks": len([r for r in loaded_risks if r.get("risk_tier") == "High"]),
                                    "medium_risks": len([r for r in loaded_risks if r.get("risk_tier") == "Medium"]),
                                    "low_risks": len([r for r in loaded_risks if r.get("risk_tier") == "Low"]),
                                    "total_risks_assessed": len(loaded_risks)
                                }
                            }
                        else:
                            st.session_state.risk_assessment = loaded_risks
                        st.success("Loaded saved risk assessment!")
                        st.rerun()
                else:
                    st.error("No saved risk assessment found.")

    # Phase 5: De-Risking Strategies
    st.header("Phase 5: De-Risking Strategies")
    if st.session_state.processing_phase == "phase5":
        with st.spinner("Developing de-risking strategies..."):
            st.write("")
    
    phase5_col1, phase5_col2 = st.columns([3, 1])
    with phase5_col1:
        if st.session_state.derisking_strategies is None:
            if st.button("Develop De-Risking Strategies", 
                        disabled=st.session_state.processing_phase is not None or st.session_state.risk_assessment is None):
                st.session_state.processing_phase = "phase5"
                try:
                    # Pass the risk assessment list, extracted data, and context
                    risks = st.session_state.risk_assessment['risks']
                    st.session_state.derisking_strategies = develop_derisking_strategies(
                        risks, 
                        st.session_state.extracted_data, 
                        st.session_state.extracted_data["context"]
                    )
                    # Save to file for future loading
                    save_state_to_file(st.session_state.derisking_strategies, DERISKING_STRATEGIES_PATH)
                    st.success("De-risking strategies developed!")
                except Exception as e:
                    st.error(f"Error developing de-risking strategies: {str(e)}")
                finally:
                    st.session_state.processing_phase = None
                    st.rerun()
        else:
            st.success("De-risking strategies developed!")
            # Display only high-priority risks with strategies
            high_priority_risks = [r for r in st.session_state.derisking_strategies 
                                  if isinstance(r.get("de_risking_plan"), dict) and 
                                  "status" not in r.get("de_risking_plan", {})]
            
            if high_priority_risks:
                st.subheader("De-Risking Plans for High-Priority Risks")
                for risk in high_priority_risks:
                    with st.expander(f"De-Risking Plan for Risk {risk['question_number']}: {risk['risk_category']}"):
                        st.write(f"**Question:** {risk['question_text']}")
                        st.write(f"**Risk Score:** {risk['risk_score']} ({risk['risk_tier']} tier)")
                        
                        plan = risk.get("de_risking_plan", {})
                        
                        # Display Research Strategies
                        if "research_strategies" in plan and plan["research_strategies"]:
                            st.write("#### Research Strategies")
                            for strategy in plan["research_strategies"]:
                                st.write(f"**{strategy.get('action_title', 'N/A')}**")
                                st.write(f"- Description: {strategy.get('description', 'N/A')}")
                                st.write(f"- Mitigation Effect: {strategy.get('mitigation_effect', 'N/A')}")
                                st.write(f"- Effort Level: {strategy.get('effort_level', 'N/A')}")
                                if "potential_challenges" in strategy:
                                    st.write(f"- Potential Challenges: {strategy.get('potential_challenges')}")
                        
                        # Display Test Strategies
                        if "test_strategies" in plan and plan["test_strategies"]:
                            st.write("#### Test Strategies")
                            for strategy in plan["test_strategies"]:
                                st.write(f"**{strategy.get('action_title', 'N/A')}**")
                                st.write(f"- Description: {strategy.get('description', 'N/A')}")
                                st.write(f"- Mitigation Effect: {strategy.get('mitigation_effect', 'N/A')}")
                                st.write(f"- Effort Level: {strategy.get('effort_level', 'N/A')}")
                                if "potential_challenges" in strategy:
                                    st.write(f"- Potential Challenges: {strategy.get('potential_challenges')}")
                        
                        # Display Act Strategies
                        if "act_strategies" in plan and plan["act_strategies"]:
                            st.write("#### Act Strategies")
                            for strategy in plan["act_strategies"]:
                                st.write(f"**{strategy.get('action_title', 'N/A')}**")
                                st.write(f"- Description: {strategy.get('description', 'N/A')}")
                                st.write(f"- Mitigation Effect: {strategy.get('mitigation_effect', 'N/A')}")
                                st.write(f"- Effort Level: {strategy.get('effort_level', 'N/A')}")
                                if "potential_challenges" in strategy:
                                    st.write(f"- Potential Challenges: {strategy.get('potential_challenges')}")
            else:
                st.info("No high-priority risks were identified for de-risking strategy development.")
    
    with phase5_col2:
        if st.session_state.risk_assessment is not None:
            if st.button("📂 Load Saved De-Risking Strategies", key="load_derisking"):
                if os.path.exists(DERISKING_STRATEGIES_PATH):
                    loaded_strategies = load_state_from_file(DERISKING_STRATEGIES_PATH)
                    if loaded_strategies:
                        st.session_state.derisking_strategies = loaded_strategies
                        st.success("Loaded saved de-risking strategies!")
                        st.rerun()
                else:
                    st.error("No saved de-risking strategies found.")

    # Phase 6: Strategic Reflection (I Like, I Wish, I Wonder)
    st.header("Phase 6: Strategic Reflection")
    if st.session_state.processing_phase == "phase6":
        with st.spinner("Generating strategic reflection..."):
            st.write("")

    phase6_col1, phase6_col2 = st.columns([3, 1])
    with phase6_col1:
        if st.session_state.strategic_reflection is None:
            if st.button("Generate Strategic Reflection", 
                        disabled=st.session_state.processing_phase is not None or st.session_state.derisking_strategies is None):
                st.session_state.processing_phase = "phase6"
                try:
                    # Pass all the required data to the function
                    st.session_state.strategic_reflection = perform_strategic_reflection(
                        st.session_state.extracted_data["context"],
                        st.session_state.final_questions,
                        st.session_state.risk_assessment,
                        st.session_state.derisking_strategies,
                        st.session_state.extracted_data
                    )
                    # Save to file for future loading
                    save_state_to_file(st.session_state.strategic_reflection, STRATEGIC_REFLECTION_PATH)
                    st.success("Strategic reflection generated!")
                except Exception as e:
                    st.error(f"Error generating strategic reflection: {str(e)}")
                finally:
                    st.session_state.processing_phase = None
                    st.rerun()
        else:
            st.success("Strategic reflection generated!")
            
            # Display I Like reflections
            if "i_like_reflection" in st.session_state.strategic_reflection:
                with st.expander("I Like (Strengths & Opportunities to Build Upon)", expanded=True):
                    for item in st.session_state.strategic_reflection["i_like_reflection"]:
                        st.write(f"- {item}")
            
            # Display I Wish reflections
            if "i_wish_reflection" in st.session_state.strategic_reflection:
                with st.expander("I Wish (Strategic Gaps & Desired Shifts)", expanded=True):
                    for item in st.session_state.strategic_reflection["i_wish_reflection"]:
                        st.write(f"- {item}")
            
            # Display I Wonder reflections
            if "i_wonder_reflection" in st.session_state.strategic_reflection:
                with st.expander("I Wonder (Pivotal Uncertainties & Future Explorations)", expanded=True):
                    for item in st.session_state.strategic_reflection["i_wonder_reflection"]:
                        st.write(f"- {item}")

    with phase6_col2:
        if st.session_state.derisking_strategies is not None:
            if st.button("📂 Load Saved Strategic Reflection", key="load_strategic_reflection"):
                if os.path.exists(STRATEGIC_REFLECTION_PATH):
                    loaded_reflection = load_state_from_file(STRATEGIC_REFLECTION_PATH)
                    if loaded_reflection:
                        st.session_state.strategic_reflection = loaded_reflection
                        st.success("Loaded saved strategic reflection!")
                        st.rerun()
                else:
                    st.error("No saved strategic reflection found.")

else:
    st.info("Please enter the context information in the sidebar to begin.") 