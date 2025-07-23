# Email Guardian 🛡️

**Advanced AI-powered email security scanner that detects spam and phishing attempts using machine learning and LLM validation.**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Available-brightgreen)](https://email-guardian-liard.vercel.app/)
[![Docker Hub](https://img.shields.io/badge/Docker%20Hub-omar669%2Femail--guardian-blue)](https://hub.docker.com/r/omar669/email-guardian)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🎯 Overview

Email Guardian is a comprehensive AI-powered toolkit designed to provide robust email security by detecting spam and phishing attempts. It leverages a fine-tuned DistilBERT model with optional LLM validation for enhanced accuracy, offering a full-stack approach to email security with a user-friendly web interface and secure cloud backend.

## ✨ Features

- **🤖 AI-Powered Detection**: Fine-tuned DistilBERT model for highly accurate multi-class email classification
- **🔍 LLM Validation**: Optional integration with Groq LLM for enhanced threat detection
- **🌐 Web Interface**: Intuitive HTML frontend with scan, history, and settings tabs
- **⚡ CLI Tool**: Command-line interface for batch processing and direct interaction
- **🔒 Secure API**: RESTful backend with API key authentication and input validation
- **📊 Comprehensive History**: Track and review past classifications and potential threats
- **🐳 Containerized**: Dockerized backend for consistent deployment across environments

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Git
- Docker (optional, for local backend deployment)

### 1. Clone the Repository

```bash
git clone https://github.com/OMARomd23/Email-Guardian.git
cd Email-Guardian
```

### 2. Download the AI Model

```bash
pip install gdown
gdown 1u3oESbMvc-XD9iqwm0LN8JrteS6JbtuU
```

### 3. Set Up the Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your configuration
```

### 4. Start the Application

```bash
python app.py
```

The backend API will be accessible at `http://localhost:5000`.

### 5. Access the Frontend

Open `frontend/index.html` in your web browser or visit the live demo at:

**🌐 [https://email-guardian-liard.vercel.app/](https://email-guardian-liard.vercel.app/)**

## 🔑 API Configuration

To use the hosted version:

- **API Key**: `contact_me_for_an_api_key`
- **Backend URL**: `https://email-guardian-production.up.railway.app`

Enter these credentials in the **Settings** tab of the web interface.

## 🛠️ Usage

### Web Interface

1. Visit the web application
2. Go to **Settings** tab and enter your API key and backend URL
3. Navigate to **Scan** tab
4. Enter email content and click "Scan Email"
5. View results and check **History** tab for past scans

### CLI Tool

```bash
cd ai
python email_guard.py --text "Your email content here"
```

**Example Output:**
```json
{
  "classification": "phishing",
  "confidence": 0.98,
  "probabilities": {
    "spam": 0.01,
    "phishing": 0.98,
    "legitimate": 0.01
  }
}
```

## 📡 API Endpoints

The Email Guardian backend exposes the following RESTful API endpoints:

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/health` | GET | System health check | No |
| `/api/scan` | POST | Classify email content | Yes |
| `/api/history` | GET | Retrieve scan history | Yes |
| `/api/stats` | GET | Get classification statistics | Yes |

### Example API Request

```bash
curl -X POST "https://email-guardian-production.up.railway.app/api/scan" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: SEG-RICHDALE-2025-APIKEY-48F7A1" \
  -d '{"text": "Congratulations! You have won $1,000,000. Click here to claim your prize!"}'
```

## 🤖 AI Model Details

### Model Architecture
- **Base Model**: DistilBERT (lightweight transformer from HuggingFace)
- **Task**: 3-class classification (spam, phishing, legitimate)
- **Output**: Class probabilities with confidence scores

### Training Configuration
```python
TrainingArguments(
    output_dir="./results",
    eval_strategy="epoch",
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    num_train_epochs=5,
    weight_decay=0.01,
    gradient_accumulation_steps=2,
    fp16=True
)
```

### Performance Metrics
- **Final Accuracy**: 98.25%
- **Precision**: 98.26%
- **Recall**: 98.26%
- **F1-Score**: 98.26%

## 📊 Dataset Information

The model was trained on a carefully curated and balanced dataset:

| Class | Samples |
|-------|---------|
| Legitimate | 92,690 |
| Spam | 40,396 |
| Phishing | 40,014 |

**Data Sources:**
- Enron Spam Dataset
- CEAS Spam Dataset
- SpamAssassin Dataset
- ealvaradob/phishing-dataset (HuggingFace)
- Phishing dataset from Kaggle

## 🏗️ Project Structure

```
Email-Guardian/
├── ai/
│   └── email_guard.py          # CLI tool
├── backend/
│   ├── app.py                  # Flask application
│   ├── model_handler.py        # AI model wrapper
│   ├── database.py             # Database management
│   ├── groq_validator.py       # LLM validation
│   ├── requirements.txt        # Python dependencies
│   └── Dockerfile              # Container configuration
├── frontend/
│   ├── index.html              # Web interface
│   ├── script.js               # Frontend logic
│   └── style.css               # Styling
├── docs/
│   ├── README.md               # This file
│   └── security_notes.md       # Security documentation
├── requirements.txt            # Root dependencies
└── reflection.md               # Project reflection
```

## 🚀 Deployment

### Frontend (Vercel)
The web frontend is deployed on Vercel for global accessibility and optimal performance.

### Backend (Railway + Docker)
The backend runs as a Docker container on Railway, with the image hosted on Docker Hub.

**Docker Image**: `omar669/email-guardian`

### Local Deployment with Docker

```bash
# Build the image
docker build -t email-guardian ./backend

# Run the container
docker run -p 5000:5000 -e API_KEY=your-api-key email-guardian
```

## 🔒 Security Features

- **API Key Authentication**: All critical endpoints require valid API keys
- **Input Validation**: Comprehensive validation and sanitization of user inputs
- **HTTPS Deployment**: Both frontend and backend use secure HTTPS connections
- **Rate Limiting**: Protection against abuse with configurable rate limits
- **Environment Variables**: Sensitive configuration managed through environment variables

## 🧪 Testing

Run the test suite:

```bash
cd backend
python -m pytest tests/ -v
```

## 📈 Performance Monitoring

The application includes:
- Health check endpoints for monitoring
- Comprehensive logging for debugging
- Classification statistics tracking
- Scan history with metadata

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- HuggingFace for the DistilBERT model and datasets
- Railway and Vercel for hosting platforms
- The open-source community for various datasets used in training

## 📞 Contact

**OUMESSAOUD Omar**
- Email: oumessaoud-omar@proton.me
- LinkedIn: [Profile](https://linkedin.com/in/your-profile)
- GitHub: [@OMARomd23](https://github.com/OMARomd23)

---

*Built with ❤️ for enhanced email security*
