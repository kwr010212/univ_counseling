#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

# 💡 [머신러닝 모델 복원용 전역 함수 선언] 
# 피클 파일이 전역 공간(__main__)에서 이 함수를 찾을 수 있도록 여기에 정의해줍니다.
def simple_korean_tokenizer(text):
    clean_text = "".join([c for c in text if c.isalnum() or c.isspace()])
    return clean_text.split()

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()