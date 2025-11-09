import os; from dotenv import load_dotenv; load_dotenv(); key=os.getenv("OPENAI_API_KEY"); print("Key found:", bool(key)); print("Key preview:", key[:20] + "..." if key else "None")
