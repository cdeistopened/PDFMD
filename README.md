# PDF OCR → MD

Transform any PDF into clean, structured Markdown using AI-powered OCR.

## 🚀 Features

- **Smart OCR**: Uses GPT-5 Mini and GPT-4 Vision for superior text extraction
- **Layout Intelligence**: Handles single columns, double columns, and mixed layouts
- **Complete Capture**: Never misses footnotes, headers, or small text
- **Perfect Markdown**: Outputs clean, properly formatted Markdown
- **Drag & Drop**: Simple web interface with drag-and-drop upload
- **Free Tier**: Process up to 10 pages free, no signup required

## 🎯 Perfect For

- Academic papers and journals
- Historical documents  
- Technical reports
- Multi-column layouts
- Documents with footnotes and citations

## 🔧 Quick Start

### Option 1: Web Interface (Easiest)

1. Open `index.html` in your browser
2. Drag and drop your PDF
3. Select processing mode and AI model
4. Download your Markdown file

### Option 2: Run Complete App Locally

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up API keys:**
   Create a `.env` file:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   ANTHROPIC_API_KEY=your_anthropic_api_key_here  
   ```

3. **Start the web server:**
   ```bash
   python app.py
   # Or use: python run.py
   ```
   Opens at http://localhost:5000

4. **Command line processing:**
   ```bash
   python chunked_ocr_processor.py your_document.pdf
   ```

## 🎛️ Processing Modes

| Mode | Best For | Description |
|------|----------|-------------|
| **Smart OCR** | Most documents | One page at a time, handles all layouts |
| **Two-Column** | Academic papers | Specialized for two-column documents |
| **Single Page** | Simple documents | Basic single-page processing |

## 🤖 AI Models

| Model | Speed | Quality | Cost |
|-------|--------|---------|------|
| **GPT-5 Mini** | ⚡ Fastest | ⭐⭐⭐⭐⭐ | 💰 Low |
| **GPT-4 Vision** | ⚡ Fast | ⭐⭐⭐⭐⭐ | 💰💰 Medium |
| **Claude Haiku** | ⚡⚡ Very Fast | ⭐⭐⭐⭐ | 💰 Lowest |

## 📁 Project Structure

```
pdf-ocr-md/
├── index.html              # Web interface
├── chunked_ocr_processor.py # Main OCR engine
├── two_column_ocr_processor.py
├── requirements.txt        # Python dependencies
├── .env.example           # API keys template
├── netlify.toml           # Deployment config
└── README.md              # This file
```

## 🔑 API Keys Required

Get your API keys from:

- **OpenAI GPT-4/GPT-5**: https://platform.openai.com/api-keys
- **Anthropic Claude**: https://console.anthropic.com/

Add to `.env` file:
```env
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
```

## 📊 Example Results

**Input**: Scanned academic PDF with two columns, footnotes, and complex formatting

**Output**: 
```markdown
# The Light of the East

## March 1924

Nature therefore is "for another." It is but a means. It is an instrument by which, as we shall see, God punishes, rewards, teaches and educates the soul.

### Footnotes

(1) According to us, those who hold that states (or modes) are incapable...
```

## 🚀 Deployment

### Netlify (Static Site)

1. Push to GitHub
2. Connect repository to Netlify  
3. Set build command: `echo "Static site"` 
4. Set publish directory: `/`
5. Add environment variables in Netlify dashboard
6. Deploy!

### Local Server

```bash
python simple_local_app.py
```

Opens at http://localhost:8080

## 🛠️ Development

**Current Status**: 
- ✅ GPT-5 Mini integration
- ✅ One-page-at-a-time processing
- ✅ 16k token limit for complete capture  
- ✅ Simple, effective prompts
- ✅ Drag & drop web interface

## 📄 License

MIT License - see LICENSE file for details.

---

Made with ❤️ for perfect PDF text extraction