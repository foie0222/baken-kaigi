@echo off
cd /d C:\jravan-api
python -m uvicorn main:app --host 0.0.0.0 --port 8000
