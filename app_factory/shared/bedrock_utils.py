"""
Amazon Bedrock utilities
"""

import os
import logging
import boto3
from typing import List, Dict, Any, Optional
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
        region_name=os.getenv("AWS_REGION", "us-east-1")
    )


def get_bedrock_management_client():
    """Create a bedrock management client for listing models"""
    return boto3.client(
        service_name='bedrock',
        region_name=os.getenv("AWS_REGION", "us-east-1")
    )


def get_supported_models():
    """
    Returns the supported models with their basic information.
    All models support text input/output, Converse API, tool use, and system prompts.
    Models can use either ON_DEMAND or INFERENCE_PROFILE access.
    """
    
    return {
        # Claude Models (includes both ON_DEMAND and INFERENCE_PROFILE models)
        "anthropic.claude-3-haiku-20240307-v1:0": {
            "name": "Claude 3 Haiku",
            "provider": "Anthropic",
            "tier": "fast"
        },
        "anthropic.claude-3-sonnet-20240229-v1:0": {
            "name": "Claude 3 Sonnet", 
            "provider": "Anthropic",
            "tier": "balanced"
        },
        "anthropic.claude-3-5-sonnet-20240620-v1:0": {
            "name": "Claude 3.5 Sonnet",
            "provider": "Anthropic",
            "tier": "balanced"
        },
        "anthropic.claude-3-5-sonnet-20241022-v2:0": {
            "name": "Claude 3.5 Sonnet v2",
            "provider": "Anthropic",
            "tier": "balanced"
        },
        "anthropic.claude-3-5-haiku-20241022-v1:0": {
            "name": "Claude 3.5 Haiku",
            "provider": "Anthropic",
            "tier": "fast"
        },
        "anthropic.claude-3-7-sonnet-20250219-v1:0": {
            "name": "Claude 3.7 Sonnet",
            "provider": "Anthropic",
            "tier": "premium"
        },
        
        # Amazon Nova Models
        "amazon.nova-micro-v1:0": {
            "name": "Amazon Nova Micro",
            "provider": "Amazon",
            "tier": "fast"
        },
        "amazon.nova-lite-v1:0": {
            "name": "Amazon Nova Lite", 
            "provider": "Amazon",
            "tier": "fast"
        },
        "amazon.nova-pro-v1:0": {
            "name": "Amazon Nova Pro",
            "provider": "Amazon", 
            "tier": "balanced"
        },
        
        # Mistral Model
        "mistral.mistral-large-2402-v1:0": {
            "name": "Mistral Large",
            "provider": "Mistral AI",
            "tier": "balanced"
        },
        
        # Cohere Model
        "cohere.command-r-plus-v1:0": {
            "name": "Command R+",
            "provider": "Cohere",
            "tier": "balanced"
        }
    }


def get_available_models(client=None):
    """
    Get models that are actually available in the user's account.
    Accepts both ON_DEMAND and INFERENCE_PROFILE models.
    
    Args:
        client: Optional bedrock management client
        
    Returns:
        List of available model dictionaries
    """
    if client is None:
        client = get_bedrock_management_client()
        
    supported_models = get_supported_models()
    available_models = []
    
    try:
        response = client.list_foundation_models()
        accessible_model_ids = {
            model['modelId'] for model in response['modelSummaries']
            if model.get('inferenceTypesSupported') and 
            (
                'ON_DEMAND' in model.get('inferenceTypesSupported') or 
                'INFERENCE_PROFILE' in model.get('inferenceTypesSupported')
            )
        }
        
        logger.info(f"Found {len(accessible_model_ids)} accessible models in Bedrock")
        
        for model_id, info in supported_models.items():
            if model_id in accessible_model_ids:
                available_models.append({
                    "id": model_id,
                    "name": info["name"],
                    "provider": info["provider"], 
                    "tier": info["tier"]
                })
                logger.debug(f"Added available model: {model_id}")
                
        # Sort by provider and tier for consistent ordering
        available_models.sort(key=lambda x: (x['provider'], x['tier'], x['name']))
        
        logger.info(f"Returning {len(available_models)} supported models")
        return available_models
        
    except Exception as e:
        logger.error(f"Error retrieving available models: {e}")
        return []


def debug_available_models():
    """
    Debug function to show what models are actually available in Bedrock
    """
    try:
        client = get_bedrock_management_client()
        response = client.list_foundation_models()
        
        print("=== ALL MODELS AVAILABLE IN YOUR BEDROCK ACCOUNT ===")
        models_by_provider = {}
        
        for model in response['modelSummaries']:
            model_id = model['modelId']
            provider = model_id.split('.')[0].title()
            
            if provider not in models_by_provider:
                models_by_provider[provider] = []
                
            # Check for both ON_DEMAND and INFERENCE_PROFILE support
            inference_types = model.get('inferenceTypesSupported', [])
            supports_usage = 'ON_DEMAND' in inference_types or 'INFERENCE_PROFILE' in inference_types
            
            models_by_provider[provider].append({
                'id': model_id,
                'name': model.get('modelName', 'Unknown'),
                'on_demand': supports_usage,
                'inference_types': inference_types
            })
        
        for provider in sorted(models_by_provider.keys()):
            print(f"\n{provider}:")
            for model in sorted(models_by_provider[provider], key=lambda x: x['id']):
                status = "✅" if model['on_demand'] else "❌"
                types_str = ", ".join(model['inference_types']) if model['inference_types'] else "None"
                print(f"  {status} {model['id']} - {model['name']} ({types_str})")
        
        print(f"\n=== SUPPORTED BY OUR APP ===")
        supported = get_supported_models()
        for model_id, info in supported.items():
            print(f"  {info['provider']} - {info['name']}: {model_id}")
        
        print(f"\n=== MATCHES ===")
        available = get_available_models(client)
        for model in available:
            print(f"  ✅ {model['provider']} - {model['name']} ({model['tier']}): {model['id']}")
            
    except Exception as e:
        print(f"Error debugging models: {e}")
        print(f"Check your AWS credentials and permissions")


def get_best_available_model(available_models=None, prefer_tier="fast"):
    """
    Get the best available model, preferring fast/cheap models by default.
    
    Args:
        available_models: Optional list of available models
        prefer_tier: Preferred tier ("fast", "balanced", "premium")
        
    Returns:
        str: Model ID to use
    """
    if available_models is None:
        available_models = get_available_models()
        
    if not available_models:
        # Fallback to most common model
        fallback = "anthropic.claude-3-haiku-20240307-v1:0"
        logger.warning(f"No available models found. Using fallback: {fallback}")
        return fallback
    
    # Define preference order by tier and provider
    tier_priority = {"fast": 0, "balanced": 1, "premium": 2}
    provider_priority = {"Anthropic": 0, "Amazon": 1, "Mistral AI": 2, "Cohere": 3}
    
    # If specific tier requested, try to find it first
    if prefer_tier != "fast":
        tier_models = [m for m in available_models if m['tier'] == prefer_tier]
        if tier_models:
            available_models = tier_models
    
    # Sort by preference (tier, then provider)
    available_models.sort(key=lambda x: (
        tier_priority.get(x['tier'], 99),
        provider_priority.get(x['provider'], 99),
        x['name']
    ))
    
    selected_model = available_models[0]['id']
    logger.info(f"Selected model: {selected_model} ({available_models[0]['name']})")
    
    return selected_model


if __name__ == "__main__":
    debug_available_models()