# Email Guardian 🛡️

Advanced AI-powered email security scanner that detects spam and phishing attempts using machine learning and LLM validation.

## Overview

This project, **Email Guardian**, is a comprehensive AI-powered toolkit designed to provide robust email security by detecting spam and phishing attempts. It emphasizes leveraging artificial intelligence, practical Python usage, secure cloud backend development, and a user-friendly web interface. The solution integrates a fine-tuned DistilBERT model with  LLM validation for enhanced accuracy, offering a full-stack approach to email security.

## Features

-   **AI-Powered Detection**: At its core, Email Guardian utilizes a fine-tuned DistilBERT model for highly accurate multi-class email classification, distinguishing between legitimate, spam, and phishing emails.
-   **LLM Validation (Optional)**: For enhanced accuracy and nuanced threat detection, the system incorporates an optional integration with Groq LLM, providing an additional layer of validation.
-   **Web Interface**: A simple yet effective HTML frontend provides an intuitive user interface for submitting email content for scanning and viewing results.
-   **CLI Tool**: A command-line interface (`email_guard.py`) is available for batch processing and direct interaction, allowing users to scan email text and display classifications from the terminal.
-   **RESTful Backend & API**: The application features a robust Flask/FastAPI backend that handles scan requests (`/api/scan`), manages scan history (`/api/history`), and provides classification statistics (`/api/stats`).
-   **Secure**: Security is paramount, with features including API key authentication for controlled access to endpoints, input validation to prevent common web vulnerabilities, and secure deployment practices.
-   **Comprehensive History**: The system maintains a comprehensive scan history, allowing users to review past classifications and track potential threats.
-   **Containerization**: The backend is Dockerized, ensuring consistent and portable deployment across various environments.

## Quick Start

Follow these steps to get the Email Guardian up and running on your local machine.

### 1. Clone the repository

Begin by cloning the GitHub repository to your local machine:

```shell
git clone https://github.com/OMARomd23/Email-Guardian.git
cd email-guardian
```

### 2. Download the AI Model

The DistilBERT model used for classification needs to be downloaded separately. Ensure you have `gdown` installed, then use the provided command:

```shell
pip install gdown
gdown 1u3oESbMvc-XD9iqwm0LN8JrteS6JbtuU
```

### 3. Set up the Backend

Navigate to the `backend` directory, install the required Python dependencies, and configure your environment variables.

```shell
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your configuration (API_KEY, optional GROQ_API_KEY)
```

### 4. Start the Application

Once the backend is configured, you can start the Flask application:

```shell
python app.py
```

The backend API will typically be accessible at `http://localhost:5000`.

### 5. Open the Frontend

Open the `frontend/index.html` file in your web browser. You will need to configure the API settings within the frontend's Settings tab to point to your running backend (e.g., `http://localhost:5000`).

## Configuration

To ensure proper functionality and security, you need to configure API keys for the backend.

1.  **Generate API Key:**
    Generate a strong API key using Python:
    ```shell
    python -c "import secrets; print(secrets.token_urlsafe(32))"
    ```
    
2.  **Update .env file:**
    Edit the `.env` file in the `backend` directory with your generated API key and, optionally, your Groq API key if you plan to use the LLM validation feature.
    ```
    API_KEY=your-generated-key-here
    GROQ_API_KEY=your-groq-key-here  # Optional: Only if using LLM validation
    ```

## API Endpoints

The Email Guardian backend exposes the following RESTful API endpoints:

-   `GET /health`: A simple endpoint to check the system's health and availability.
-   `POST /api/scan`: Used to classify email content. Requires an API key for authentication.
-   `GET /api/history`: Retrieves the history of scanned emails. Requires an API key.

## Deployment

This project is designed for easy deployment on free-tier cloud platforms, demonstrating a practical approach to hosting full-stack applications.

-   **Frontend:** The web frontend was be deployed on [Vercel](https://vercel.com). Live example is available at [https://email-guardian-liard.vercel.app/](https://email-guardian-liard.vercel.app/).
-   **Backend:** The Flask/FastAPI backend, being Dockerized, can was deployed on the container-friendly platform [Railway](https://railway.app). The Docker image is hosted on Docker Hub (e.g., `omar669/email-guardian`).

## Security Considerations

Security is a core aspect of the Email Guardian. Key measures include:

-   **API Key Authentication:** All critical API endpoints (`/api/scan`, `/api/history`) are protected by API key authentication, ensuring only authorized access.
-   **HTTPS Hosting:** Both frontend and backend components are intended to be hosted over HTTPS to encrypt data in transit and protect against eavesdropping.
-   **Input Validation & Sanitization:** Input validation and sanitization are implemented on both the frontend and backend to prevent common web vulnerabilities like Cross-Site Scripting (XSS) and HTML injection.
-   **Environment Variables:** Sensitive information, such as API keys, is managed through environment variables, preventing their exposure in the codebase.

## AI Model Details

-   **Primary Model:** DistilBERT, a lightweight yet powerful transformer model from HuggingFace, forms the backbone of the email classification system.
-   **Classification Task:** The model is fine-tuned for a 3-class classification problem: `spam`, `phishing`, and `legitimate`.
-   **Output:** The model provides class probabilities, with the highest probability determining the final classification. This also provides a confidence score for each prediction.
-   **Training:** The model was trained over 5 epochs with CPU-safe settings. Specific hyperparameters and the detailed training process can be found in `Email-Guard_distilbert-fine-tuned.ipynb`.
-   **Performance:** At epoch 5, the model achieved an accuracy of 98.25% and similar Precision/Recall/F1 scores. It's noted that slight overfitting was observed, leading to some high-confidence outputs.

## Dataset Strategy

The effectiveness of the AI model relies on a carefully curated and balanced dataset. Multiple heterogeneous datasets were merged to achieve this:

-   **Legitimate Emails:** Approximately 92,690 samples.
-   **Spam Emails:** Approximately 40,396 samples.
-   **Phishing Emails:** Approximately 40,014 samples.

**Preprocessing steps** included unifying label formats, removing datasets that could introduce bias (e.g., overly preprocessed phishing sets), cleaning features to retain only text and label columns, and finally, merging and shuffling the combined dataset. Detailed steps are documented in `docs/Data_processing.ipynb`.

## Challenges Faced

During the development of Email Guardian, several challenges were encountered:

-   **Model Training & Data Bias:** Initial datasets led to misclassification of short tokens as phishing, necessitating extensive testing and re-curation of the dataset to mitigate bias.
-   **Overfitting:** The model exhibited high confidence outputs, indicating slight overfitting, likely due to the limited number of training epochs. This suggests a need for further regularization or more extensive validation.
-   **Limited 3-Class Models:** The scarcity of pre-trained models specifically for 3-class email classification required manual fine-tuning, adding complexity to the AI development phase.
-   **Multi-Platform Integration:** Managing and ensuring seamless integration across different cloud platforms (Vercel, Railway, Docker Hub) for frontend, backend, and container registry proved to be a significant coordination effort.

## Future Improvements

Potential enhancements for the Email Guardian include:

-   **Dataset Quality:** Utilizing higher-quality datasets, ideally with full raw email content, to provide richer contextual information for the model.
-   **Overfitting Mitigation:** Implementing strategies such as more epochs with early stopping, better validation sets, or data augmentation to reduce overfitting and improve generalization.
-   **Feature Expansion:** Adding advanced features like scan history visualization, detailed email header analysis, and real-time scan feedback.
-   **Integration:** Exploring extensions such as a browser plugin or direct Gmail integration for more seamless user experience.

## License

This project is released under the MIT License. See the [LICENSE](LICENSE) file in the repository for full details. You are free to use, modify, distribute, and sublicense the software.

