#!/bin/bash
# Start FastAPI backend in the background
cd /app/env
uvicorn server.app:app --host 0.0.0.0 --port 8000 &

# Give the backend a few seconds to initialize
sleep 3

# Start Streamlit on port 7860 (Hugging Face default)
streamlit run streamlit_app.py --server.port=7860 --server.address=0.0.0.0
