#!/usr/bin/env python3
"""
PDF OCR → MD - Main OCR Processor

Transform any PDF into clean Markdown using GPT-5 Mini.
Optimized for complete text capture with simple prompts.
"""

import os
import sys
import argparse
import json
import base64
import io
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging
import tempfile

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Manual .env loading if python-dotenv not available
    env_file = Path('.env')
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

print("🔑 API Keys:", "✅ Loaded" if os.getenv("OPENAI_API_KEY") else "❌ Missing")

try:
    import fitz  # PyMuPDF
    from PIL import Image
    from openai import OpenAI
    import anthropic
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Install with: pip install PyMuPDF Pillow openai anthropic python-dotenv")
    sys.exit(1)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChunkedOCRProcessor:
    """
    PDF OCR → MD Processor
    Uses GPT-5 Mini with simple prompts for superior results.
    """

    def __init__(self, chunk_size: int = 1, output_dir: str = None, api_key: str = None, provider: str = "openai", model: str = None):
        """
        Initialize processor.

        Args:
            chunk_size: Pages per chunk (1 = one page at a time, recommended)
            output_dir: Output directory (default: same as input PDF)
            api_key: API key (or set OPENAI_API_KEY/ANTHROPIC_API_KEY env var)
            provider: AI provider - "openai" or "anthropic" (default: "openai")
            model: Model name (default: gpt-5-mini for OpenAI, claude-haiku-4.5 for Anthropic)
        """
        self.chunk_size = chunk_size
        self.output_dir = output_dir
        self.status_callback = None  # Optional callback for status updates
        self.provider = provider.lower()

        # Initialize AI client based on provider
        if self.provider == "openai":
            if api_key:
                self.client = OpenAI(api_key=api_key)
            elif os.getenv("OPENAI_API_KEY"):
                self.client = OpenAI()
            else:
                raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable.")
            self.model = model or "gpt-5-mini"

        elif self.provider == "anthropic":
            if api_key:
                self.client = anthropic.Anthropic(api_key=api_key)
            elif os.getenv("ANTHROPIC_API_KEY"):
                self.client = anthropic.Anthropic()
            else:
                raise ValueError("Anthropic API key required. Set ANTHROPIC_API_KEY environment variable.")
            self.model = model or "claude-haiku-4-5"
        else:
            raise ValueError(f"Unknown provider: {provider}. Use 'openai' or 'anthropic'")

        # Simple OCR prompt
        self.ocr_prompt = "Convert this PDF page to Markdown. Preserve all text, headings, and footnotes (use [^1] format)."

    def pdf_to_images(self, pdf_path: str, start_page: int = 0, end_page: int = None) -> list:
        """Convert PDF pages to images (no splitting by default)."""
        doc = fitz.open(pdf_path)
        images = []
        if end_page is None:
            end_page = len(doc) - 1

        for page_num in range(start_page, min(end_page + 1, len(doc))):
            page = doc.load_page(page_num)
            # High resolution for better OCR quality
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            images.append((page_num, 'single', img))

        doc.close()
        return images

    def image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 with compression if needed."""
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        img_data = buffer.getvalue()

        # Compress if too large (>4MB)
        if len(img_data) > 4 * 1024 * 1024:
            logger.info(f"Compressing large image ({len(img_data)} bytes)...")
            for quality in [85, 70, 60, 50]:
                buffer = io.BytesIO()
                if image.mode in ('RGBA', 'LA', 'P'):
                    rgb_image = image.convert('RGB')
                else:
                    rgb_image = image

                rgb_image.save(buffer, format='JPEG', quality=quality, optimize=True)
                img_data = buffer.getvalue()

                if len(img_data) <= 4 * 1024 * 1024:
                    logger.info(f"Compressed to {len(img_data)} bytes")
                    break

        return base64.b64encode(img_data).decode('utf-8')

    def analyze_page_chunk(self, images: list) -> dict:
        """
        Process page images using selected AI provider.
        Args: images: List of (page_number, 'single', PIL.Image) tuples
        Returns: Processing results
        """
        try:
            if self.provider == "openai":
                return self._analyze_with_openai(images)
            elif self.provider == "anthropic":
                return self._analyze_with_anthropic(images)
        except Exception as e:
            logger.error(f"Error processing pages: {str(e)}")
            return {
                "success": False,
                "pages": [(p, s) for p, s, _ in images],
                "error": str(e),
                "page_range": f"{images[0][0] + 1}-{images[-1][0] + 1}"
            }

    def _analyze_with_openai(self, images: list) -> dict:
        """Process with OpenAI GPT models."""
        messages = [{
            "role": "user",
            "content": [{"type": "text", "text": self.ocr_prompt}]
        }]

        # Add each image
        for page_num, side, image in images:
            img_b64 = self.image_to_base64(image)
            label = f"PAGE {page_num + 1}"
            messages[0]["content"].append({"type": "text", "text": f"\n\n--- {label} ---\n"})
            messages[0]["content"].append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}"}
            })

        response = self.client.chat.completions.create(
            model=self.model,
            max_completion_tokens=16000,
            messages=messages
        )

        return {
            "success": True,
            "pages": [(p, s) for p, s, _ in images],
            "text": response.choices[0].message.content,
            "page_range": f"{images[0][0] + 1}-{images[-1][0] + 1}"
        }

    def _analyze_with_anthropic(self, images: list) -> dict:
        """Process with Anthropic Claude models."""
        content = [{"type": "text", "text": self.ocr_prompt}]

        # Add each image
        for page_num, side, image in images:
            img_b64 = self.image_to_base64(image)
            label = f"PAGE {page_num + 1}"
            content.append({"type": "text", "text": f"\n\n--- {label} ---\n"})
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": img_b64,
                }
            })

        response = self.client.messages.create(
            model=self.model,
            max_tokens=16000,
            messages=[{"role": "user", "content": content}]
        )

        return {
            "success": True,
            "pages": [(p, s) for p, s, _ in images],
            "text": response.content[0].text,
            "page_range": f"{images[0][0] + 1}-{images[-1][0] + 1}"
        }

    def clean_llm_output(self, text: str) -> str:
        """Remove markdown code block wrappers from LLM output."""
        # Remove opening ```markdown and closing ```
        text = text.strip()
        if text.startswith('```markdown'):
            text = text[11:].strip()  # Remove ```markdown
        elif text.startswith('```'):
            text = text[3:].strip()   # Remove ```

        if text.endswith('```'):
            text = text[:-3].strip()  # Remove closing ```

        return text

    def save_chunk_result(self, result: Dict, output_file: str, chunk_index: int):
        """Save processing results to output file."""
        if result["success"]:
            # Clean the LLM output to remove code block wrappers
            cleaned_text = self.clean_llm_output(result["text"])

            with open(output_file, 'a', encoding='utf-8') as f:
                if chunk_index == 0:
                    f.write(f"# OCR Results\n\n")
                f.write(f"## Pages {result['page_range']}\n\n")
                f.write(cleaned_text)
                f.write("\n\n---\n\n")

            logger.info(f"✅ Pages {result['page_range']} completed")
        else:
            logger.error(f"❌ Pages {result['page_range']} failed: {result['error']}")

    def process_pdf(self, pdf_path: str, start_page: int = 0, max_pages: int = None, output_file_override: str = None) -> str:
        """
        Process entire PDF with GPT-5 Mini.

        Args:
            pdf_path: Path to PDF file
            start_page: Starting page (0-indexed)
            max_pages: Maximum pages to process (None for all)
            output_file_override: Custom output file path

        Returns:
            Path to output file
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        # Set up output
        if self.output_dir:
            output_dir = Path(self.output_dir)
        else:
            output_dir = pdf_path.parent

        output_dir.mkdir(exist_ok=True)

        if output_file_override:
            output_file = Path(output_file_override)
        else:
            output_file = output_dir / f"{pdf_path.stem}_ocr.md"

        # Clear output file if starting fresh
        if start_page == 0:
            output_file.write_text("", encoding='utf-8')

        # Get page count
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        doc.close()

        if max_pages:
            end_page = min(start_page + max_pages - 1, total_pages - 1)
        else:
            end_page = total_pages - 1

        logger.info(f"📄 Processing: {pdf_path.name}")
        logger.info(f"📊 Pages: {start_page + 1} to {end_page + 1} (total: {total_pages})")
        logger.info(f"🎯 Mode: {self.chunk_size} page(s) at a time")
        logger.info(f"💾 Output: {output_file}")

        # Process in chunks
        chunk_index = 0
        current_page = start_page

        while current_page <= end_page:
            chunk_end = min(current_page + self.chunk_size - 1, end_page)

            logger.info(f"🔄 Processing chunk {chunk_index + 1}: pages {current_page + 1}-{chunk_end + 1}")

            # Update status if callback provided
            if self.status_callback:
                self.status_callback(
                    current_page + 1,
                    total_pages,
                    f"Processing page {current_page + 1} of {total_pages}..."
                )

            try:
                # Get images for this chunk
                images = self.pdf_to_images(pdf_path, current_page, chunk_end)

                # Process with GPT-5 Mini
                result = self.analyze_page_chunk(images)

                # Save results
                self.save_chunk_result(result, output_file, chunk_index)

                current_page = chunk_end + 1
                chunk_index += 1

            except Exception as e:
                logger.error(f"❌ Error processing chunk {chunk_index + 1}: {str(e)}")
                current_page = chunk_end + 1
                chunk_index += 1

        logger.info(f"🎉 Processing complete! Output: {output_file}")
        return str(output_file)

def main():
    """Command line interface."""
    parser = argparse.ArgumentParser(description="PDF OCR → MD - Transform PDFs to Markdown")
    parser.add_argument("pdf_file", help="PDF file to process")
    parser.add_argument("--chunk-size", type=int, default=1, help="Pages per chunk (default: 1)")
    parser.add_argument("--start-page", type=int, default=1, help="Starting page (1-indexed)")
    parser.add_argument("--max-pages", type=int, help="Maximum pages to process")
    parser.add_argument("--output-dir", help="Output directory")
    parser.add_argument("--output-file", help="Output file path")

    args = parser.parse_args()

    # Convert to 0-indexed
    start_page = args.start_page - 1

    try:
        processor = ChunkedOCRProcessor(
            chunk_size=args.chunk_size,
            output_dir=args.output_dir
        )

        output_file = processor.process_pdf(
            args.pdf_file,
            start_page=start_page,
            max_pages=args.max_pages,
            output_file_override=args.output_file
        )

        print(f"\n🎉 Success! Output saved to: {output_file}")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
