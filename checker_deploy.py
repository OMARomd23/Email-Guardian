#!/usr/bin/env python3
"""
GitHub Deployment Script for Email Guardian
Safely prepares and deploys your Email Guardian to GitHub
"""

import os
import shutil
import subprocess
from pathlib import Path

class GitHubDeployer:
    def __init__(self):
        self.project_root = Path.cwd()
        self.sensitive_files = [
            '.env',
            '*.db',
            '*.sqlite*',
            'email_guardian.db',
            'scan_history.db'
        ]
        
    def print_step(self, step, message):
        print(f"\n🔹 Step {step}: {message}")
        print("-" * 50)
    
    def check_sensitive_files(self):
        """Check for sensitive files that shouldn't be uploaded"""
        print("🔍 Checking for sensitive files...")
        
        sensitive_found = []
        
        # Check for .env files
        for env_file in self.project_root.rglob('.env*'):
            if env_file.name != '.env.example':
                sensitive_found.append(str(env_file))
        
        # Check for database files
        for db_file in self.project_root.rglob('*.db'):
            sensitive_found.append(str(db_file))
        
        for sqlite_file in self.project_root.rglob('*.sqlite*'):
            sensitive_found.append(str(sqlite_file))
        
        if sensitive_found:
            print("⚠️  WARNING: Found sensitive files:")
            for file in sensitive_found:
                print(f"   - {file}")
            print("\n🛡️  These files will be protected by .gitignore")
        else:
            print("✅ No sensitive files found")
        
        return sensitive_found
    
    def create_gitignore(self):
        """Create comprehensive .gitignore"""
        print("📝 Creating .gitignore...")
        
        gitignore_content = """# Email Guardian .gitignore
# CRITICAL: This file protects your sensitive data

# Environment variables - NEVER COMMIT
.env
.env.local
.env.production
.env.staging

# Database files - Contains user data
*.db
*.sqlite
*.sqlite3
email_guardian.db

# API keys and secrets
secrets.json
config.json

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
env/
ENV/
.venv/

# IDE files
.vscode/
.idea/
*.swp
*.swo
*~

# OS files
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Model files (if too large)
my-3class-model/

# Node modules
node_modules/

# Backup files
*.backup.*
*.bak

# Test results
test_results/
coverage/
"""
        
        gitignore_path = self.project_root / '.gitignore'
        gitignore_path.write_text(gitignore_content.strip())
        print(f"✅ Created {gitignore_path}")
    
    def create_env_example(self):
        """Create .env.example template"""
        print("📝 Creating .env.example...")
        
        env_example_content = """# Email Guardian Configuration Example
# Copy this file to .env and update with your values

# API Security
API_KEY=your-secure-api-key-here

# Model Configuration
MODEL_PATH=./my-3class-model

# Database Configuration
DATABASE_PATH=email_guardian.db

# Groq LLM Integration (Optional)
GROQ_API_KEY=your-groq-api-key-here

# Server Configuration
FLASK_ENV=development
PORT=5000

# For production:
# - Generate secure API key: python -c "import secrets; print(secrets.token_urlsafe(32))"
# - Set FLASK_ENV=production
# - Use environment variables instead of .env file
"""
        
        env_example_path = self.project_root / '.env.example'
        env_example_path.write_text(env_example_content.strip())
        print(f"✅ Created {env_example_path}")
        
        # Also create one in backend if it exists
        backend_dir = self.project_root / 'backend'
        if backend_dir.exists():
            backend_env_example = backend_dir / '.env.example'
            backend_env_example.write_text(env_example_content.strip())
            print(f"✅ Created {backend_env_example}")
    
    def create_readme(self):
        """Create main README.md"""
        print("📝 Creating README.md...")
        
        readme_content = """# Email Guardian 🛡️

Advanced AI-powered email security scanner that detects spam and phishing attempts using machine learning and LLM validation.

## Features

- 🤖 **AI-Powered Detection**: DistilBERT model for accurate classification
- 🧠 **LLM Validation**: Optional Groq LLM for enhanced accuracy  
- 🌐 **Web Interface**: Simple HTML frontend
- 💻 **CLI Tool**: Command-line interface for batch processing
- 📊 **Analytics**: Comprehensive scan history and statistics
- 🔒 **Secure**: API key authentication and input validation

## Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/email-guardian.git
cd email-guardian
```

### 2. Set up the backend
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your configuration
```

### 3. Start the application
```bash
python app.py
```

### 4. Open the frontend
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
"""
        
        readme_path = self.project_root / 'README.md'
        readme_path.write_text(readme_content.strip())
        print(f"✅ Created {readme_path}")
    
    def create_requirements_txt(self):
        """Create requirements.txt if it doesn't exist"""
        backend_dir = self.project_root / 'backend'
        requirements_file = backend_dir / 'requirements.txt'
        
        if not requirements_file.exists() and backend_dir.exists():
            print("📝 Creating requirements.txt...")
            
            requirements_content = """# Email Guardian Backend Dependencies

# Core Flask dependencies
Flask==2.3.3
Flask-CORS==4.0.0
Flask-Limiter==3.5.0

# Machine Learning dependencies
torch==2.0.1
transformers==4.33.2
numpy==1.24.3

# LLM Integration
groq==0.12.0

# Utility dependencies
python-dotenv==1.0.0
gunicorn==21.2.0
requests==2.31.0

# Development dependencies (optional)
pytest==7.4.2
pytest-flask==1.2.0
"""
            
            requirements_file.write_text(requirements_content.strip())
            print(f"✅ Created {requirements_file}")
    
    def init_git_repo(self):
        """Initialize Git repository"""
        print("🔧 Initializing Git repository...")
        
        try:
            # Check if git is already initialized
            git_dir = self.project_root / '.git'
            if git_dir.exists():
                print("✅ Git repository already initialized")
                return
            
            # Initialize git
            subprocess.run(['git', 'init'], cwd=self.project_root, check=True)
            print("✅ Git repository initialized")
            
            # Add .gitignore first
            subprocess.run(['git', 'add', '.gitignore'], cwd=self.project_root, check=True)
            subprocess.run(['git', 'commit', '-m', 'Add .gitignore for security'], cwd=self.project_root, check=True)
            print("✅ Added .gitignore to repository")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Git command failed: {e}")
        except FileNotFoundError:
            print("❌ Git not found. Please install Git first.")
    
    def show_next_steps(self):
        """Show next steps for GitHub deployment"""
        print("\n🚀 NEXT STEPS FOR GITHUB DEPLOYMENT")
        print("=" * 60)
        
        print("\n1. Create GitHub Repository:")
        print("   - Go to https://github.com/new")
        print("   - Name: email-guardian")
        print("   - Don't initialize with README")
        print("   - Create repository")
        
        print("\n2. Add and commit your files:")
        print("   git add .")
        print("   git commit -m 'Initial commit: Email Guardian AI security scanner'")
        
        print("\n3. Connect to GitHub:")
        print("   git remote add origin https://github.com/yourusername/email-guardian.git")
        print("   git branch -M main")
        print("   git push -u origin main")
        
        print("\n4. Repository Settings:")
        print("   - Add description: 'AI-powered email security scanner'")
        print("   - Add topics: ai, security, email, spam-detection, phishing")
        print("   - Enable Issues for user feedback")
        print("   - Add a license (MIT recommended)")
        
        print("\n🔒 SECURITY REMINDERS:")
        print("   ✅ .gitignore protects your sensitive files")
        print("   ✅ Never commit .env files")
        print("   ✅ Use .env.example for configuration templates")
        print("   ✅ Generate new API keys for users")
        
        print("\n📋 Files ready for GitHub:")
        files_to_upload = [
            "README.md", ".gitignore", ".env.example", 
            "backend/app.py", "backend/model_handler.py", 
            "backend/database.py", "backend/groq_validator.py",
            "backend/email_guard.py", "frontend/index.html",
            "scripts/setup_email_guardian.py"
        ]
        
        for file in files_to_upload:
            file_path = self.project_root / file
            if file_path.exists():
                print(f"   ✅ {file}")
            else:
                print(f"   ⚠️  {file} (missing)")

def main():
    """Main deployment function"""
    print("🛡️  Email Guardian - GitHub Deployment Preparation")
    print("=" * 60)
    
    deployer = GitHubDeployer()
    
    # Step 1: Check for sensitive files
    deployer.print_step(1, "Checking for sensitive files")
    deployer.check_sensitive_files()
    
    # Step 2: Create .gitignore
    deployer.print_step(2, "Creating .gitignore")
    deployer.create_gitignore()
    
    # Step 3: Create .env.example
    deployer.print_step(3, "Creating configuration templates")
    deployer.create_env_example()
    
    # Step 4: Create README
    deployer.print_step(4, "Creating documentation")
    deployer.create_readme()
    
    # Step 5: Create requirements.txt
    deployer.print_step(5, "Creating requirements.txt")
    deployer.create_requirements_txt()
    
    # Step 6: Initialize Git
    deployer.print_step(6, "Initializing Git repository")
    deployer.init_git_repo()
    
    # Step 7: Show next steps
    deployer.show_next_steps()
    
    print(f"\n🎉 Your Email Guardian is ready for GitHub!")
    print(f"All sensitive data is protected by .gitignore")

if __name__ == "__main__":
    main()
