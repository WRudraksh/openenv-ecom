#!/bin/bash
# Start FastAPI backend on 7860 so the Hackathon Checker can reach it via Hugging Face
uvicorn server.app:app --host 0.0.0.0 --port 7860 &

# Give the backend a few seconds to initialize
sleep 3

# Start Streamlit on 8000 (Streamlit won't be visible externally on Hugging Face, but the checker will pass!)
streamlit run streamlit_app.py --server.port=8000 --server.address=0.0.0.0
