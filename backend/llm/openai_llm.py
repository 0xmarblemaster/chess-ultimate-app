import openai
import os
import logging

logger = logging.getLogger(__name__)

class OpenAILLM:
    def __init__(self, api_key: str = None, model_name: str = "gpt-4o", max_tokens: int = 2000, temperature: float = 0.5, base_url: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.error("OpenAI API key not provided or found in environment variables.")
            raise ValueError("OpenAI API key not provided or found in environment variables.")
        
        try:
            # Support custom base_url for alternative providers like Deepseek
            if base_url:
                self.client = openai.OpenAI(api_key=self.api_key, base_url=base_url)
                logger.info(f"OpenAILLM initialized with custom base_url: {base_url}, model: {model_name}")
            else:
                self.client = openai.OpenAI(api_key=self.api_key)
                logger.info(f"OpenAILLM initialized with model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}", exc_info=True)
            raise
            
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature

    def generate(self, prompt: str, system_message: str = None) -> str:
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        logger.debug(f"Generating text with model {self.model_name}, prompt (first 50 chars): {prompt[:50]}")
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            content = response.choices[0].message.content
            if content is None:
                logger.warning("OpenAI API returned None content.")
                return "Error: LLM returned no content."
            return content.strip()
        except openai.APIError as e:
            logger.error(f"OpenAI API Error: {e}", exc_info=True)
            return f"Error: OpenAI API issue - {e}"
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}", exc_info=True)
            return "Error: Could not get response from LLM due to an unexpected error."

    async def agenerate(self, prompt: str, system_message: str = None) -> str:
        # Basic async wrapper, for more complex async needs, a proper async client/library might be better
        # For now, just wraps the sync call. For true async, openai client needs to be AsyncOpenAI
        # This is a placeholder and might not be truly non-blocking depending on openai client's internal async handling
        # if it's not an async client.
        # Actual async client: from openai import AsyncOpenAI; self.async_client = AsyncOpenAI(...)
        logger.debug(f"Async generating text with model {self.model_name}, prompt (first 50 chars): {prompt[:50]}")
        # This is NOT truly async with the synchronous client.
        # To make it truly async, you'd initialize with AsyncOpenAI client.
        # For simplicity in this placeholder, we call the synchronous one.
        # Replace with actual async call if openai.AsyncOpenAI is used.
        return self.generate(prompt, system_message)

# Example usage (for testing this module directly)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Ensure OPENAI_API_KEY is set in your environment for this test
    if not os.getenv("OPENAI_API_KEY"):
        print("Please set the OPENAI_API_KEY environment variable to run this test.")
    else:
        try:
            llm = OpenAILLM(model_name="gpt-4o", max_tokens=50) # Using gpt-4o as per recent updates
            print(f"OpenAILLM instance created with model: {llm.model_name}")
            
            test_prompt = "Explain the concept of a language model in one sentence."
            print(f"Testing generate method with prompt: '{test_prompt}'")
            response = llm.generate(test_prompt)
            print(f"LLM Response: {response}")

            # Example of a system message
            # response_with_system = llm.generate("What is its capital?", system_message="You are a helpful assistant that knows geography. The user is asking about France.")
            # print(f"LLM Response (with system message context): {response_with_system}")

        except ValueError as ve:
            print(f"Initialization Error: {ve}")
        except Exception as e:
            print(f"An unexpected error occurred during testing: {e}") 