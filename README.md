# Email Guardian 🛡️

Advanced AI-powered email security scanner that detects spam and phishing attempts using machine learning and LLM validation.

## Features

- 🤖 **AI-Powered Detection**: DistilBERT model for accurate classification
- 🧠 **LLM Validation**: Optional Groq LLM for enhanced accuracy  
- 🌐 **Web Interface**: Simple HTML frontend
- 💻 **CLI Tool**: Command-line interface for batch processing
- 📊 **History**: Comprehensive scan history
- 🔒 **Secure**: API key authentication and input validation

## Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/OMARomd23/Email-Guardian.git
cd email-guardian
```
### 2. Download the model
```bash
pip install gdown
gdown 1u3oESbMvc-XD9iqwm0LN8JrteS6JbtuU
```

### 3. Set up the backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your configuration
```

### 4. Start the application
```bash
python app.py
```

### 5. Open the frontend
- Open `frontend/index.html` in your browser
- Configure API settings in the Settings tab

## Configuration

1. **Generate API Key:**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Update .env file:**
   ```bash
   API_KEY=your-generated-key-here
   GROQ_API_KEY=your-groq-key-here  # Optional
   ```

## API Endpoints

- `GET /health` - System health check
- `POST /api/scan` - Classify email content
- `GET /api/history` - Get scan history
- `GET /api/stats` - Get classification statistics

## License

MIT License - see [LICENSE](LICENSE) file for details.
You can freely use, modify, distribute, and sublicense the software.

