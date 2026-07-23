"""
Amazon Bedrock utilities — lightweight helpers for runtime environment setup.

Model selection is defined in app_factory/mes_agents/config.py (SUPPORTED_MODELS).
This module provides Bedrock client factories used by the daily analysis scripts.
"""

import os
import logging

import boto3
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def get_bedrock_client():
    """Create a bedrock-runtime client using the environment region."""
    return boto3.client(
        service_name='bedrock-runtime',
        region_name=os.getenv("AWS_REGION", "us-east-1")
    )


def get_bedrock_management_client():
    """Create a bedrock management client (for listing models, etc.)."""
    return boto3.client(
        service_name='bedrock',
        region_name=os.getenv("AWS_REGION", "us-east-1")
    )
