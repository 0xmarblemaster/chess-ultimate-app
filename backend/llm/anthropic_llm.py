import anthropic
import os
import logging

logger = logging.getLogger(__name__)

class AnthropicLLM:
    def __init__(self, api_key: str = None, model_name: str = "anthropic/claude-3.5-sonnet", max_tokens: int = 2000, temperature: float = 0.7):
        # Try OpenRouter first, fallback to direct Anthropic
        self.use_openrouter = False
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        anthropic_key = api_key or os.getenv("ANTHROPIC_API_KEY")

        if openrouter_key:
            # Use OpenRouter
            self.api_key = openrouter_key
            self.use_openrouter = True
            try:
                self.client = anthropic.Anthropic(
                    api_key=self.api_key,
                    base_url="https://openrouter.ai/api/v1"
                )
                logger.info(f"AnthropicLLM initialized with OpenRouter, model: {model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize OpenRouter client: {e}", exc_info=True)
                raise
        elif anthropic_key:
            # Use direct Anthropic API
            self.api_key = anthropic_key
            try:
                self.client = anthropic.Anthropic(api_key=self.api_key)
                logger.info(f"AnthropicLLM initialized with direct Anthropic API, model: {model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}", exc_info=True)
                raise
        else:
            logger.error("No API key found (neither OPENROUTER_API_KEY nor ANTHROPIC_API_KEY)")
            raise ValueError("No API key found (neither OPENROUTER_API_KEY nor ANTHROPIC_API_KEY)")

        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature

    def generate(self, prompt: str, system_message: str = None) -> str:
        logger.debug(f"Generating text with model {self.model_name}, prompt (first 50 chars): {prompt[:50]}")
        try:
            # Anthropic uses a different message format
            messages = [{"role": "user", "content": prompt}]
            
            # Create the request parameters
            request_params = {
                "model": self.model_name,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature
            }
            
            # Add system message if provided
            if system_message:
                request_params["system"] = system_message
            
            response = self.client.messages.create(**request_params)
            
            # Extract content from Anthropic response format
            content = response.content[0].text if response.content else None
            if content is None:
                logger.warning("Anthropic API returned None content.")
                return "Error: LLM returned no content."
            return content.strip()
            
        except anthropic.APIError as e:
            logger.error(f"Anthropic API Error: {e}", exc_info=True)
            return f"Error: Anthropic API issue - {e}"
        except Exception as e:
            logger.error(f"Error calling Anthropic API: {e}", exc_info=True)
            return "Error: Could not get response from LLM due to an unexpected error."

    async def agenerate(self, prompt: str, system_message: str = None) -> str:
        # Basic async wrapper - for true async, would need AsyncAnthropic client
        logger.debug(f"Async generating text with model {self.model_name}, prompt (first 50 chars): {prompt[:50]}")
        # This is NOT truly async with the synchronous client.
        # For simplicity in this placeholder, we call the synchronous one.
        return self.generate(prompt, system_message)

# Example usage (for testing this module directly)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Ensure ANTHROPIC_API_KEY is set in your environment for this test
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Please set the ANTHROPIC_API_KEY environment variable to run this test.")
    else:
        try:
            llm = AnthropicLLM(model_name="claude-3-5-sonnet-20240620", max_tokens=50)
            print(f"AnthropicLLM instance created with model: {llm.model_name}")
            
            test_prompt = "Explain the concept of a language model in one sentence."
            print(f"Testing generate method with prompt: '{test_prompt}'")
            response = llm.generate(test_prompt)
            print(f"LLM Response: {response}")

        except ValueError as ve:
            print(f"Initialization Error: {ve}")
        except Exception as e:
            print(f"An unexpected error occurred during testing: {e}") 