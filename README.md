# PDFMD

Transform scanned PDFs into perfectly formatted Markdown using AI-powered OCR. Built with Flask and designed for Railway deployment.

## ✨ Features

- **AI-Powered OCR**: Choose between GPT-5 Mini or Claude Haiku 4.5 for intelligent text extraction
- **Smart Layout Detection**: Handles complex documents, footnotes, tables, and multi-column layouts
- **Batch Processing**: Process multiple documents with automatic page chunking
- **Modern UI**: Clean, minimal interface with drag-and-drop file upload
- **Real-time Progress**: Live updates during document processing
- **Markdown Preview**: Preview extracted content before downloading

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- OpenAI API key and/or Anthropic API key

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/PDFMD.git
   cd PDFMD
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**

   Copy `.env.example` to `.env` and add your API keys:
   ```bash
   cp .env.example .env
   ```

   Edit `.env`:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

4. **Run the application**
   ```bash
   python run.py
   ```

   Open http://localhost:5000 in your browser

## 🎯 Usage

### Quick Process (Single Document)

1. Navigate to the home page
2. Drag and drop a PDF or click to upload
3. Select your AI model (GPT-5 Mini or Claude Haiku 4.5)
4. Click "Begin Processing"
5. Download or preview your Markdown file

### Workbench (Batch Processing)

1. Navigate to `/workbench`
2. Upload a PDF document
3. Set pages per batch (1-20)
4. Process automatically splits document into manageable chunks
5. Download individual batches or complete document

## 🤖 AI Models

| Model | Provider | Speed | Quality | Cost |
|-------|----------|-------|---------|------|
| **GPT-5 Mini** | OpenAI | Fast | Excellent | Low |
| **Claude Haiku 4.5** | Anthropic | Very Fast | Excellent | Lowest ($1/$5 per MTok) |

## 📁 Project Structure

```
PDFMD/
├── app.py                      # Main Flask application
├── run.py                      # Application launcher
├── chunked_ocr_processor.py    # Core OCR processing engine
├── auth.py                     # Authentication (optional)
├── billing.py                  # Billing/subscriptions (optional)
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
├── .gitignore                 # Git ignore rules
├── Procfile                   # Process file for deployment
├── railway.json               # Railway deployment config
├── nixpacks.toml             # Nixpacks build configuration
├── static/
│   ├── css/                  # Stylesheets (modernized design)
│   │   ├── base.css         # Base styles and design system
│   │   ├── index.css        # Home page styles
│   │   ├── workbench.css    # Workbench styles
│   │   └── auth.css         # Authentication styles
│   └── js/                   # Frontend JavaScript
│       ├── index.js         # Home page logic
│       ├── workbench.js     # Batch processing logic
│       └── auth.js          # Authentication logic
└── templates/                # Flask templates
    ├── index.html           # Home page (quick process)
    ├── workbench.html       # Batch processing interface
    └── auth.html            # Authentication page
```

## 🚂 Deployment to Railway

This app is optimized for Railway deployment with zero configuration needed.

### Automatic Deployment

1. **Push to GitHub**
   ```bash
   git push origin main
   ```

2. **Connect to Railway**
   - Go to [railway.app](https://railway.app)
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your PDFMD repository
   - Railway will auto-detect the configuration

3. **Add Environment Variables**

   In Railway dashboard, add:
   ```
   OPENAI_API_KEY=your_key_here
   ANTHROPIC_API_KEY=your_key_here
   ```

4. **Deploy!**
   - Railway automatically builds and deploys
   - Your app will be live in ~2-3 minutes

### Railway Configuration Files

- **`railway.json`**: Deployment settings (Nixpacks builder, restart policy)
- **`nixpacks.toml`**: Build configuration for Python
- **`Procfile`**: Process command (web: python run.py)

## 🔧 Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes* | OpenAI API key for GPT models |
| `ANTHROPIC_API_KEY` | Yes* | Anthropic API key for Claude models |
| `SUPABASE_URL` | No | Supabase project URL (if using auth) |
| `SUPABASE_ANON_KEY` | No | Supabase anon key (if using auth) |
| `STRIPE_SECRET_KEY` | No | Stripe secret key (if using billing) |

*At least one AI provider key is required

### API Keys

Get your API keys from:
- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/

## 🎨 Design System

The UI features a modern, minimalist design inspired by Apple's aesthetics:

- **Color Palette**: Refined stone and sage neutrals
- **Typography**: Inter font with optimized spacing
- **Components**: Floating cards with subtle shadows
- **Animations**: Smooth transitions with cubic-bezier easing
- **Responsive**: Mobile-friendly breakpoints

## 🧪 Development

### Running Tests

```bash
# Install dev dependencies
pip install pytest pytest-cov

# Run tests (when implemented)
pytest
```

### Code Structure

- **`app.py`**: Flask routes, file handling, job management
- **`chunked_ocr_processor.py`**: OCR processing logic, AI integration
- **`auth.py`**: Supabase authentication (optional)
- **`billing.py`**: Stripe billing integration (optional)

## 📊 How It Works

1. **Upload**: User uploads PDF via web interface
2. **Chunk**: PDF split into pages, converted to images
3. **Process**: Each page sent to AI model with optimized prompt
4. **Extract**: AI returns structured Markdown
5. **Combine**: Pages merged into final document
6. **Download**: User receives clean Markdown file

## 🛠️ Tech Stack

- **Backend**: Flask (Python)
- **OCR Engine**: PyMuPDF + PIL for image processing
- **AI Models**: OpenAI GPT-5 Mini, Anthropic Claude Haiku 4.5
- **Frontend**: Vanilla JavaScript, modern CSS
- **Deployment**: Railway (Nixpacks)
- **Optional**: Supabase (auth), Stripe (billing)

## 📝 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Home page (quick process) |
| `/workbench` | GET | Batch processing interface |
| `/auth` | GET | Authentication page |
| `/process` | POST | Process single document |
| `/upload` | POST | Upload document for batch processing |
| `/process-batch` | POST | Process batch of pages |
| `/job-status/<job_id>` | GET | Check processing status |
| `/download/<filename>` | GET | Download processed file |

## 🤝 Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License - see LICENSE file for details.

## 🙏 Acknowledgments

- Built with [Flask](https://flask.palletsprojects.com/)
- OCR powered by [OpenAI](https://openai.com/) and [Anthropic](https://anthropic.com/)
- Deployed on [Railway](https://railway.app/)

---

**Made with ❤️ for perfect PDF text extraction**
