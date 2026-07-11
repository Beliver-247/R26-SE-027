#!/bin/bash
# Setup environment script

echo "Setting up Green DevOps Operation Component environment..."

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version | cut -d' ' -f2)
echo "Python version: $python_version"

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Copy environment file
echo "Setting up environment variables..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo ".env file created. Please edit with your settings."
else
    echo ".env already exists"
fi

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your settings"
echo "2. Run: python scripts/fetch_public_datasets.py"
echo "3. Run: python scripts/train_cold_start_models.py"
echo "4. Run: pytest tests/ -v"
echo "5. Run: make dev  (to start development server)"
