#!/usr/bin/env python3
"""
Email Guardian CLI Tool
A command-line interface for the Smart Email Guardian spam/phishing detection system.
"""

import argparse
import json
import sys
import os
from typing import Dict, Optional
import requests
from pathlib import Path

# Add the backend directory to the path for local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from model_handler import EmailClassifier
    LOCAL_MODE_AVAILABLE = True
except ImportError:
    LOCAL_MODE_AVAILABLE = False

class EmailGuardCLI:
    """Command-line interface for Email Guardian"""
    
    def __init__(self):
        self.config = self.load_config()
        self.classifier = None
        
    def load_config(self) -> Dict:
        """Load configuration from file or environment"""
        config = {
            'api_url': os.getenv('EMAIL_GUARD_API_URL', 'http://localhost:5000'),
            'api_key': os.getenv('API_KEY', 'your_api_key'),
            'model_path': os.getenv('EMAIL_GUARD_MODEL_PATH', './my-3class-model'),
            'timeout': int(os.getenv('EMAIL_GUARD_TIMEOUT', '30'))
        }
        
        # Try to load from config file
        config_file = Path.home() / '.email_guard_config.json'
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                    config.update(file_config)
            except Exception as e:
                print(f"Warning: Could not load config file: {e}", file=sys.stderr)
        
        return config
    
    def save_config(self):
        """Save current configuration to file"""
        config_file = Path.home() / '.email_guard_config.json'
        try:
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            print(f"Configuration saved to: {config_file}")
        except Exception as e:
            print(f"Error saving configuration: {e}", file=sys.stderr)
    
    def classify_local(self, text: str) -> Dict:
        """Classify email using local model"""
        if not LOCAL_MODE_AVAILABLE:
            raise RuntimeError("Local mode not available. Install required dependencies or use API mode.")
        
        if self.classifier is None:
            print("Loading local model...", file=sys.stderr)
            try:
                self.classifier = EmailClassifier(self.config['model_path'])
            except Exception as e:
                raise RuntimeError(f"Failed to load local model: {e}")
        
        return self.classifier.classify(text)
    
    def classify_api(self, text: str, use_llm: bool = False) -> Dict:
        """Classify email using API endpoint"""
        url = f"{self.config['api_url'].rstrip('/')}/api/scan"
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': self.config['api_key']
        }
        
        payload = {
            'text': text,
            'use_llm_validation': use_llm
        }
        
        try:
            response = requests.post(
                url, 
                json=payload, 
                headers=headers, 
                timeout=self.config['timeout']
            )
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.ConnectionError:
            raise RuntimeError(f"Could not connect to API at {url}")
        except requests.exceptions.Timeout:
            raise RuntimeError("API request timed out")
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise RuntimeError("Invalid API key")
            elif response.status_code == 429:
                raise RuntimeError("Rate limit exceeded")
            else:
                raise RuntimeError(f"API error: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error: {e}")
    
    def test_groq_connection(self) -> Dict:
        """Test Groq LLM connection via API"""
        url = f"{self.config['api_url'].rstrip('/')}/api/groq-test"
        headers = {'X-API-Key': self.config['api_key']}
        
        try:
            response = requests.get(url, headers=headers, timeout=self.config['timeout'])
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise RuntimeError(f"Failed to test Groq connection: {e}")
    
    def classify_text(self, text: str, use_api: bool = False, use_llm: bool = False) -> Dict:
        """Classify email text using specified method"""
        if use_api:
            return self.classify_api(text, use_llm=use_llm)
        else:
            if use_llm:
                print("Warning: LLM validation only available in API mode", file=sys.stderr)
            return self.classify_local(text)
    
    def read_input(self, source: str) -> str:
        """Read input from file, stdin, or direct text"""
        if source == '-':
            # Read from stdin
            return sys.stdin.read().strip()
        elif os.path.isfile(source):
            # Read from file
            try:
                with open(source, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except Exception as e:
                raise RuntimeError(f"Could not read file {source}: {e}")
        else:
            # Treat as direct text
            return source.strip()
    
    def format_output(self, result: Dict, format_type: str = 'json') -> str:
        """Format classification result"""
        if format_type == 'json':
            return json.dumps(result, indent=2)
        
        elif format_type == 'simple':
            return f"{result['classification']} ({result['confidence']:.2%})"
        
        elif format_type == 'detailed':
            output = [
                f"Classification: {result['classification']}",
                f"Confidence: {result['confidence']:.2%}",
                f"Probabilities:",
            ]
            
            for label, prob in result['probabilities'].items():
                output.append(f"  {label}: {prob:.2%}")
            
            if 'explanation' in result:
                output.extend(["", f"Explanation: {result['explanation']}"])
            
            # Add LLM validation info if available
            if 'llm_validation' in result:
                llm_val = result['llm_validation']
                output.extend(["", "LLM Validation:"])
                
                if llm_val.get('enabled', False):
                    output.append(f"  LLM Classification: {llm_val.get('llm_classification', 'N/A')}")
                    output.append(f"  LLM Confidence: {llm_val.get('llm_confidence', 0):.2%}")
                    output.append(f"  Agreement: {'Yes' if llm_val.get('agreement', False) else 'No'}")
                    output.append(f"  Recommendation: {llm_val.get('recommendation', 'N/A')}")
                    if 'llm_reasoning' in llm_val:
                        output.append(f"  LLM Reasoning: {llm_val['llm_reasoning']}")
                else:
                    reason = llm_val.get('reason', llm_val.get('error', 'Unknown'))
                    output.append(f"  Status: Disabled ({reason})")
            
            return '\n'.join(output)
        
        else:
            raise ValueError(f"Unknown format type: {format_type}")
    
    def get_history(self, limit: int = 10) -> Dict:
        """Get scan history from API"""
        url = f"{self.config['api_url'].rstrip('/')}/api/history"
        headers = {'X-API-Key': self.config['api_key']}
        params = {'limit': limit}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=self.config['timeout'])
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise RuntimeError(f"Failed to get history: {e}")
    
    def get_stats(self) -> Dict:
        """Get classification statistics from API"""
        url = f"{self.config['api_url'].rstrip('/')}/api/stats"
        headers = {'X-API-Key': self.config['api_key']}
        
        try:
            response = requests.get(url, headers=headers, timeout=self.config['timeout'])
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise RuntimeError(f"Failed to get stats: {e}")

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Email Guardian - AI-powered spam and phishing detection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s "This is a test email"
  %(prog)s --file email.txt
  cat email.txt | %(prog)s -
  %(prog)s --api "Check this email" --format simple
  %(prog)s --api --llm "Suspicious email content" --format detailed
  %(prog)s --test-groq
  %(prog)s --history --limit 5
  %(prog)s --stats
  %(prog)s --config api_url http://my-server.com:5000
        '''
    )
    
    # Main operation arguments
    parser.add_argument(
        'text', 
        nargs='?', 
        help='Email text to classify (use "-" to read from stdin, or specify a file path)'
    )
    
    parser.add_argument(
        '--file', 
        help='Read email text from file'
    )
    
    parser.add_argument(
        '--api', 
        action='store_true',
        help='Use API instead of local model'
    )
    
    parser.add_argument(
        '--llm', 
        action='store_true',
        help='Enable LLM validation (requires --api and Groq API key)'
    )
    
    parser.add_argument(
        '--format', 
        choices=['json', 'simple', 'detailed'],
        default='json',
        help='Output format (default: json)'
    )
    
    # History and stats
    parser.add_argument(
        '--history', 
        action='store_true',
        help='Show recent scan history'
    )
    
    parser.add_argument(
        '--stats', 
        action='store_true',
        help='Show classification statistics'
    )
    
    parser.add_argument(
        '--limit', 
        type=int,
        default=10,
        help='Limit for history results (default: 10)'
    )
    
    # Configuration
    parser.add_argument(
        '--config', 
        nargs=2, 
        metavar=('KEY', 'VALUE'),
        help='Set configuration value (api_url, api_key, model_path, timeout)'
    )
    
    parser.add_argument(
        '--show-config', 
        action='store_true',
        help='Show current configuration'
    )
    
    parser.add_argument(
        '--test-groq', 
        action='store_true',
        help='Test Groq LLM connection'
    )
    
    parser.add_argument(
        '--version', 
        action='version',
        version='Email Guardian CLI v1.0.0'
    )
    
    args = parser.parse_args()
    
    # Initialize CLI
    cli = EmailGuardCLI()
    
    try:
        # Handle configuration commands
        if args.config:
            key, value = args.config
            if key in cli.config:
                # Type conversion for specific keys
                if key == 'timeout':
                    value = int(value)
                cli.config[key] = value
                cli.save_config()
                print(f"Configuration updated: {key} = {value}")
            else:
                print(f"Error: Unknown configuration key '{key}'", file=sys.stderr)
                print(f"Valid keys: {', '.join(cli.config.keys())}")
                sys.exit(1)
            return
        
        if args.show_config:
            print(json.dumps(cli.config, indent=2))
            return
        
        # Handle Groq test
        if args.test_groq:
            try:
                result = cli.test_groq_connection()
                if result['success']:
                    print(f"✅ Groq connection successful!")
                    print(f"Model: {result.get('model', 'Unknown')}")
                    print(f"Test classification: {result.get('test_classification', 'N/A')}")
                else:
                    print(f"❌ Groq connection failed: {result.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"❌ Error testing Groq: {e}")
            return
        
        # Handle history and stats commands
        if args.history:
            history = cli.get_history(args.limit)
            print(json.dumps(history, indent=2))
            return
        
        if args.stats:
            stats = cli.get_stats()
            print(json.dumps(stats, indent=2))
            return
        
        # Handle classification
        if not args.text and not args.file:
            parser.print_help()
            sys.exit(1)
        
        # Get input text
        if args.file:
            text = cli.read_input(args.file)
        else:
            text = cli.read_input(args.text)
        
        if not text:
            print("Error: No text provided for classification", file=sys.stderr)
            sys.exit(1)
        
        # Classify the text
        result = cli.classify_text(text, use_api=args.api, use_llm=args.llm)
        
        # Output the result
        output = cli.format_output(result, args.format)
        print(output)
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(1)
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
