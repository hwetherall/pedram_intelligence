import os
import argparse
from intelligence_question_generator import extract_text_from_pdf

def main():
    """Test the PDF extraction functionality."""
    parser = argparse.ArgumentParser(description="Test PDF text extraction.")
    parser.add_argument("pdf_path", help="Path to the PDF file to test.")
    args = parser.parse_args()
    
    if not os.path.exists(args.pdf_path):
        print(f"Error: The PDF file '{args.pdf_path}' does not exist.")
        return
    
    print(f"Extracting text from '{args.pdf_path}'...")
    text = extract_text_from_pdf(args.pdf_path)
    
    # Calculate stats
    word_count = len(text.split())
    line_count = len(text.splitlines())
    
    print(f"\nExtraction Results:")
    print(f"Word Count: {word_count}")
    print(f"Line Count: {line_count}")
    
    # Preview the extracted text
    preview_length = min(500, len(text))
    print(f"\nPreview of extracted text (first {preview_length} characters):")
    print("-" * 80)
    print(text[:preview_length] + "..." if len(text) > preview_length else text)
    print("-" * 80)
    
    # Ask to save the complete extraction
    save = input("Save the complete extracted text to a file? (y/n): ").strip().lower()
    if save == 'y':
        output_file = f"{os.path.splitext(os.path.basename(args.pdf_path))[0]}_extracted.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"Extracted text saved to '{output_file}'")

if __name__ == "__main__":
    main() 