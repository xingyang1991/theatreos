#!/bin/bash
# TheatreOS M1 Server Startup Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   TheatreOS M1 Server Startup${NC}"
echo -e "${GREEN}========================================${NC}"

# Navigate to project root
cd "$(dirname "$0")/.."
PROJECT_ROOT=$(pwd)

echo -e "${YELLOW}Project root: ${PROJECT_ROOT}${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python3 not found!${NC}"
    exit 1
fi

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip3 install -q -r requirements.txt

# Set environment variables
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH}"
export DATABASE_URL="${DATABASE_URL:-sqlite:///./theatreos_demo.db}"
export API_HOST="${API_HOST:-0.0.0.0}"
export API_PORT="${API_PORT:-8000}"
export DEBUG="${DEBUG:-true}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

echo -e "${YELLOW}Database: ${DATABASE_URL}${NC}"
echo -e "${YELLOW}API Host: ${API_HOST}:${API_PORT}${NC}"

# Start server
echo -e "${GREEN}Starting TheatreOS API Server...${NC}"
echo -e "${GREEN}API Documentation: http://localhost:${API_PORT}/docs${NC}"
echo ""

cd gateway/src
python3 -m uvicorn main:app --host ${API_HOST} --port ${API_PORT} --reload
