"""
OpenRouter LLM Client
Uses OpenAI SDK format to communicate with OpenRouter API
"""
import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

class OpenRouterLLM:
    def __init__(self, api_key: str = None, model_name: str = "anthropic/claude-3.5-sonnet", max_tokens: int = 2000, temperature: float = 0.7):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            logger.error("OpenRouter API key not provided or found in environment variables.")
            raise ValueError("OpenRouter API key not provided or found in environment variables.")

        try:
            # OpenRouter uses OpenAI SDK format
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://openrouter.ai/api/v1"
            )
            logger.info(f"OpenRouterLLM initialized with model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenRouter client: {e}", exc_info=True)
            raise

        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature

    def generate(self, prompt: str, system_message: str = None) -> str:
        logger.debug(f"Generating text with model {self.model_name}, prompt (first 50 chars): {prompt[:50]}")
        try:
            # Build messages array (OpenAI format)
            messages = []

            # Add system message if provided
            if system_message:
                messages.append({"role": "system", "content": system_message})

            # Add user prompt
            messages.append({"role": "user", "content": prompt})

            # Call OpenRouter using OpenAI SDK format
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )

            # Extract content from OpenAI-style response
            content = response.choices[0].message.content
            if content is None:
                logger.warning("OpenRouter API returned None content.")
                return "Error: LLM returned no content."
            return content.strip()

        except Exception as e:
            logger.error(f"Error calling OpenRouter API: {e}", exc_info=True)
            return f"Error: OpenRouter API issue - {e}"

    async def agenerate(self, prompt: str, system_message: str = None) -> str:
        # Basic async wrapper - for true async, would need AsyncOpenAI client
        logger.debug(f"Async generating text with model {self.model_name}, prompt (first 50 chars): {prompt[:50]}")
        # This is NOT truly async with the synchronous client.
        # For simplicity in this placeholder, we call the synchronous one.
        return self.generate(prompt, system_message)
