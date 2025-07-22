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

3. **Test the setup:**
   ```bash
   python scripts/setup_email_guardian.py --test-only
   ```

## API Endpoints

- `GET /health` - System health check
- `POST /api/scan` - Classify email content
- `GET /api/history` - Get scan history
- `GET /api/stats` - Get classification statistics

## Security

- Never commit `.env` files to version control
- Generate secure API keys for production
- Use HTTPS in production environments
- Regularly rotate API keys

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

If you encounter issues:
1. Check the [troubleshooting guide](docs/troubleshooting.md)
2. Review [API documentation](docs/api.md)
3. Open an issue on GitHub
