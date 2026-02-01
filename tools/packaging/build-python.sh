#!/bin/bash
# Build bundled Python runtime for Kiroku Memory Desktop App
# Uses python-build-standalone: https://github.com/indygreg/python-build-standalone
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/dist"

# Python version to bundle
PYTHON_VERSION="3.11.11"
PBS_RELEASE="20250115"  # python-build-standalone release date

# Parse arguments
CLEAN_BUNDLE=true
ARCH_OVERRIDE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-clean)
            CLEAN_BUNDLE=false
            shift
            ;;
        --arch)
            ARCH_OVERRIDE="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--no-clean] [--arch aarch64|x86_64]"
            echo "  --no-clean    Skip cleanup step (keep tests, docs, etc.)"
            echo "  --arch        Force specific architecture"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Detect architecture
if [ -n "$ARCH_OVERRIDE" ]; then
    PBS_ARCH="$ARCH_OVERRIDE"
else
    ARCH=$(uname -m)
    case "$ARCH" in
        arm64|aarch64)
            PBS_ARCH="aarch64"
            ;;
        x86_64)
            PBS_ARCH="x86_64"
            ;;
        *)
            echo "Error: Unsupported architecture: $ARCH"
            exit 1
            ;;
    esac
fi

# Download URL
PBS_FILENAME="cpython-${PYTHON_VERSION}+${PBS_RELEASE}-${PBS_ARCH}-apple-darwin-install_only.tar.gz"
PBS_URL="https://github.com/indygreg/python-build-standalone/releases/download/${PBS_RELEASE}/${PBS_FILENAME}"

echo "=== Kiroku Memory Python Bundler ==="
echo "Python version: $PYTHON_VERSION"
echo "Architecture: $PBS_ARCH"
echo "Output: $OUTPUT_DIR/$PBS_ARCH"
echo "Clean bundle: $CLEAN_BUNDLE"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR/$PBS_ARCH"

# Download python-build-standalone if not cached
CACHE_DIR="$SCRIPT_DIR/.cache"
mkdir -p "$CACHE_DIR"
CACHED_FILE="$CACHE_DIR/$PBS_FILENAME"

if [ ! -f "$CACHED_FILE" ]; then
    echo "Downloading python-build-standalone..."
    curl -L -o "$CACHED_FILE" "$PBS_URL"
else
    echo "Using cached python-build-standalone..."
fi

# Extract
echo "Extracting Python runtime..."
rm -rf "$OUTPUT_DIR/$PBS_ARCH/python"
mkdir -p "$OUTPUT_DIR/$PBS_ARCH"
tar -xzf "$CACHED_FILE" -C "$OUTPUT_DIR/$PBS_ARCH"

# The archive extracts to "python/" directory
PYTHON_DIR="$OUTPUT_DIR/$PBS_ARCH/python"
PYTHON_BIN="$PYTHON_DIR/bin/python3"

# Verify Python works
echo "Verifying Python..."
"$PYTHON_BIN" --version

# Upgrade pip
echo "Upgrading pip..."
"$PYTHON_BIN" -m pip install --upgrade pip -q

# Install project dependencies (from pyproject.toml + surrealdb extra)
echo "Installing Kiroku Memory dependencies..."
"$PYTHON_BIN" -m pip install -q \
    "fastapi>=0.115.0" \
    "uvicorn[standard]>=0.34.0" \
    "sqlalchemy[asyncio]>=2.0.0" \
    "asyncpg>=0.30.0" \
    "pgvector>=0.3.0" \
    "alembic>=1.14.0" \
    "pydantic>=2.10.0" \
    "pydantic-settings>=2.7.0" \
    "openai>=1.60.0" \
    "redis>=5.0.0" \
    "python-dotenv>=1.0.0" \
    "surrealdb>=0.3.0"

# Verify imports
echo "Verifying imports..."
"$PYTHON_BIN" -c "
import fastapi
import uvicorn
import pydantic
import surrealdb
print('All imports successful!')
print(f'FastAPI version: {fastapi.__version__}')
print(f'Uvicorn version: {uvicorn.__version__}')
"

# Clean up bundle to reduce size
if [ "$CLEAN_BUNDLE" = true ]; then
    echo ""
    echo "=== Cleaning up bundle to reduce size ==="

    # Remove __pycache__ directories
    echo "Removing __pycache__ directories..."
    find "$PYTHON_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

    # Remove .pyc files (bytecode)
    echo "Removing .pyc files..."
    find "$PYTHON_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true

    # Remove test directories
    echo "Removing test directories..."
    find "$PYTHON_DIR" -type d -name "test" -exec rm -rf {} + 2>/dev/null || true
    find "$PYTHON_DIR" -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
    find "$PYTHON_DIR" -type d -name "testing" -exec rm -rf {} + 2>/dev/null || true

    # Remove documentation and examples
    echo "Removing docs and examples..."
    find "$PYTHON_DIR" -type d -name "docs" -exec rm -rf {} + 2>/dev/null || true
    find "$PYTHON_DIR" -type d -name "doc" -exec rm -rf {} + 2>/dev/null || true
    find "$PYTHON_DIR" -type d -name "examples" -exec rm -rf {} + 2>/dev/null || true

    # Remove pip cache
    echo "Removing pip cache..."
    rm -rf "$PYTHON_DIR/lib/python3.11/site-packages/pip" 2>/dev/null || true
    rm -rf "$PYTHON_DIR/lib/python3.11/site-packages/setuptools" 2>/dev/null || true

    # Remove unnecessary include files
    echo "Removing include files..."
    rm -rf "$PYTHON_DIR/include" 2>/dev/null || true

    # Remove share directory (man pages, etc.)
    echo "Removing share directory..."
    rm -rf "$PYTHON_DIR/share" 2>/dev/null || true

    # Remove unused binaries (keep only python3 and pip3)
    echo "Removing unused binaries..."
    cd "$PYTHON_DIR/bin"
    for f in *; do
        case "$f" in
            python3|python3.11|pip3|pip3.11|uvicorn)
                # Keep these
                ;;
            *)
                rm -f "$f" 2>/dev/null || true
                ;;
        esac
    done
    cd - > /dev/null

    # Verify imports still work after cleanup
    echo "Verifying imports after cleanup..."
    "$PYTHON_BIN" -c "
import fastapi
import uvicorn
import pydantic
import surrealdb
print('Post-cleanup verification successful!')
"
fi

# Create a simple test
echo ""
echo "=== Testing bundled Python ==="
"$PYTHON_BIN" -c "
import sys
print(f'Python: {sys.version}')
print(f'Executable: {sys.executable}')
print(f'Prefix: {sys.prefix}')
"

# Calculate size
BUNDLE_SIZE=$(du -sh "$PYTHON_DIR" | cut -f1)
echo ""
echo "=== Build Complete ==="
echo "Bundle location: $PYTHON_DIR"
echo "Bundle size: $BUNDLE_SIZE"
echo ""
echo "To test with Kiroku Memory:"
echo "  PYTHONPATH=$PROJECT_ROOT $PYTHON_BIN -m uvicorn kiroku_memory.api:app --host 127.0.0.1 --port 8000"
