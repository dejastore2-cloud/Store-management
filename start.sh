#!/bin/bash
# تشغيل تطبيق الكاشير محلياً
cd "$(dirname "$0")"
pip install -r requirements.txt -q
python -c "from utils.icon_generator import generate_all; generate_all(); print('Icons OK')"
python app.py
