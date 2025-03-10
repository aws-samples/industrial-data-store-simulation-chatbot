"""
Utilities for working with Amazon Bedrock
"""

import os
import logging
import boto3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_bedrock_client():
    """Create a bedrock-runtime client"""
    return boto3.client(
        service_name='bedrock-runtime',
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        endpoint_url=f'https://bedrock-runtime.{os.getenv("AWS_REGION", "us-east-1")}.amazonaws.com',
    )

def get_bedrock_management_client():
    """Create a bedrock management client for listing models"""
    return boto3.client(
        service_name='bedrock',  # Use bedrock service (not bedrock-runtime)
        region_name=os.getenv("AWS_REGION", "us-east-1")
    )

def get_available_bedrock_models(client=None):
    """
    Retrieves all Bedrock models available to the user that support tool use with the Converse API.
    
    Args:
        client: An optional boto3 bedrock client. If not provided, a new one will be created.
        
    Returns:
        A list of dictionaries containing model details (id, name, provider) for models that:
        1. Are accessible to the user account
        2. Support Converse API
        3. Support tool use
    """
        
    # models that support both Converse API and tool use based on documentation
    MODELS_WITH_TOOL_USE = {
        # Anthropic models (don't use region prefix)
        "anthropic.claude-3-sonnet-20240229-v1:0": {
            "name": "Claude 3 Sonnet",
            "provider": "Anthropic"
        },
        "anthropic.claude-3-haiku-20240307-v1:0": {
            "name": "Claude 3 Haiku",
            "provider": "Anthropic"
        },
        "anthropic.claude-3-opus-20240229-v1:0": {
            "name": "Claude 3 Opus",
            "provider": "Anthropic"
        },
        "anthropic.claude-3-5-sonnet-20240620-v1:0": {
            "name": "Claude 3.5 Sonnet",
            "provider": "Anthropic"
        },
        "anthropic.claude-3-5-sonnet-20240620-v1:0": {
            "name": "Claude 3.5 Sonnet v2",
            "provider": "Anthropic"
        },
        "anthropic.claude-3-7-sonnet-20250219": {
            "name": "Claude 3.7 Sonnet",
            "provider": "Anthropic"
        },
        # Amazon models (use region prefix)
        "us.amazon.nova-pro-v1:0": {
            "name": "Amazon Nova Pro",
            "provider": "Amazon",
            "base_model_id": "amazon.nova-pro-v1:0"  # Base model ID without region prefix
        },
        "us.amazon.nova-lite-v1:0": {
            "name": "Amazon Nova Lite",
            "provider": "Amazon",
            "base_model_id": "amazon.nova-lite-v1:0"
        },
        "us.amazon.nova-micro-v1:0": {
            "name": "Amazon Nova Micro",
            "provider": "Amazon",
            "base_model_id": "amazon.nova-micro-v1:0"
        },
        # AI21 models
        "ai21.jamba-1-5-mini-v1:0": {
            "name": "Jamba 1.5 Mini",
            "provider": "AI21"
        },
        "ai21.jamba-1-5-large-v1:0": {
            "name": "Jamba 1.5 Large",
            "provider": "AI21"
        },
        # Cohere models 
        "cohere.command-r-v1:0": {
            "name": "Command R",
            "provider": "Cohere"
        },
        "cohere.command-r-plus-v1:0": {
            "name": "Command R+",
            "provider": "Cohere"
        },
        # Mistral models - updated based on mistralmodels.json
        "mistral.mistral-7b-instruct-v0:2": {
            "name": "Mistral 7B Instruct",
            "provider": "Mistral AI"
        },
        "mistral.mixtral-8x7b-instruct-v0:1": {
            "name": "Mixtral 8x7B Instruct",
            "provider": "Mistral AI"
        },
        "mistral.mistral-large-2402-v1:0": {
            "name": "Mistral Large (24.02)",
            "provider": "Mistral AI"
        },
        "mistral.mistral-small-2402-v1:0": {
            "name": "Mistral Small (24.02)",
            "provider": "Mistral AI"
        },
        # Meta models
        "meta.llama3-1-405b-instruction-v1:0": {
            "name": "Llama 3.1 405B",
            "provider": "Meta"
        },
        "meta.llama3-1-70b-instruction-v1:0": {
            "name": "Llama 3.1 70B",
            "provider": "Meta"
        },
        "meta.llama3-2-11b-instruct-v1:0": {
            "name": "Llama 3.2 11B",
            "provider": "Meta"
        },
        "meta.llama3-2-90b-instruct-v1:0": {
            "name": "Llama 3.2 90B",
            "provider": "Meta"
        }
    }
    
    # Create a Bedrock client if not provided
    if client is None:
        client = get_bedrock_management_client()
    
    try:
        # List all foundation models available to the user
        response = client.list_foundation_models()
        
        # Filter models that are both available to the user and in our tool use list
        available_models = []
        
        for model in response['modelSummaries']:
            model_id = model['modelId']  # This is the base Model ID from the API
            
            # For Amazon models, we need to map from base Model ID to Inference Profile ID
            inference_id = None
            
            # Direct match (for most models)
            if model_id in MODELS_WITH_TOOL_USE:
                inference_id = model_id
            
            # Check for Amazon models that need region prefix
            for tool_model_id, info in MODELS_WITH_TOOL_USE.items():
                if "base_model_id" in info and info["base_model_id"] == model_id:
                    inference_id = tool_model_id
                    break
            
            # If we found a matching inference ID that supports tool use
            if inference_id and inference_id in MODELS_WITH_TOOL_USE:
                # Check if the model is accessible to the user (inferenceTypes contains "ON_DEMAND")
                if model.get('inferenceTypesSupported') and 'ON_DEMAND' in model.get('inferenceTypesSupported'):
                    # Add to available models
                    model_info = MODELS_WITH_TOOL_USE[inference_id].copy()
                    model_info['id'] = inference_id  # Store the Inference Profile ID for API calls
                    model_info['base_id'] = model_id  # Also store the base Model ID for reference
                    available_models.append(model_info)
        
        # Sort models by provider and name for better display
        available_models.sort(key=lambda x: (x['provider'], x['name']))
        
        return available_models
        
    except Exception as e:
        logger.error(f"Error retrieving available models: {e}")
        # Return a default list of models that are likely to be available
        default_models = [
            {"id": "anthropic.claude-3-haiku-20240307-v1:0", "name": "Claude 3 Haiku", "provider": "Anthropic"},
            {"id": "us.amazon.nova-lite-v1:0", "name": "Nova Lite", "provider": "Amazon"},
        ]
        return default_models
