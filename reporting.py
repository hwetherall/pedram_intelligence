# reporting.py

import os
import json
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

# Attempt to import WeasyPrint, but make it optional if not strictly needed for HTML part
try:
    from weasyprint import HTML
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    print("Warning: WeasyPrint not installed. PDF generation will not be available.")
    print("To enable PDF generation, run: pip install WeasyPrint")


def generate_html_report(template_data, template_name="memo_template.html", output_html_file="intelligence_brief.html"):
    """Generates an HTML report using Jinja2."""
    try:
        # Setup Jinja2 environment
        # Assumes 'memo_template.html' is in a 'templates' subdirectory relative to this script
        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        template_dir = os.path.join(current_script_dir, 'templates')
        
        if not os.path.isdir(template_dir):
            # Fallback: check if templates dir is in parent if reporting.py is in a subdir
            parent_dir = os.path.dirname(current_script_dir)
            template_dir_alt = os.path.join(parent_dir, 'templates')
            if os.path.isdir(template_dir_alt):
                template_dir = template_dir_alt
            else: # Fallback to current directory of the script if no 'templates' found
                 print(f"Warning: 'templates' directory not found at {template_dir} or {template_dir_alt}. Looking in script directory.")
                 template_dir = current_script_dir if current_script_dir else '.'


        if not os.path.exists(os.path.join(template_dir, template_name)):
            print(f"Error: Template file '{template_name}' not found in directory '{template_dir}'.")
            # Try looking in the current working directory as a last resort
            if os.path.exists(template_name):
                template_dir = "." # Use current working directory
                print(f"Found template '{template_name}' in current working directory.")
            else:
                print(f"HTML report generation failed: Template '{template_name}' not found.")
                return None


        env = Environment(loader=FileSystemLoader(template_dir), autoescape=True) # Enable autoescaping
        template = env.get_template(template_name)
        
        # Render HTML
        html_content = template.render(template_data)
        
        # Save HTML file
        with open(output_html_file, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"HTML report saved to {output_html_file}")
        return output_html_file
    except Exception as e:
        print(f"Error generating HTML report: {e}")
        import traceback
        traceback.print_exc()
        return None

def convert_html_to_pdf(html_file_path, output_pdf_file="intelligence_brief.pdf"):
    """Converts an HTML file to PDF using WeasyPrint."""
    if not WEASYPRINT_AVAILABLE:
        print("PDF conversion skipped: WeasyPrint library is not available.")
        return None
    if not os.path.exists(html_file_path):
        print(f"Error: HTML file for PDF conversion not found at {html_file_path}")
        return None
        
    try:
        HTML(html_file_path).write_pdf(output_pdf_file)
        print(f"PDF report saved to {output_pdf_file}")
        return output_pdf_file
    except Exception as e:
        print(f"Error converting HTML to PDF: {e}")
        print("Ensure WeasyPrint and its system dependencies (Pango, Cairo, etc.) are correctly installed.")
        import traceback
        traceback.print_exc()
        return None

def create_final_report(company_context, final_questions_data, risk_assessment_data_dict, derisking_strategies_data, strategic_reflection_data, output_base_filename="intelligence_brief"):
    """
    Prepares data and generates HTML and PDF reports.
    Args:
        company_context (str)
        final_questions_data (list): Output of consolidate_questions
        risk_assessment_data_dict (dict): Output of perform_risk_assessment (contains 'risks' list)
        derisking_strategies_data (list): Output of develop_derisking_strategies (list of risks with plans)
        strategic_reflection_data (dict): Output of perform_strategic_reflection
        output_base_filename (str): Base name for output files (e.g., "intelligence_brief")
    """
    print("\n--- Generating Final Report Memo ---")

    if not all([final_questions_data, risk_assessment_data_dict, strategic_reflection_data]):
        print("Cannot generate report: Missing critical data (Final Questions, Risk Assessment, or Strategic Reflection).")
        if not final_questions_data: print("- Final Questions data missing.")
        if not risk_assessment_data_dict: print("- Risk Assessment data missing.")
        if not strategic_reflection_data: print("- Strategic Reflection data missing.")
        return

    # Prepare data for the template
    # Combine final_questions, their risk assessments, and their de-risking plans.
    
    # The derisking_strategies_data is a list of ALL risks, where some (high-priority)
    # will have a 'de_risking_plan' key.
    # If derisking was not run or failed, derisking_strategies_data might be None or an empty list,
    # or a list where no items have the 'de_risking_plan' key populated with actual strategies.
    
    final_questions_with_details_list = []
    if final_questions_data and isinstance(final_questions_data, list):
        for fq_item in final_questions_data:
            q_num = fq_item.get("question_number")
            
            # Find corresponding risk assessment
            risk_data_for_q = None
            if risk_assessment_data_dict and "risks" in risk_assessment_data_dict and isinstance(risk_assessment_data_dict["risks"], list):
                risk_data_for_q = next((r for r in risk_assessment_data_dict["risks"] if r.get("question_number") == q_num), None)

            # Find corresponding de-risking plan
            derisking_plan_for_q = None
            # derisking_strategies_data is the list of *all* risks, potentially updated with plans
            if derisking_strategies_data and isinstance(derisking_strategies_data, list):
                full_risk_item_with_plan = next((r_wp for r_wp in derisking_strategies_data if r_wp.get("question_number") == q_num), None)
                if full_risk_item_with_plan and "de_risking_plan" in full_risk_item_with_plan:
                    derisking_plan_for_q = full_risk_item_with_plan["de_risking_plan"]
                    # If the risk_data_for_q was not found from risk_assessment_data_dict,
                    # but we found a match in derisking_strategies_data, use that as the risk_data too.
                    if risk_data_for_q is None:
                        risk_data_for_q = full_risk_item_with_plan
            
            # Fallback if risk_data_for_q is still None but we expect it (e.g. from derisking_strategies_data itself)
            if risk_data_for_q is None and derisking_strategies_data and isinstance(derisking_strategies_data, list):
                 risk_data_for_q = next((r for r in derisking_strategies_data if r.get("question_number") == q_num), None)


            final_questions_with_details_list.append({
                "question_data": fq_item,
                "risk_assessment_data": risk_data_for_q, # This will be the dict for the risk
                "derisking_plan": derisking_plan_for_q   # This is the sub-dict for the plan, or None
            })
    
    # Sort this list by question_number for consistent display in the report
    final_questions_with_details_list.sort(key=lambda x: x["question_data"].get("question_number", float('inf')))

    # Optional: Generate a brief executive summary text via LLM
    # executive_summary_text = generate_executive_summary(company_context, final_questions_with_details_list, strategic_reflection_data)
    # For now, we'll skip this to keep it simpler.

    template_data = {
        "company_context": company_context,
        "analysis_date": datetime.now().strftime("%Y-%m-%d"),
        "final_questions_with_details": final_questions_with_details_list,
        "strategic_reflection": strategic_reflection_data,
        # "executive_summary": executive_summary_text, # If generated
    }

    html_output_path = f"{output_base_filename}.html"
    pdf_output_path = f"{output_base_filename}.pdf"

    html_file = generate_html_report(template_data, output_html_file=html_output_path)
    if html_file:
        convert_html_to_pdf(html_file, output_pdf_file=pdf_output_path)
    
    print("Report generation attempt complete.")

# Optional: function to generate executive summary via LLM
# def generate_executive_summary(company_context, questions_details, reflection_data):
#     print("Generating executive summary via LLM...")
#     # ... (LLM call logic similar to other phases) ...
#     return "This is a placeholder executive summary. Key risks were identified regarding market adoption and regulatory hurdles. Strategic reflections point towards leveraging technological strengths while addressing market validation gaps."

if __name__ == '__main__':
    # This part is for testing reporting.py directly (optional)
    print("Testing reporting.py module...")
    # Create some dummy data to test report generation
    dummy_final_questions = [
        {"question_number": 1, "question_text": "Test Q1?", "reasoning": "Critical because test."},
        {"question_number": 2, "question_text": "Test Q2?", "reasoning": "Important for testing."},
    ]
    dummy_risk_assessment = {
        "risks": [
            {"question_number": 1, "risk_category": "Test Risk", "probability": 3, "impact": 4, "risk_score": 12, "risk_tier": "Medium", "justification": "Just a test."},
            {"question_number": 2, "risk_category": "Another Risk", "probability": 2, "impact": 2, "risk_score": 4, "risk_tier": "Low", "justification": "Low test risk."},
        ],
        "summary_stats": {}
    }
    dummy_derisking = [ # This is a list of risks, some might have de_risking_plan
        {
            "question_number": 1, 
            # ... other risk fields ...
            "de_risking_plan": {
                "research_strategies": [{"action_title": "Dummy Research", "description": "Do dummy research", "effort_level": "Low"}],
                "test_strategies": [], "act_strategies": []
            }
        },
        {
             "question_number": 2
             # ... no de_risking_plan for this one ...
        }
    ]

    dummy_reflection = {
        "i_like_reflection": ["Test like 1", "Test like 2"],
        "i_wish_reflection": ["Test wish 1"],
        "i_wonder_reflection": ["Test wonder 1", "Test wonder 2", "Test wonder 3"]
    }
    
    # Ensure your memo_template.html is in a 'templates' subdirectory next to reporting.py for this test
    # or in the current directory if the 'templates' dir logic above is used.
    if not os.path.exists("templates/memo_template.html") and os.path.exists("memo_template.html"):
        print("Moving memo_template.html to templates/ for test. Create this dir if it doesn't exist.")
        # Create templates dir if it doesn't exist
        if not os.path.exists("templates"):
            os.makedirs("templates")
        if os.path.exists("memo_template.html") and not os.path.exists("templates/memo_template.html"):
             os.rename("memo_template.html", "templates/memo_template.html")


    create_final_report(
        "Dummy Corp Test",
        dummy_final_questions,
        dummy_risk_assessment,
        dummy_derisking,
        dummy_reflection,
        output_base_filename="dummy_report_test"
    )
    print("Direct test of reporting.py complete.")