#!/usr/bin/env python3
"""
OCR Output Cleaner
Removes page separators and formatting artifacts to create a smooth flowing document.
"""

import re
import argparse
from pathlib import Path

def remove_repetitive_headers(content):
    """
    Remove repetitive headers, running titles, and publication info that appears on multiple pages.
    """
    lines = content.split('\n')
    seen_titles = {}
    result_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines but preserve them
        if not line:
            result_lines.append(lines[i])
            i += 1
            continue
        
        # Check if this looks like a repetitive header
        is_repetitive_header = False
        
        # Common patterns for running headers/titles
        patterns = [
            r'^#+ (LAUDATE|Laudate)$',  # Journal title
            r'^#+ QUARTERLY REVIEW',    # Running header
            r'^#+ (Vol\.|Volume) [IVX]+\.? No\. \d+',  # Volume info
            r'^\*\*(Vol\.|Volume) [IVX]+\.? No\. \d+\*\*',  # Bold volume info
            r'^\d{4}$',  # Year by itself
            r'^(MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER),? \d{4}$',  # Month/year
            r'^The Quarterly Review of',  # Publication description
            r'^By H\. Exc\. Mgr\.',  # Repeated author bylines
            r'^Price \d+s\. \d+d\.',  # Price information
            r'^\d+$',  # Page numbers
            r'^p\. \d+$',  # Page references
        ]
        
        # Check against patterns
        for pattern in patterns:
            if re.match(pattern, line, re.IGNORECASE):
                # Track how many times we've seen this exact line
                if line in seen_titles:
                    seen_titles[line] += 1
                    # If we've seen it before, it's likely a running header
                    if seen_titles[line] > 1:
                        is_repetitive_header = True
                        break
                else:
                    seen_titles[line] = 1
        
        # Special case: Remove repeated journal/publication titles after first occurrence
        if not is_repetitive_header:
            # Exact text matches for common repetitive elements
            repetitive_texts = [
                'LAUDATE',
                'Laudate', 
                'QUARTERLY REVIEW OF THE BENEDICTINES OF NASHDOM',
                'The Quarterly Review of the Benedictine Community at Nashdom Abbey, Burnham, Buckinghamshire',
                'Price 1s. 4s. 6d. per annum, post free.',
                'Etc., Etc., Etc.',
            ]
            
            for text in repetitive_texts:
                if line == text or line == f'# {text}' or line == f'## {text}':
                    if text in seen_titles:
                        seen_titles[text] += 1
                        if seen_titles[text] > 1:
                            is_repetitive_header = True
                            break
                    else:
                        seen_titles[text] = 1
        
        # If not a repetitive header, keep the line
        if not is_repetitive_header:
            result_lines.append(lines[i])
        else:
            print(f"   Removed repetitive header: {line[:50]}...")
        
        i += 1
    
    return '\n'.join(result_lines)

def clean_ocr_output(input_file, output_file=None):
    """
    Clean OCR output by removing page separators, repetitive headers, and unnecessary formatting.
    
    Args:
        input_file: Path to the OCR markdown file
        output_file: Optional output path (default: adds '_cleaned' suffix)
    """
    input_path = Path(input_file)
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    # Set output path
    if output_file:
        output_path = Path(output_file)
    else:
        output_path = input_path.parent / f"{input_path.stem}_cleaned{input_path.suffix}"
    
    print(f"📖 Reading: {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("🧹 Cleaning document...")
    
    # Remove the main OCR Results header
    content = re.sub(r'^# OCR Results\n\n', '', content, flags=re.MULTILINE)
    
    # Remove page headers like "## Pages X-X"
    content = re.sub(r'^## Pages \d+-\d+\n\n', '', content, flags=re.MULTILINE)
    
    # Remove markdown code block markers around content
    content = re.sub(r'^```markdown\n', '', content, flags=re.MULTILINE)
    content = re.sub(r'^```\n', '', content, flags=re.MULTILINE)
    
    # Remove horizontal separators between pages
    content = re.sub(r'\n---\n\n', '\n\n', content, flags=re.MULTILINE)
    content = re.sub(r'^---\n', '', content, flags=re.MULTILINE)
    
    # Remove repetitive headers and running titles
    print("🗑️ Removing repetitive headers...")
    content = remove_repetitive_headers(content)
    
    # Clean up excessive whitespace
    # Replace multiple consecutive newlines with double newlines
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # Remove leading/trailing whitespace
    content = content.strip()
    
    # Ensure document ends with single newline
    if not content.endswith('\n'):
        content += '\n'
    
    print(f"💾 Writing cleaned document: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Document cleaned successfully!")
    return str(output_path)

def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(description="Clean OCR output by removing page separators")
    parser.add_argument("input_file", help="Path to OCR markdown file")
    parser.add_argument("-o", "--output", help="Output file path (optional)")
    
    args = parser.parse_args()
    
    try:
        output_path = clean_ocr_output(args.input_file, args.output)
        print(f"\n🎉 Cleaned document saved to: {output_path}")
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())