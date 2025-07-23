
#!/usr/bin/env python3
"""
Email Guardian Test Suite
Tests the API endpoints and classification accuracy
"""

import requests
import json
import time
from typing import Dict, List, Tuple
import os
from datetime import datetime

class EmailGuardianTester:
    def __init__(self, base_url: str = "http://localhost:5000", api_key: str = None):
        """
        Initialize the tester
        
        Args:
            base_url: Base URL of the API
            api_key: API key for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key or os.environ.get('API_KEY', 'your-api-key')
        self.headers = {
            'Content-Type': 'application/json',
            'X-API-Key': self.api_key
        }
        self.test_results = []
        
    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'details': details,
            'timestamp': timestamp
        })
        print(f"[{timestamp}] {status} {test_name}")
        if details:
            print(f"    Details: {details}")

    def test_health_endpoint(self) -> bool:
        """Test the health endpoint"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                details = f"Model loaded: {data.get('model_loaded')}, Groq: {data.get('groq_validator')}"
                self.log_result("Health Check", True, details)
                return True
            else:
                self.log_result("Health Check", False, f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Health Check", False, f"Error: {str(e)}")
            return False

    def test_authentication(self) -> bool:
        """Test API key authentication"""
        # Test without API key
        try:
            response = requests.post(f"{self.base_url}/api/scan", 
                                   json={"text": "test"}, 
                                   timeout=10)
            if response.status_code == 401:
                self.log_result("Auth - No Key", True, "Correctly rejected")
            else:
                self.log_result("Auth - No Key", False, f"Expected 401, got {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Auth - No Key", False, f"Error: {str(e)}")
            return False

        # Test with wrong API key
        try:
            wrong_headers = {'Content-Type': 'application/json', 'X-API-Key': 'wrong-key'}
            response = requests.post(f"{self.base_url}/api/scan", 
                                   json={"text": "test"}, 
                                   headers=wrong_headers,
                                   timeout=10)
            if response.status_code == 401:
                self.log_result("Auth - Wrong Key", True, "Correctly rejected")
                return True
            else:
                self.log_result("Auth - Wrong Key", False, f"Expected 401, got {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Auth - Wrong Key", False, f"Error: {str(e)}")
            return False

    def classify_email(self, text: str, expected_class: str = None) -> Dict:
        """
        Classify an email and return the result
        
        Args:
            text: Email text to classify
            expected_class: Expected classification for testing
            
        Returns:
            Classification result dict
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/scan",
                json={"text": text, "llm_validation": True},
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                classification = result.get('classification')
                confidence = result.get('confidence')
                probabilities = result.get('probabilities', {})
                
                # Log detailed results
                prob_str = ", ".join([f"{k}: {v:.2%}" for k, v in probabilities.items()])
                details = f"Class: {classification}, Confidence: {confidence:.2%}, Probs: [{prob_str}]"
                
                if expected_class:
                    passed = classification == expected_class
                    test_name = f"Classify as {expected_class}"
                    if not passed:
                        details += f" (Expected: {expected_class})"
                    self.log_result(test_name, passed, details)
                
                return result
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                if expected_class:
                    self.log_result(f"Classify as {expected_class}", False, error_msg)
                return {"error": error_msg}
                
        except Exception as e:
            error_msg = f"Request failed: {str(e)}"
            if expected_class:
                self.log_result(f"Classify as {expected_class}", False, error_msg)
            return {"error": error_msg}

    def test_legitimate_emails(self) -> List[Dict]:
        """Test legitimate email classification"""
        legitimate_emails = [
            {
                "text": """From: notifications@company.com
To: user@example.com
Subject: Your Monthly Report is Ready

Hello,

Your monthly analytics report for January 2025 is now available for download.

You can access it by logging into your dashboard at https://company.com/dashboard

Best regards,
Analytics Team""",
                "description": "Corporate notification"
            },
            {
                "text": """From: noreply@github.com
To: developer@company.com
Subject: Pull Request Merged

Your pull request #123 has been successfully merged into the main branch.

Changes:
- Fixed authentication bug
- Updated documentation

View the changes: https://github.com/yourrepo/pull/123""",
                "description": "GitHub notification"
            },
            {
                "text": """From: support@amazon.com
To: customer@email.com
Subject: Your Order Has Shipped

Thank you for your order #112-3456789-1234567.

Your package is on its way and will arrive by Thursday, January 25th.

Track your package: https://www.amazon.com/progress-tracker/package/12345

Amazon Customer Service""",
                "description": "Amazon shipping notification"
            }
        ]
        
        print("\n🔍 Testing Legitimate Emails...")
        results = []
        for email in legitimate_emails:
            print(f"  Testing: {email['description']}")
            result = self.classify_email(email["text"], "legitimate")
            result["description"] = email["description"]
            results.append(result)
            time.sleep(1)  # Rate limiting
        
        return results

    def test_spam_emails(self) -> List[Dict]:
        """Test spam email classification"""
        spam_emails = [
            {
                "text": """From: winner@lottery-international.com
To: user@example.com
Subject: CONGRATULATIONS! YOU'VE WON $1,000,000!!!

DEAR LUCKY WINNER!!!

YOU HAVE WON THE INTERNATIONAL LOTTERY JACKPOT OF ONE MILLION DOLLARS!!!

Send us your bank details IMMEDIATELY to claim your prize:
- Full Name
- Bank Account Number
- Social Security Number
- Copy of ID

Contact: winner@lottery-international.com

URGENT! CLAIM NOW!""",
                "description": "Lottery scam"
            },
            {
                "text": """From: prince.nigeria@email.com
To: recipient@email.com
Subject: URGENT BUSINESS PROPOSAL

Dear Friend,

I am Prince Mubarak from Nigeria. I have $25 MILLION USD that I need to transfer out of my country.

I need your help to transfer this money. You will receive 30% commission.

Please send me your bank account details:
- Account number
- Routing number
- Full name

This is 100% safe and legal.

Best regards,
Prince Mubarak""",
                "description": "Nigerian prince scam"
            },
            {
                "text": """MAKE $5000 PER WEEK FROM HOME!!!

NO EXPERIENCE NEEDED! WORK FROM HOME!

Click here to start earning money TODAY:
http://make-money-fast.scam.com

- Make $500-$5000 per week
- Work only 2 hours per day
- No skills required
- 100% guaranteed income

LIMITED TIME OFFER! CLICK NOW!

UNSUBSCRIBE: send email to remove@scam.com""",
                "description": "Get rich quick scheme"
            }
        ]
        
        print("\n🔍 Testing Spam Emails...")
        results = []
        for email in spam_emails:
            print(f"  Testing: {email['description']}")
            result = self.classify_email(email["text"], "spam")
            result["description"] = email["description"]
            results.append(result)
            time.sleep(1)
        
        return results

    def test_phishing_emails(self) -> List[Dict]:
        """Test phishing email classification"""
        phishing_emails = [
            {
                "text": """From: security@paypa1.com
To: user@example.com
Subject: Urgent: Verify Your Account

Your PayPal account has been temporarily suspended due to suspicious activity.

Click here to verify your account immediately:
http://paypa1-security.suspicious-domain.com/verify

If you don't verify within 24 hours, your account will be permanently closed.

PayPal Security Team""",
                "description": "PayPal phishing (typosquatting)"
            },
            {
                "text": """From: security-noreply@apple.com
To: user@example.com
Subject: Your Apple ID has been locked

Dear Apple Customer,

We've detected unusual activity on your Apple ID account. To protect your account, we've temporarily locked it.

To unlock your account, please verify your identity:
https://appleid-security-verification.com/unlock

This link expires in 2 hours. If you don't take action, your account may be permanently disabled and all purchases will be lost.

For your security, this email was sent from a secure Apple server.

Apple Security Team
Copyright © 2025 Apple Inc.""",
                "description": "Apple ID phishing"
            },
            {
                "text": """From: alerts@bankofamerica.com
To: customer@email.com
Subject: Suspicious Activity Detected

We have detected suspicious activity on your Bank of America account.

For your security, we have temporarily restricted your account access.

To restore full access, please verify your information:
https://secure-bankofamerica-verification.net/login

Required information:
- Username and Password
- Social Security Number
- Account Number
- Debit Card PIN

This verification must be completed within 24 hours.

Bank of America Security Department""",
                "description": "Bank phishing"
            },
            {
                "text": """From: ceo@yourcompany.com
To: finance@yourcompany.com
Subject: Urgent: Wire Transfer Required

Hi Sarah,

I'm currently in a client meeting and need you to process an urgent wire transfer immediately. Our legal team requires $50,000 to be sent to our new law firm for the acquisition deal.

Wire details:
Account: 4782-9901-2234
Routing: 021000021
Recipient: Morrison Legal LLC

This is time-sensitive and confidential. Please confirm once sent.

Thanks,
John Smith
CEO""",
                "description": "CEO fraud / Spear phishing"
            },
            {
                "text": """From: no-reply@microsoft.com
To: user@company.com
Subject: Microsoft Office 365 Security Alert

Your Microsoft Office 365 account will be suspended in 2 hours due to unusual sign-in activity.

Location: Unknown (IP: 192.168.1.1)
Device: Unknown Browser
Time: Today 2:30 PM

If this was not you, secure your account immediately:
https://office365-security-center.net/verify

Click "Secure Account" to prevent suspension.

This is an automated security message from Microsoft.
Do not reply to this email.""",
                "description": "Microsoft Office 365 phishing"
            }
        ]
        
        print("\n🔍 Testing Phishing Emails...")
        results = []
        for email in phishing_emails:
            print(f"  Testing: {email['description']}")
            result = self.classify_email(email["text"], "phishing")
            result["description"] = email["description"]
            results.append(result)
            time.sleep(1)
        
        return results

    def test_edge_cases(self) -> List[Dict]:
        """Test edge cases and validation"""
        edge_cases = [
            {"text": "", "expected_status": 400, "description": "Empty text"},
            {"text": "Hi", "expected_class": None, "description": "Very short text"},
            {"text": "A" * 10001, "expected_status": 400, "description": "Text too long"},
        ]
        
        print("\n🔍 Testing Edge Cases...")
        results = []
        
        for case in edge_cases:
            print(f"  Testing: {case['description']}")
            try:
                response = requests.post(
                    f"{self.base_url}/api/scan",
                    json={"text": case["text"]},
                    headers=self.headers,
                    timeout=10
                )
                
                if "expected_status" in case:
                    passed = response.status_code == case["expected_status"]
                    details = f"Expected status {case['expected_status']}, got {response.status_code}"
                else:
                    passed = response.status_code == 200
                    details = f"Status: {response.status_code}"
                    
                self.log_result(f"Edge case: {case['description']}", passed, details)
                
                result = {"description": case["description"], "status_code": response.status_code}
                if response.status_code == 200:
                    result.update(response.json())
                results.append(result)
                
            except Exception as e:
                self.log_result(f"Edge case: {case['description']}", False, f"Error: {str(e)}")
                results.append({"description": case["description"], "error": str(e)})
            
            time.sleep(1)
        
        return results

    def analyze_results(self, all_results: Dict[str, List[Dict]]):
        """Analyze and report on test results"""
        print("\n" + "="*60)
        print("📊 CLASSIFICATION ANALYSIS")
        print("="*60)
        
        for category, results in all_results.items():
            if not results:
                continue
                
            print(f"\n{category.upper()} EMAILS:")
            print("-" * 40)
            
            classifications = {}
            total = 0
            
            for result in results:
                if "classification" in result:
                    cls = result["classification"]
                    classifications[cls] = classifications.get(cls, 0) + 1
                    total += 1
                    
                    confidence = result.get("confidence", 0)
                    probabilities = result.get("probabilities", {})
                    
                    print(f"  {result['description'][:40]:<40} -> {cls} ({confidence:.1%})")
                    
                    # Show probability breakdown
                    prob_details = []
                    for prob_class, prob_value in probabilities.items():
                        prob_details.append(f"{prob_class}: {prob_value:.1%}")
                    if prob_details:
                        print(f"    Probabilities: {', '.join(prob_details)}")
            
            # Summary
            if total > 0:
                print(f"\n  Summary for {category}:")
                for cls, count in classifications.items():
                    percentage = (count / total) * 100
                    print(f"    {cls}: {count}/{total} ({percentage:.1f}%)")

    def test_model_bias(self):
        """Test for potential model bias issues"""
        print("\n🔍 Testing Model Bias and Edge Cases...")
        
        # Test for classification threshold issues
        borderline_cases = [
            {
                "text": "Your account needs verification. Please click here: https://secure-site.com",
                "description": "Borderline phishing/legitimate"
            },
            {
                "text": "Congratulations! You've been selected for a special offer. Call 1-800-123-4567",
                "description": "Borderline spam/legitimate"
            },
            {
                "text": "From: admin@company.com\nImportant security update required.",
                "description": "Minimal context email"
            }
        ]
        
        for case in borderline_cases:
            print(f"  Testing: {case['description']}")
            result = self.classify_email(case["text"])
            if "classification" in result:
                probs = result.get("probabilities", {})
                max_prob = max(probs.values()) if probs else 0
                print(f"    Result: {result['classification']} (max prob: {max_prob:.1%})")
                
                # Flag if classification is very uncertain
                if max_prob < 0.6:
                    print(f"    ⚠️  Low confidence classification detected")

    def run_comprehensive_test(self):
        """Run all tests and generate a comprehensive report"""
        print("🚀 Starting Email Guardian Comprehensive Test Suite")
        print("="*60)
        
        start_time = time.time()
        
        # Basic connectivity tests
        print("\n1️⃣ Testing Basic Connectivity...")
        health_ok = self.test_health_endpoint()
        auth_ok = self.test_authentication()
        
        if not health_ok:
            print("\n❌ Health check failed. Cannot proceed with classification tests.")
            return
        
        # Classification tests
        all_results = {}
        
        if health_ok and auth_ok:
            all_results["legitimate"] = self.test_legitimate_emails()
            all_results["spam"] = self.test_spam_emails()
            all_results["phishing"] = self.test_phishing_emails()
            
            # Edge cases
            self.test_edge_cases()
            
            # Bias testing
            self.test_model_bias()
        
        # Analysis
        if all_results:
            self.analyze_results(all_results)
        
        # Final summary
        end_time = time.time()
        duration = end_time - start_time
        
        print("\n" + "="*60)
        print("📋 TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for result in self.test_results if result["passed"])
        total = len(self.test_results)
        
        print(f"Total tests run: {total}")
        print(f"Tests passed: {passed}")
        print(f"Tests failed: {total - passed}")
        print(f"Success rate: {(passed/total)*100:.1f}%" if total > 0 else "N/A")
        print(f"Test duration: {duration:.1f} seconds")
        
        # Show failed tests
        failed_tests = [r for r in self.test_results if not r["passed"]]
        if failed_tests:
            print(f"\n❌ Failed tests:")
            for test in failed_tests:
                print(f"  - {test['test']}: {test['details']}")
        
        # Specific phishing analysis
        phishing_results = all_results.get("phishing", [])
        if phishing_results:
            phishing_detected = sum(1 for r in phishing_results if r.get("classification") == "phishing")
            phishing_total = len([r for r in phishing_results if "classification" in r])
            
            print(f"\n🎯 PHISHING DETECTION ANALYSIS:")
            print(f"   Phishing emails correctly identified: {phishing_detected}/{phishing_total}")
            
            if phishing_detected < phishing_total:
                print(f"   ⚠️  Some phishing emails were misclassified!")
                for result in phishing_results:
                    if result.get("classification") != "phishing":
                        cls = result.get("classification", "unknown")
                        print(f"      - {result['description']} -> classified as '{cls}'")

def main():
    """Main function to run tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Email Guardian Test Suite")
    parser.add_argument("--url", default="http://localhost:5000", 
                       help="Base URL of the API (default: http://localhost:5000)")
    parser.add_argument("--api-key", 
                       help="API key for authentication")
    parser.add_argument("--quick", action="store_true",
                       help="Run only basic tests")
    
    args = parser.parse_args()
    
    # Initialize tester
    tester = EmailGuardianTester(args.url, args.api_key)
    
    if args.quick:
        print("🚀 Running Quick Test Suite...")
        tester.test_health_endpoint()
        tester.test_authentication()
        
        # Test one email of each type
        print("\nTesting sample emails...")
        tester.classify_email("Hello, this is a normal email.", "legitimate")
        tester.classify_email("CONGRATULATIONS! YOU'VE WON $1,000,000!!!", "spam")
        tester.classify_email("Your PayPal account has been suspended. Click here: http://fake-paypal.com", "phishing")
    else:
        # Run comprehensive test
        tester.run_comprehensive_test()

if __name__ == "__main__":
    main()
