#!/bin/bash
# Quick setup script for Market Outreach Platform

echo "🚀 Market Outreach Platform - Setup Guide"
echo "========================================="
echo ""

# Check conda environment
if ! command -v conda &> /dev/null; then
    echo "❌ Conda not found. Please install Miniconda/Anaconda first."
    exit 1
fi

# Activate environment
echo "1️⃣  Activating conda environment..."
conda activate twinquery

# Install dependencies
echo "2️⃣  Installing dependencies..."
pip install -r requirements.txt

# Create .env file
echo "3️⃣  Setting up configuration..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "   ✓ Created .env file - edit with your SMTP credentials"
else
    echo "   ℹ️  .env already exists"
fi

# Initialize database
echo "4️⃣  Initializing database..."
python -c "from app.database import init_db; init_db(); print('   ✓ Database initialized')"

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Edit .env with your email credentials (optional)"
echo "   2. Run 'make dev' to start the server"
echo "   3. Open http://localhost:8000/targets"
echo ""
echo "📚 Documentation: See GUIDE.md for detailed usage"
