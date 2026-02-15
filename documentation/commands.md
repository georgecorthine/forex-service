## python backend
    python3 -m venv venv
    source venv/bin/activate
    export TELEGRAM_BOT_TOKEN="8485558984:AAGoRNBIH4F5OeJBeTRioqdGkHRy30Lccf0"
    export TELEGRAM_CHAT_ID="5556864036"
    export OANDA_API_TOKEN="e4fc42da1dff74b0b20a30e969776ab1-a7fe27187d8b8684e0eab4f07d8f1060"
    export OANDA_ACCOUNT_ID="101-004-38541547-001"
    ./start.py

## docker
    docker build -t forex-service .
    docker run -d --name forex-engine -p 8000:8000 forex-service
    docker logs -f forex-engine
    docker stop forex-engine

## swagger
    http://127.0.0.1:8000/docs#/
    http://localhost:8000/


