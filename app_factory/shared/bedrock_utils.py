"""
Utilities for working with Amazon Bedrock
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
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        endpoint_url=f'https://bedrock-runtime.{os.getenv("AWS_REGION", "us-east-1")}.amazonaws.com',
    )

def get_bedrock_management_client():
    """Create a bedrock management client for listing models"""
    return boto3.client(
        service_name='bedrock',  # Use bedrock service (not bedrock-runtime)
        region_name=os.getenv("AWS_REGION", "us-east-1")
    )

def get_model_features():
    """
    Returns a dictionary mapping models to their features for the Converse API.
    This information is typically static but not accessible through the API directly.
    
    Returns:
        Dictionary mapping model IDs to dictionaries with feature information
    """
    # Lists models that support both Converse API and tool use
    # Based on: https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference-supported-models-features.html
    # and: https://aws.amazon.com/about-aws/whats-new/2024/05/amazon-bedrock-new-converse-api/
    return {
        # Anthropic models
        "anthropic.claude-3-sonnet-20240229-v1:0": {
            "name": "Claude 3 Sonnet",
            "provider": "Anthropic",
            "features": {
                "converse_api": True,
                "tool_use": True,
                "chat": True,
                "image_chat": True,
                "system_prompt": True
            }
        },
        "anthropic.claude-3-haiku-20240307-v1:0": {
            "name": "Claude 3 Haiku",
            "provider": "Anthropic",
            "features": {
                "converse_api": True,
                "tool_use": True,
                "chat": True,
                "image_chat": True,
                "system_prompt": True
            }
        },
        "anthropic.claude-3-opus-20240229-v1:0": {
            "name": "Claude 3 Opus",
            "provider": "Anthropic",
            "features": {
                "converse_api": True,
                "tool_use": True,
                "chat": True,
                "image_chat": True,
                "system_prompt": True
            }
        },
        "anthropic.claude-3-5-sonnet-20240620-v1:0": {
            "name": "Claude 3.5 Sonnet",
            "provider": "Anthropic",
            "features": {
                "converse_api": True,
                "tool_use": True,
                "chat": True,
                "image_chat": True,
                "system_prompt": True
            }
        },
        "anthropic.claude-3-7-sonnet-20250219": {
            "name": "Claude 3.7 Sonnet",
            "provider": "Anthropic",
            "features": {
                "converse_api": True,
                "tool_use": True,
                "chat": True,
                "image_chat": True,
                "system_prompt": True
            }
        },
        # Amazon Nova models
        "amazon.nova-pro-v1:0": {
            "name": "Amazon Nova Pro",
            "provider": "Amazon",
            "use_region_prefix": True,
            "features": {
                "converse_api": True,
                "tool_use": True,
                "chat": True,
                "image_chat": False,
                "system_prompt": True
            }
        },
        "amazon.nova-lite-v1:0": {
            "name": "Amazon Nova Lite",
            "provider": "Amazon",
            "use_region_prefix": True,
            "features": {
                "converse_api": True,
                "tool_use": True,
                "chat": True,
                "image_chat": False,
                "system_prompt": True
            }
        },
        "amazon.nova-micro-v1:0": {
            "name": "Amazon Nova Micro",
            "provider": "Amazon",
            "use_region_prefix": True,
            "features": {
                "converse_api": True,
                "tool_use": True,
                "chat": True,
                "image_chat": False,
                "system_prompt": True
            }
        },
        # AI21 models
        "ai21.jamba-1-5-mini-v1:0": {
            "name": "Jamba 1.5 Mini",
            "provider": "AI21",
            "features": {
                "converse_api": True,
                "tool_use": True,
                "chat": True,
                "image_chat": False,
                "system_prompt": False
            }
        },
        "ai21.jamba-1-5-large-v1:0": {
            "name": "Jamba 1.5 Large",
            "provider": "AI21",
            "features": {
                "converse_api": True,
                "tool_use": True,
                "chat": True,
                "image_chat": False,
                "system_prompt": False
            }
        },
        # Cohere models
        "cohere.command-r-v1:0": {
            "name": "Command R",
            "provider": "Cohere",
            "features": {
                "converse_api": True,
                "tool_use": True,
                "chat": True,
                "image_chat": False,
                "system_prompt": True
            }
        },
        "cohere.command-r-plus-v1:0": {
            "name": "Command R+",
            "provider": "Cohere",
            "features": {
                "converse_api": True,
                "tool_use": True,
                "chat": True,
                "image_chat": False,
                "system_prompt": True
            }
        },
        # Mistral models
        "mistral.mistral-large-2402-v1:0": {
            "name": "Mistral Large (24.02)",
            "provider": "Mistral AI",
            "features": {
                "converse_api": True,
                "tool_use": True,
                "chat": True,
                "image_chat": False,
                "system_prompt": True
            }
        },
        "mistral.mistral-small-2402-v1:0": {
            "name": "Mistral Small (24.02)",
            "provider": "Mistral AI",
            "features": {
                "converse_api": True,
                "tool_use": True,
                "chat": True,
                "image_chat": False,
                "system_prompt": True
            }
        },
        "mistral.mistral-7b-instruct-v0:2": {
            "name": "Mistral 7B Instruct",
            "provider": "Mistral AI",
            "features": {
                "converse_api": True,
                "tool_use": True,
                "chat": True,
                "image_chat": False,
                "system_prompt": True
            }
        },
        "mistral.mixtral-8x7b-instruct-v0:1": {
            "name": "Mixtral 8x7B Instruct",
            "provider": "Mistral AI",
            "features": {
                "converse_api": True,
                "tool_use": True,
                "chat": True,
                "image_chat": False,
                "system_prompt": True
            }
        },
        # Meta models
        "meta.llama3-1-405b-instruction-v1:0": {
            "name": "Llama 3.1 405B",
            "provider": "Meta",
            "features": {
                "converse_api": True,
                "tool_use": True,
                "chat": True,
                "image_chat": False,
                "system_prompt": True
            }
        },
        "meta.llama3-1-70b-instruction-v1:0": {
            "name": "Llama 3.1 70B",
            "provider": "Meta",
            "features": {
                "converse_api": True,
                "tool_use": True,
                "chat": True,
                "image_chat": False,
                "system_prompt": True
            }
        },
        "meta.llama3-2-11b-instruct-v1:0": {
            "name": "Llama 3.2 11B",
            "provider": "Meta",
            "features": {
                "converse_api": True, 
                "tool_use": True,
                "chat": True,
                "image_chat": False,
                "system_prompt": True
            }
        },
        "meta.llama3-2-90b-instruct-v1:0": {
            "name": "Llama 3.2 90B",
            "provider": "Meta",
            "features": {
                "converse_api": True,
                "tool_use": True,
                "chat": True,
                "image_chat": False,
                "system_prompt": True
            }
        }
    }

def get_available_bedrock_models(client=None, filter_features=None):
    """
    Retrieves available Bedrock models with optional feature filtering.
    
    Args:
        client: An optional boto3 bedrock client. If not provided, a new one will be created.
        filter_features: Dictionary of features to filter models by, e.g. {"converse_api": True, "tool_use": True}
        
    Returns:
        A list of dictionaries containing model details (id, name, provider, features) for models that:
        1. Are accessible to the user account
        2. Match the requested features if filter_features is provided
    """
    # Create a Bedrock client if not provided
    if client is None:
        client = get_bedrock_management_client()
    
    # Get model features information
    model_features = get_model_features()
        
    try:
        # List all foundation models available to the user
        response = client.list_foundation_models()
        
        # Filter models based on availability and requested features
        available_models = []
        
        for model in response['modelSummaries']:
            model_id = model['modelId']
            
            # For Amazon models, we need to check if a region prefix is needed
            inference_id = None
            
            # Try direct match first
            if model_id in model_features:
                inference_id = model_id
            
            # Check if model ID needs region prefix (primarily Amazon models)
            region = os.getenv("AWS_REGION", "us-east-1")
            region_prefix = f"{region.split('-')[0]}."  # e.g., "us."
            prefixed_id = f"{region_prefix}{model_id}"
            
            # Check for models where we need to add region prefix 
            for feature_model_id, info in model_features.items():
                # If the model uses region prefix and matches after removing prefix
                if (info.get("use_region_prefix") and 
                    feature_model_id == model_id and 
                    not model_id.startswith(region_prefix)):
                    inference_id = prefixed_id
                    break
                # If the model matches after adding region prefix
                elif feature_model_id == prefixed_id:
                    inference_id = prefixed_id
                    break
            
            # If we found a match in our features list
            if inference_id is not None and (model_id in model_features or prefixed_id in model_features):
                # Get the correct model ID to look up in our features dictionary
                features_id = model_id if model_id in model_features else prefixed_id
                
                # Check if the model is accessible to the user (inferenceTypes contains "ON_DEMAND")
                if model.get('inferenceTypesSupported') and 'ON_DEMAND' in model.get('inferenceTypesSupported'):
                    # If filter_features is provided, check if model has all requested features
                    features_match = True
                    if filter_features:
                        for feature, value in filter_features.items():
                            model_value = model_features[features_id].get("features", {}).get(feature, False)
                            if model_value != value:
                                features_match = False
                                break
                    
                    if features_match:
                        # Add to available models
                        model_info = {
                            "id": inference_id,  # ID to use for API calls
                            "name": model_features[features_id]["name"],
                            "provider": model_features[features_id]["provider"],
                            "features": model_features[features_id].get("features", {})
                        }
                        available_models.append(model_info)
        
        # Sort models by provider and name for better display
        available_models.sort(key=lambda x: (x['provider'], x['name']))
        
        return available_models
        
    except Exception as e:
        logger.error(f"Error retrieving available models: {e}")
        # Return an empty list since we couldn't retrieve models
        return []

def get_tool_use_converse_models(client=None):
    """
    Helper function to get models that support both tool use and the Converse API.
    
    Args:
        client: An optional boto3 bedrock client. If not provided, a new one will be created.
        
    Returns:
        A list of dictionaries containing model details for models supporting both features.
    """
    return get_available_bedrock_models(
        client=client,
        filter_features={
            "converse_api": True,
            "tool_use": True
        }
    )

def test_available_models():
    """Test function to display available models with tool use and Converse API support"""
    models = get_tool_use_converse_models()
    
    if not models:
        print("No models found supporting both Converse API and tool use.")
        return
    
    print(f"Found {len(models)} models supporting both Converse API and tool use:")
    for model in models:
        print(f"- {model['name']} ({model['provider']}): {model['id']}")
    
    return models

def get_best_available_model(available_models=None):
    """
    Get the best available model for AI insights from the provided list
    or fetch available models if none provided.
    
    Args:
        available_models (list, optional): List of available models with tool use capability.
                                          If None, will be fetched.
    
    Returns:
        str: Model ID to use
    """
    
    # Define preferred lightweight models in order of preference
    preferred_models = [
        "anthropic.claude-3-haiku-20240307-v1:0",  # Claude 3 Haiku
        "us.amazon.nova-lite-v1:0"                # Amazon Nova Lite
    ]
    
    try:
        # Get models that support both tool use and Converse API if not provided
        if available_models is None:
            available_models = get_tool_use_converse_models()
        
        # Find first available preferred model
        model_id = None
        for preferred in preferred_models:
            if any(m['id'] == preferred for m in available_models):
                model_id = preferred
                logging.info(f"Selected preferred model: {model_id}")
                break
        
        # If no preferred model found, use first available model with suitable features
        if not model_id and available_models:
            # Prioritize models from specific providers if available
            for provider in ["Anthropic", "Amazon"]:
                provider_models = [m for m in available_models if m['provider'] == provider]
                if provider_models:
                    model_id = provider_models[0]['id']
                    logging.info(f"Selected {provider} model: {model_id}")
                    break
            
            # If still no model selected, just use the first available
            if not model_id:
                model_id = available_models[0]['id']
                logging.info(f"Selected first available model: {model_id}")
        
        # Fallback default if all else fails
        if not model_id:
            model_id = "anthropic.claude-3-haiku-20240307-v1:0"
            logging.warning(f"No available models found. Using fallback default: {model_id}")
    
    except Exception as e:
        # Log the error and use a default model
        logging.error(f"Error selecting model: {e}")
        model_id = "anthropic.claude-3-haiku-20240307-v1:0" 
        logging.warning(f"Using fallback default model due to error: {model_id}")
    
    return model_id

if __name__ == "__main__":
    # Run test to display models
    test_available_models()