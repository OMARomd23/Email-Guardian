import os
import json
import logging
from typing import Dict, Optional, Tuple
import time

logger = logging.getLogger(__name__)

# Try to import Groq with multiple fallback strategies
GROQ_AVAILABLE = False
GROQ_ERROR = None

def _test_groq_import():
    """Test Groq import with different strategies"""
    global GROQ_AVAILABLE, GROQ_ERROR
    
    try:
        # Strategy 1: Direct import
        from groq import Groq
        GROQ_AVAILABLE = True
        logger.info("Groq imported successfully")
        return Groq
    except ImportError as e:
        GROQ_ERROR = f"Groq package not installed: {e}"
        logger.warning(GROQ_ERROR)
        return None
    except Exception as e:
        GROQ_ERROR = f"Groq import error: {e}"
        logger.error(GROQ_ERROR)
        return None

def _create_groq_client(api_key: str):
    """Create Groq client with fallback strategies"""
    GroqClass = _test_groq_import()
    if not GroqClass:
        raise RuntimeError(f"Cannot import Groq: {GROQ_ERROR}")
    
    # Strategy 1: Standard initialization
    try:
        client = GroqClass(api_key=api_key)
        logger.info("Groq client created with standard initialization")
        return client
    except TypeError as e:
        if 'proxies' in str(e):
            logger.warning(f"Standard initialization failed: {e}")
        else:
            raise
    
    # Strategy 2: Minimal initialization (for older versions)
    try:
        import inspect
        sig = inspect.signature(GroqClass.__init__)
        params = list(sig.parameters.keys())
        logger.info(f"Groq client parameters: {params}")
        
        # Only pass api_key parameter
        client = GroqClass(api_key=api_key)
        logger.info("Groq client created with minimal initialization")
        return client
    except Exception as e:
        logger.error(f"Minimal initialization failed: {e}")
        raise
    
    # Strategy 3: Alternative initialization patterns
    try:
        # Some versions might expect different parameter names
        client = GroqClass(api_key=api_key, timeout=30)
        logger.info("Groq client created with timeout parameter")
        return client
    except Exception as e:
        logger.error(f"Alternative initialization failed: {e}")
        
    raise RuntimeError("All Groq client initialization strategies failed")

class GroqEmailValidator:
    """
    Groq LLM integration for email classification validation with robust error handling
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.1-8b-instant"):
        """
        Initialize Groq validator with multiple fallback strategies
        
        Args:
            api_key: Groq API key (if None, will use environment variable)
            model: Groq model to use for classification (default: llama-3.1-8b-instant)
        """
        self.api_key = api_key or os.getenv('GROQ_API_KEY')
        self.model = model
        self.client = None
        self.enabled = False
        self.error_message = None
        
        # Get Groq package info for debugging
        try:
            import groq
            logger.info(f"Groq package version: {groq.__version__}")
            logger.info(f"Groq package location: {groq.__file__}")
        except:
            pass
        
        if not self.api_key:
            self.error_message = "Groq API key not provided"
            logger.warning(f"{self.error_message} - LLM validation disabled")
            return
        
        try:
            logger.info("Attempting to create Groq client...")
            self.client = _create_groq_client(self.api_key)
            
            # Test the client with a minimal call
            self._test_client_basic()
            
            self.enabled = True
            logger.info(f"Groq validator successfully initialized with model: {self.model}")
            
        except Exception as e:
            self.error_message = str(e)
            logger.error(f"Failed to initialize Groq client: {e}")
            logger.info("LLM validation will be disabled")
            self.enabled = False
    
    def _test_client_basic(self):
        """Test basic client functionality"""
        try:
            # Just verify the client has the required attributes
            if not hasattr(self.client, 'chat'):
                raise Exception("Groq client missing 'chat' attribute")
            
            if not hasattr(self.client.chat, 'completions'):
                raise Exception("Groq client missing 'completions' attribute")
            
            logger.debug("Basic Groq client test passed")
            
        except Exception as e:
            logger.error(f"Basic client test failed: {e}")
            raise
    
    def validate_classification(self, text: str, primary_result: Dict) -> Dict:
        """
        Use Groq LLM to validate the primary classification
        
        Args:
            text: Email text to validate
            primary_result: Result from primary classifier
            
        Returns:
            Enhanced result with LLM validation
        """
        if not self.enabled:
            # Return original result with validation disabled status
            primary_result['llm_validation'] = {
                'enabled': False,
                'reason': self.error_message or 'Groq validator not available'
            }
            return primary_result
        
        try:
            llm_result = self._classify_with_llm(text)
            
            # Compare results
            validation_result = self._compare_classifications(primary_result, llm_result)
            
            # Add validation info to primary result
            primary_result['llm_validation'] = {
                'enabled': True,
                'llm_classification': llm_result['classification'],
                'llm_confidence': llm_result['confidence'],
                'llm_reasoning': llm_result['reasoning'],
                'agreement': validation_result['agreement'],
                'confidence_boost': validation_result['confidence_boost'],
                'final_confidence': validation_result['final_confidence'],
                'recommendation': validation_result['recommendation']
            }
            
            # Update final classification if LLM provides strong disagreement
            if validation_result['should_override']:
                primary_result['classification'] = llm_result['classification']
                primary_result['confidence'] = validation_result['final_confidence']
                primary_result['explanation'] += f" [LLM Override: {llm_result['reasoning']}]"
            
            return primary_result
            
        except Exception as e:
            logger.error(f"Error in LLM validation: {e}")
            primary_result['llm_validation'] = {
                'enabled': False,
                'error': str(e)
            }
            return primary_result
    
    def _classify_with_llm(self, text: str) -> Dict:
        """
        Classify email using Groq LLM
        
        Args:
            text: Email text to classify
            
        Returns:
            LLM classification result
        """
        if not self.enabled:
            raise RuntimeError("Groq client not available")
        
        # Truncate text if too long (Groq has token limits)
        max_chars = 8000
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        
        prompt = self._create_classification_prompt(text)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # Low temperature for consistent results
                max_tokens=500,
                timeout=30
            )
            
            result = self._parse_llm_response(response.choices[0].message.content)
            return result
            
        except Exception as e:
            logger.error(f"Error calling Groq API: {e}")
            raise
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for email classification"""
        return """You are an expert email security analyst specializing in identifying spam and phishing emails. 

Your task is to classify emails into one of three categories:
1. LEGITIMATE - Normal, safe emails
2. SPAM - Unsolicited promotional or marketing emails
3. PHISHING - Malicious emails attempting to steal credentials or personal information

For each classification, provide:
- Your classification (LEGITIMATE, SPAM, or PHISHING)
- Confidence level (0.0 to 1.0)
- Brief reasoning explaining your decision

Focus on key indicators:
- Phishing: Urgent language, credential requests, suspicious links, impersonation
- Spam: Promotional content, offers, unsolicited marketing
- Legitimate: Normal business/personal communication

Respond in JSON format:
{
  "classification": "LEGITIMATE|SPAM|PHISHING",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation"
}"""
    
    def _create_classification_prompt(self, text: str) -> str:
        """Create the classification prompt"""
        return f"""Please analyze this email and classify it:

EMAIL CONTENT:
{text}

Respond with your classification in the specified JSON format."""
    
    def _parse_llm_response(self, response: str) -> Dict:
        """Parse LLM response into structured format"""
        try:
            # Try to extract JSON from response
            response = response.strip()
            
            # Look for JSON block
            if '```json' in response:
                start = response.find('```json') + 7
                end = response.find('```', start)
                json_str = response[start:end].strip()
            elif '{' in response and '}' in response:
                start = response.find('{')
                end = response.rfind('}') + 1
                json_str = response[start:end]
            else:
                json_str = response
            
            result = json.loads(json_str)
            
            # Normalize classification
            classification = result.get('classification', 'LEGITIMATE').upper()
            if classification not in ['LEGITIMATE', 'SPAM', 'PHISHING']:
                classification = 'LEGITIMATE'
            
            # Ensure confidence is a float between 0 and 1
            confidence = float(result.get('confidence', 0.5))
            confidence = max(0.0, min(1.0, confidence))
            
            return {
                'classification': classification.lower(),
                'confidence': confidence,
                'reasoning': result.get('reasoning', 'No reasoning provided')
            }
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.debug(f"Raw response: {response}")
            
            # Fallback parsing
            response_lower = response.lower()
            if 'phishing' in response_lower:
                classification = 'phishing'
                confidence = 0.7
            elif 'spam' in response_lower:
                classification = 'spam'
                confidence = 0.7
            else:
                classification = 'legitimate'
                confidence = 0.6
            
            return {
                'classification': classification,
                'confidence': confidence,
                'reasoning': 'Fallback classification due to parsing error'
            }
    
    def _compare_classifications(self, primary: Dict, llm: Dict) -> Dict:
        """
        Compare primary and LLM classifications
        
        Args:
            primary: Primary classifier result
            llm: LLM classifier result
            
        Returns:
            Comparison analysis
        """
        primary_class = primary['classification']
        llm_class = llm['classification']
        primary_conf = primary['confidence']
        llm_conf = llm['confidence']
        
        # Check if classifications agree
        agreement = primary_class == llm_class
        
        # Calculate confidence boost/penalty
        if agreement:
            # Both agree - boost confidence
            confidence_boost = min(0.1, (llm_conf - 0.5) * 0.2)
            final_confidence = min(1.0, primary_conf + confidence_boost)
            should_override = False
            recommendation = f"Both classifiers agree on '{primary_class}' - confidence boosted"
        else:
            # Disagreement - need to decide
            confidence_diff = abs(llm_conf - primary_conf)
            
            if llm_conf > 0.8 and primary_conf < 0.6:
                # LLM is very confident, primary is not - consider override
                should_override = True
                final_confidence = (llm_conf + primary_conf) / 2
                recommendation = f"LLM strongly disagrees (LLM: {llm_class}, Primary: {primary_class}) - overriding"
            elif llm_conf > primary_conf + 0.2:
                # LLM is significantly more confident
                should_override = False
                final_confidence = (llm_conf + primary_conf) / 2
                recommendation = f"LLM disagrees but keeping primary classification with adjusted confidence"
            else:
                # Keep primary classification but lower confidence
                should_override = False
                confidence_penalty = min(0.2, confidence_diff * 0.5)
                final_confidence = max(0.1, primary_conf - confidence_penalty)
                recommendation = f"Classifiers disagree (LLM: {llm_class}, Primary: {primary_class}) - lowering confidence"
        
        return {
            'agreement': agreement,
            'confidence_boost': final_confidence - primary_conf,
            'final_confidence': final_confidence,
            'should_override': should_override,
            'recommendation': recommendation
        }
    
    def batch_validate(self, emails_and_results: list) -> list:
        """
        Validate multiple emails in batch
        
        Args:
            emails_and_results: List of (text, primary_result) tuples
            
        Returns:
            List of validated results
        """
        validated_results = []
        
        for text, primary_result in emails_and_results:
            # Add small delay to respect rate limits
            time.sleep(0.1)
            
            validated_result = self.validate_classification(text, primary_result.copy())
            validated_results.append(validated_result)
        
        return validated_results
    
    def test_connection(self) -> Dict:
        """
        Test the Groq connection
        
        Returns:
            Connection test result
        """
        if not self.enabled:
            return {
                'success': False,
                'error': self.error_message or 'Groq validator not enabled'
            }
        
        try:
            test_text = "This is a test email to verify the connection."
            result = self._classify_with_llm(test_text)
            
            return {
                'success': True,
                'model': self.model,
                'test_classification': result['classification'],
                'message': 'Groq connection successful'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

# Convenience function for easy integration
def create_groq_validator(api_key: Optional[str] = None, model: str = "llama-3.1-8b-instant") -> GroqEmailValidator:
    """
    Create a Groq validator instance
    
    Args:
        api_key: Groq API key (optional)
        model: Model to use (default: llama-3.1-8b-instant)
        
    Returns:
        GroqEmailValidator instance
    """
    return GroqEmailValidator(api_key, model)