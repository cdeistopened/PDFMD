#!/usr/bin/env python3
"""
Two-Column OCR Processor
Specialized for documents with two-column layouts per page.
"""

import os
import sys
from pathlib import Path
import logging
import base64
from typing import List

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

try:
    import fitz  # PyMuPDF
    from openai import OpenAI
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Install with: pip install PyMuPDF openai python-dotenv")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TwoColumnOCRProcessor:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.status_callback = None  # Optional callback for status updates

        # Simple prompt for two-column documents
        self.ocr_prompt = "Give me a clean Markdown-formatted transcription of this two-column PDF page. Read LEFT column first (top to bottom), then RIGHT column (top to bottom). Include all text and preserve structure."

    def extract_page_images(self, pdf_path: Path, start_page: int, end_page: int) -> List[bytes]:
        """Extract pages as images from PDF."""
        doc = fitz.open(pdf_path)
        images = []

        for page_num in range(start_page - 1, min(end_page, doc.page_count)):
            page = doc.load_page(page_num)
            mat = fitz.Matrix(2.5, 2.5)  # High resolution for column text
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            images.append(img_data)

        doc.close()
        return images

    def process_pages_batch(self, images: List[bytes], start_page: int) -> str:
        """Process pages with GPT-5 Mini."""
        messages = [{
            "role": "user",
            "content": [{"type": "text", "text": self.ocr_prompt}]
        }]

        # Add images to message
        for i, img_data in enumerate(images):
            img_b64 = base64.b64encode(img_data).decode('utf-8')
            page_num = start_page + i
            messages[0]["content"].append({
                "type": "text",
                "text": f"\n--- PAGE {page_num} ---\n"
            })
            messages[0]["content"].append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}"}
            })

        try:
            response = self.client.chat.completions.create(
                model="gpt-5-mini",
                max_completion_tokens=16000,
                messages=messages
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OCR processing failed: {e}")
            return f"Error processing pages {start_page}-{start_page + len(images) - 1}: {str(e)}"

    def process_pdf(self, pdf_path: str, start_page: int = 1, end_page: int = None, batch_size: int = 1) -> str:
        """Process PDF with two-column OCR."""
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Get page count
        doc = fitz.open(pdf_path)
        total_pages = doc.page_count
        doc.close()

        if end_page is None:
            end_page = total_pages

        logger.info(f"📄 Processing: {pdf_path.name}")
        logger.info(f"📊 Pages: {start_page} to {end_page} (total: {total_pages})")
        logger.info(f"🎯 Batch size: {batch_size}")

        output_file = pdf_path.parent / "two_column_output.md"
        logger.info(f"💾 Output: {output_file}")

        all_results = []

        # Process in batches
        for batch_start in range(start_page, end_page + 1, batch_size):
            batch_end = min(batch_start + batch_size - 1, end_page)

            logger.info(f"🔄 Processing batch: pages {batch_start}-{batch_end}")

            # Update status if callback provided
            if self.status_callback:
                self.status_callback(
                    batch_start,
                    total_pages,
                    f"Processing page {batch_start} of {total_pages}..."
                )

            try:
                # Extract images for this batch
                images = self.extract_page_images(pdf_path, batch_start, batch_end)

                # Process batch
                result = self.process_pages_batch(images, batch_start)
                all_results.append(result)

                logger.info(f"✅ Completed pages {batch_start}-{batch_end}")

            except Exception as e:
                logger.error(f"❌ Error processing batch {batch_start}-{batch_end}: {e}")
                all_results.append(f"\n## Error processing pages {batch_start}-{batch_end}\n{str(e)}\n")

        # Save combined results
        combined_result = "\n\n---\n\n".join(all_results)
        output_file.write_text(combined_result, encoding='utf-8')

        logger.info(f"🎉 Processing complete! Output: {output_file}")
        return str(output_file)

def main():
    """Command line interface."""
    import argparse

    parser = argparse.ArgumentParser(description="Two-Column PDF OCR → MD")
    parser.add_argument("pdf_file", help="PDF file to process")
    parser.add_argument("--start-page", type=int, default=1, help="Starting page")
    parser.add_argument("--end-page", type=int, help="Ending page")
    parser.add_argument("--batch-size", type=int, default=1, help="Pages per batch")

    args = parser.parse_args()

    try:
        processor = TwoColumnOCRProcessor()
        output_file = processor.process_pdf(
            args.pdf_file,
            start_page=args.start_page,
            end_page=args.end_page,
            batch_size=args.batch_size
        )

        print(f"\n🎉 Success! Output saved to: {output_file}")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
