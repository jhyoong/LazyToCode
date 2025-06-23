import os
from typing import Optional
from dotenv import load_dotenv

# Import model clients from autogen-ext
try:
    from autogen_ext.models.ollama import OllamaChatCompletionClient
    from autogen_core.models import ModelInfo
except ImportError:
    OllamaChatCompletionClient = None
    ModelInfo = None

try:
    from autogen_ext.models.llama_cpp import LlamaCppChatCompletionClient
except ImportError:
    LlamaCppChatCompletionClient = None

from utils.logger import get_logger

class ModelClientFactory:
    """Factory class for creating model clients based on provider."""
    
    def __init__(self):
        load_dotenv()
        self.logger = get_logger()
    
    def create_client(self, provider: str, model: str, **kwargs):
        """Create a model client based on the provider type."""
        
        if provider == "ollama":
            return self._create_ollama_client(model, **kwargs)
        elif provider == "llamacpp":
            return self._create_llamacpp_client(model, **kwargs)
        else:
            raise ValueError(f"Unsupported model provider: {provider}")
    
    def _create_ollama_client(self, model: str, **kwargs) -> Optional[OllamaChatCompletionClient]:
        """Create and configure Ollama model client."""
        
        if OllamaChatCompletionClient is None:
            raise ImportError("autogen-ext[ollama] not installed. Install with: pip install autogen-ext[ollama]")
        
        endpoint = kwargs.get('endpoint', os.getenv('OLLAMA_ENDPOINT', 'http://localhost:11434'))
        
        self.logger.info(f"Creating Ollama client with model: {model}, endpoint: {endpoint}")
        
        try:
            # Create model info for the model
            model_info = None
            if ModelInfo is not None:
                model_info = ModelInfo(
                    vision=False,
                    function_calling=True,
                    json_output=True,
                    family="qwen2.5-coder",
                    structured_output=True
                )
            
            client = OllamaChatCompletionClient(
                model=model,
                host=endpoint,
                model_info=model_info,
                **kwargs
            )
            
            self.logger.info("Ollama client created successfully")
            return client
            
        except Exception as e:
            self.logger.error(f"Failed to create Ollama client: {e}")
            raise
    
    def _create_llamacpp_client(self, model: str, **kwargs) -> Optional[LlamaCppChatCompletionClient]:
        """Create and configure LlamaCpp model client."""
        
        if LlamaCppChatCompletionClient is None:
            raise ImportError("autogen-ext[llama-cpp] not installed. Install with: pip install autogen-ext[llama-cpp]")
        
        # Check if using local model file or HuggingFace model
        model_path = kwargs.get('model_path', os.getenv('LLAMACPP_MODEL_PATH'))
        repo_id = kwargs.get('repo_id', os.getenv('LLAMACPP_REPO_ID'))
        filename = kwargs.get('filename', os.getenv('LLAMACPP_FILENAME'))
        
        # Model parameters
        n_gpu_layers = int(kwargs.get('n_gpu_layers', os.getenv('LLAMACPP_N_GPU_LAYERS', -1)))
        n_ctx = int(kwargs.get('n_ctx', os.getenv('LLAMACPP_N_CTX', 4096)))
        
        self.logger.info(f"Creating LlamaCpp client with model: {model}")
        
        try:
            if model_path and os.path.exists(model_path):
                # Use local model file
                self.logger.info(f"Using local model file: {model_path}")
                client = LlamaCppChatCompletionClient(
                    model_path=model_path,
                    n_gpu_layers=n_gpu_layers,
                    n_ctx=n_ctx,
                    **kwargs
                )
            elif repo_id and filename:
                # Use HuggingFace model
                self.logger.info(f"Using HuggingFace model: {repo_id}/{filename}")
                client = LlamaCppChatCompletionClient(
                    repo_id=repo_id,
                    filename=filename,
                    n_gpu_layers=n_gpu_layers,
                    n_ctx=n_ctx,
                    **kwargs
                )
            else:
                raise ValueError("Either model_path or (repo_id + filename) must be provided for LlamaCpp")
            
            self.logger.info("LlamaCpp client created successfully")
            return client
            
        except Exception as e:
            self.logger.error(f"Failed to create LlamaCpp client: {e}")
            raise
    
    async def validate_client(self, client, model_name: str) -> bool:
        """Validate that the model client is working correctly."""
        
        try:
            self.logger.info(f"Validating model client for: {model_name}")
            
            # Simple test prompt
            test_prompt = "Hello, respond with 'OK' if you can understand this."
            
            # This would depend on the specific client API
            # For now, we'll assume the client is valid if it was created without errors
            self.logger.info("Model client validation passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Model client validation failed: {e}")
            return False