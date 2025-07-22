import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import numpy as np
import logging
from typing import Dict, List
import re

logger = logging.getLogger(__name__)

class EmailClassifier:
    """
    Email classification handler using DistilBERT model
    """
    
    def __init__(self, model_path: str):
        """
        Initialize the classifier with a pre-trained model
        
        Args:
            model_path: Path to the saved model directory
        """
        self.model_path = model_path
        self.model = None
        self.tokenizer = None
        self.label_map = {0: "legitimate", 1: "spam", 2: "phishing"}
        self.max_length = 512  # DistilBERT max sequence length
        
        self.load_model()
    
    def load_model(self):
        """Load the model and tokenizer"""
        try:
            logger.info(f"Loading model from {self.model_path}")
            
            # Load tokenizer and model
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_path)
            
            # Set model to evaluation mode
            self.model.eval()
            
            # Disable gradients for inference (saves memory and speeds up)
            for param in self.model.parameters():
                param.requires_grad = False
            
            logger.info("Model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            # Fallback to a simple rule-based classifier for demonstration
            logger.warning("Using fallback rule-based classifier")
            self.model = None
            self.tokenizer = None
    
    def preprocess_text(self, text: str) -> str:
        """
        Clean and preprocess email text
        
        Args:
            text: Raw email text
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove email headers (basic cleanup)
        text = re.sub(r'^(From|To|Subject|Date|Reply-To):\s*.*$', '', text, flags=re.MULTILINE)
        
        # Remove URLs (optional - you might want to keep them for phishing detection)
        # text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '[URL]', text)
        
        # Strip and limit length
        text = text.strip()
        
        return text
    
    def classify(self, text: str) -> Dict:
        """
        Classify an email text
        
        Args:
            text: Email content to classify
            
        Returns:
            Dictionary containing classification results
        """
        # Preprocess text
        processed_text = self.preprocess_text(text)
        
        if self.model is None or self.tokenizer is None:
            # Fallback rule-based classification
            return self._rule_based_classify(processed_text)
        
        try:
            # Tokenize input
            inputs = self.tokenizer(
                processed_text,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=self.max_length
            )
            
            # Get model predictions
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
            
            # Apply softmax to get probabilities
            probabilities = torch.softmax(logits, dim=-1)
            
            # Get predictions
            predicted_class = torch.argmax(probabilities, dim=-1).item()
            confidence = probabilities[0][predicted_class].item()
            
            # Create probability dictionary
            prob_dict = {}
            for i, label in self.label_map.items():
                prob_dict[label] = round(probabilities[0][i].item(), 4)
            
            result = {
                "classification": self.label_map[predicted_class],
                "confidence": round(confidence, 4),
                "probabilities": prob_dict,
                "explanation": self._generate_explanation(
                    self.label_map[predicted_class], 
                    confidence,
                    processed_text
                )
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error during classification: {str(e)}")
            # Return fallback classification
            return self._rule_based_classify(processed_text)
    
    def _rule_based_classify(self, text: str) -> Dict:
        """
        Simple rule-based classifier as fallback
        
        Args:
            text: Email text to classify
            
        Returns:
            Classification result
        """
        text_lower = text.lower()
        
        # Phishing indicators
        phishing_keywords = [
            'urgent', 'verify account', 'click here', 'suspended', 'confirm identity',
            'update payment', 'security alert', 'act now', 'limited time', 'verify now'
        ]
        
        # Spam indicators
        spam_keywords = [
            'free', 'winner', 'congratulations', 'prize', 'offer', 'deal',
            'discount', 'save money', 'earn money', 'work from home'
        ]
        
        phishing_score = sum(1 for keyword in phishing_keywords if keyword in text_lower)
        spam_score = sum(1 for keyword in spam_keywords if keyword in text_lower)
        
        if phishing_score > 2:
            classification = "phishing"
            confidence = min(0.7 + (phishing_score * 0.05), 0.95)
            probabilities = {"legitimate": 0.1, "spam": 0.2, "phishing": confidence}
        elif spam_score > 2:
            classification = "spam"
            confidence = min(0.6 + (spam_score * 0.05), 0.9)
            probabilities = {"legitimate": 0.2, "spam": confidence, "phishing": 0.1}
        else:
            classification = "legitimate"
            confidence = 0.7
            probabilities = {"legitimate": confidence, "spam": 0.2, "phishing": 0.1}
        
        # Normalize probabilities
        total = sum(probabilities.values())
        probabilities = {k: round(v/total, 4) for k, v in probabilities.items()}
        
        return {
            "classification": classification,
            "confidence": round(confidence, 4),
            "probabilities": probabilities,
            "explanation": self._generate_explanation(classification, confidence, text)
        }
    
    def _generate_explanation(self, classification: str, confidence: float, text: str) -> str:
        """
        Generate explanation for the classification
        
        Args:
            classification: Predicted class
            confidence: Confidence score
            text: Original text
            
        Returns:
            Human-readable explanation
        """
        explanations = {
            "legitimate": f"This email appears to be legitimate with {confidence:.1%} confidence. "
                         "The content follows normal email patterns without suspicious indicators.",
            
            "spam": f"This email is classified as spam with {confidence:.1%} confidence. "
                   "It likely contains promotional content or unsolicited offers.",
            
            "phishing": f"This email is classified as phishing with {confidence:.1%} confidence. "
                       "It may contain attempts to steal personal information or credentials."
        }
        
        base_explanation = explanations.get(classification, "Unable to classify this email.")
        
        # Add additional context based on content analysis
        if "urgent" in text.lower() and classification == "phishing":
            base_explanation += " The email uses urgency tactics commonly found in phishing attempts."
        elif "free" in text.lower() and classification == "spam":
            base_explanation += " The email contains promotional language typical of spam messages."
        
        return base_explanation
    
    def batch_classify(self, texts: List[str]) -> List[Dict]:
        """
        Classify multiple emails at once
        
        Args:
            texts: List of email texts to classify
            
        Returns:
            List of classification results
        """
        results = []
        for text in texts:
            result = self.classify(text)
            results.append(result)
        
        return results