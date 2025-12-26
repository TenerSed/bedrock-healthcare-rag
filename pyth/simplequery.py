"""
Simple Bedrock Knowledge Base Query Script
"""

import boto3
from datetime import datetime
import time

client = boto3.client(
    'bedrock-agent-runtime',
    region_name='us-east-1'
)

KNOWLEDGE_BASE_ID = '0U6HHF7FWC'
MODEL_ARN = 'arn:aws:bedrock:us-east-1:925445553569:inference-profile/us.deepseek.r1-v1:0'

def query_knowledge_base(question):
    try:
        response = client.retrieve_and_generate(
            input={
                'text': question
            },
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': KNOWLEDGE_BASE_ID,
                    'modelArn': MODEL_ARN
                }
            }
        )
        return response
    except Exception as e:
        print(f"Error querying knowledge base: {str(e)}")
        return None

def print_response(response):
    if not response:
        print("No response received")
        return
    
    generated_text = response['output']['text']
    
    print("\n" + "="*80)
    print("ANSWER:")
    print("="*80)
    print(generated_text)
    
    citations = response.get('citations', [])
    if citations:
        print("\n" + "="*80)
        print("SOURCES:")
        print("="*80)
        for i, citation in enumerate(citations, 1):
            print(f"\nSource {i}:")
            references = citation.get('retrievedReferences', [])
            for ref in references:
                content = ref.get('content', {}).get('text', 'N/A')
                location = ref.get('location', {})
                s3_location = location.get('s3Location', {})
                uri = s3_location.get('uri', 'Unknown source')
                print(f"  Document: {uri}")
                print(f"  Excerpt: {content[:200]}...")
    
    print("\n" + "="*80)

def main():
    questions = [
        "What is Protected Health Information under HIPAA?",
        "Explain the difference between HIPAA Privacy Rule and Security Rule",
        "What are the normal ranges for a Complete Blood Count?",
        "What is the ICD-10 coding system?",
        "What are HIPAA breach notification requirements?"
    ]
    
    print(f"Healthcare Knowledge Base Query System")
    print(f"Knowledge Base ID: {KNOWLEDGE_BASE_ID}")
    print(f"Model: Amazon Nova Lite")
    print(f"Region: us-east-1")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    for question in questions:
        print(f"\n\n{'#'*80}")
        print(f"QUESTION: {question}")
        print(f"{'#'*80}")
        
        response = query_knowledge_base(question)
        print_response(response)
        time.sleep(1)

if __name__ == "__main__":
    main()
