#!/usr/bin/env python3

import os
import sys
sys.path.insert(0, '/home/marblemaster/Desktop/Cursor/mvp1/backend')

from dotenv import load_dotenv

# Load .env file
load_dotenv()

print("=== OpenAI API Key Debug ===")
print(f"Current working directory: {os.getcwd()}")
print(f"OPENAI_API_KEY from os.getenv(): {os.getenv('OPENAI_API_KEY', 'NOT_SET')}")

# Check ETL config
try:
    from etl import config as etl_config
    print(f"ETL config OPENAI_API_KEY: {etl_config.OPENAI_API_KEY}")
except Exception as e:
    print(f"Error loading ETL config: {e}")

# Check main config
try:
    import config as main_config
    print(f"Main config OPENAI_API_KEY: {main_config.OPENAI_API_KEY}")
except Exception as e:
    print(f"Error loading main config: {e}")

# Check if .env file exists
env_path = os.path.join(os.getcwd(), '.env')
print(f".env file exists at {env_path}: {os.path.exists(env_path)}")

if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        content = f.read()
    print(f".env file first 200 chars: {content[:200]}")