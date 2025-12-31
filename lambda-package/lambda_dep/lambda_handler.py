"""
AWS Lambda handler for Healthcare RAG Assistant
Provides API endpoint for patient-specific clinical queries
"""

import json
import os
from datetime import datetime
from typing import Dict
import boto3
from botocore.exceptions import ClientError
import psycopg2

# Load .env for local testing only (Lambda uses environment variables natively)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # In Lambda, dotenv won't be installed (and isn't needed)

# Import core classes
from healthcare_assistant import Config, PatientDataRetriever, HealthcareAssistant


def lambda_handler(event, context):
    """
    AWS Lambda entry point for healthcare queries
    
    Expected event format (API Gateway):
    {
        "body": {
            "subject_id": 10000032,
            "question": "What medications is this patient on?",
            "session_id": "optional-session-id"
        }
    }
    
    Or direct invocation:
    {
        "subject_id": 10000032,
        "question": "What medications is this patient on?",
        "session_id": "optional-session-id"
    }
    """
    
    try:
        # Parse request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', event)  # Handle direct invocation
        
        # Extract parameters
        subject_id = body.get('subject_id')
        question = body.get('question')
        session_id = body.get('session_id')
        
        # Validate required inputs
        if not subject_id:
            return error_response(400, "Missing required field: subject_id")
        
        if not question:
            return error_response(400, "Missing required field: question")
        
        # Validate subject_id exists
        retriever = PatientDataRetriever()
        if not retriever.validate_subject_id(subject_id):
            retriever.close()
            return error_response(404, f"Subject ID {subject_id} not found in database")
        retriever.close()
        
        # Initialize assistant
        assistant = HealthcareAssistant(subject_id=subject_id, session_id=session_id)
        
        # Query with patient context
        result = assistant.query(question)
        
        # Clean up
        assistant.close()
        
        # Return response
        if result['success']:
            return success_response({
                'subject_id': subject_id,
                'question': question,
                'answer': result['answer'],
                'citations': result.get('citations', []),
                'session_id': result.get('session_id'),
                'response_time_ms': result.get('response_time_ms'),
                'query_type': result.get('query_type', 'unknown'),
                'timestamp': datetime.now().isoformat()
            })
        else:
            return error_response(500, result.get('error', 'Query failed'), {
                'response_time_ms': result.get('response_time_ms')
            })
    
    except json.JSONDecodeError as e:
        return error_response(400, f"Invalid JSON in request body: {str(e)}")
    
    except psycopg2.Error as e:
        return error_response(503, f"Database error: {str(e)}")
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        return error_response(502, f"AWS Bedrock error: {error_code} - {error_message}")
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"ERROR: {error_trace}")  # CloudWatch logs
        return error_response(500, f"Internal server error: {str(e)}")


def success_response( Dict, status_code: int = 200) -> Dict:
    """Format successful API response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',  # Configure CORS as needed
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'POST, OPTIONS'
        },
        'body': json.dumps(data, default=str)  # default=str handles datetime serialization
    }


def error_response(status_code: int, message: str, details: Dict = None) -> Dict:
    """Format error API response"""
    error_body = {
        'error': message,
        'timestamp': datetime.now().isoformat()
    }
    
    if details:
        error_body['details'] = details
    
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'POST, OPTIONS'
        },
        'body': json.dumps(error_body)
    }


def health_check(event, context):
    """
    Health check endpoint for monitoring
    Can be invoked separately or via API Gateway /health
    """
    try:
        # Test database connection
        retriever = PatientDataRetriever()
        retriever.cursor.execute("SELECT 1")
        retriever.close()
        
        return success_response({
            'status': 'healthy',
            'service': 'healthcare-rag-assistant',
            'database': 'connected',
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        return error_response(503, 'Service unhealthy', {
            'database': 'disconnected',
            'error': str(e)
        })
