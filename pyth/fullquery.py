"""
Enhanced Bedrock Knowledge Base Query Script
Includes error handling, logging, and configuration management
"""

import boto3
from botocore.exceptions import ClientError, BotoCoreError
import json
import logging
from datetime import datetime
import time
import sys
from pathlib import Path
from typing import Dict, Optional, List
import os

# Configuration Management
class Config:
    """Centralized configuration management"""
    
    # AWS Configuration
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    KNOWLEDGE_BASE_ID = os.getenv('KB_ID', '0U6HHF7FWC')
    MODEL_ARN = os.getenv('MODEL_ARN', 'arn:aws:bedrock:us-east-1:925445553569:inference-profile/us.deepseek.r1-v1:0')
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'kb_queries.log')
    
    # Query Configuration
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_DELAY = int(os.getenv('RETRY_DELAY', '2'))
    QUERY_TIMEOUT = int(os.getenv('QUERY_TIMEOUT', '30'))
    
    # Response Configuration
    MAX_CITATION_LENGTH = int(os.getenv('MAX_CITATION_LENGTH', '200'))
    SAVE_RESPONSES = os.getenv('SAVE_RESPONSES', 'true').lower() == 'true'
    RESPONSE_DIR = os.getenv('RESPONSE_DIR', 'responses')

# Logging Setup
def setup_logging():
    """Configure logging with both file and console handlers"""
    
    # Create logs directory if it doesn't exist
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger('BedrockKB')
    logger.setLevel(getattr(logging, Config.LOG_LEVEL))
    
    # Remove existing handlers
    logger.handlers = []
    
    # File handler with detailed formatting
    file_handler = logging.FileHandler(
        log_dir / Config.LOG_FILE,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    
    # Console handler with simpler formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logging()

# Response Data Classes
class QueryResult:
    """Structured representation of a query result"""
    
    def __init__(self, success: bool, query: str, answer: Optional[str] = None, 
                 citations: Optional[List[Dict]] = None, error: Optional[str] = None, 
                 response_time_ms: Optional[int] = None, metadata: Optional[Dict] = None):
        self.success = success
        self.query = query
        self.answer = answer
        self.citations = citations or []
        self.error = error
        self.response_time_ms = response_time_ms
        self.metadata = metadata or {}
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'success': self.success,
            'query': self.query,
            'answer': self.answer,
            'citations': self.citations,
            'error': self.error,
            'response_time_ms': self.response_time_ms,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }

# Enhanced Bedrock Client
class BedrockKnowledgeBaseClient:
    """Enhanced client with error handling and retry logic"""
    
    def __init__(self):
        """Initialize the Bedrock client with configuration"""
        try:
            self.client = boto3.client(
                'bedrock-agent-runtime',
                region_name=Config.AWS_REGION
            )
            self.kb_id = Config.KNOWLEDGE_BASE_ID
            self.model_arn = Config.MODEL_ARN
            
            logger.info(f"Initialized Bedrock client in region: {Config.AWS_REGION}")
            logger.info(f"Knowledge Base ID: {self.kb_id}")
            logger.info(f"Model ARN: {self.model_arn}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {str(e)}")
            raise
    
    def query(self, question: str, retry_count: int = 0) -> QueryResult:
        """
        Query the knowledge base with retry logic and error handling
        
        Args:
            question: The question to ask
            retry_count: Current retry attempt (internal use)
        
        Returns:
            QueryResult object with response data
        """
        logger.info(f"Querying KB: {question[:100]}...")
        start_time = time.time()
        
        try:
            # Validate input
            if not question or not question.strip():
                raise ValueError("Question cannot be empty")
            
            # Make API call
            response = self.client.retrieve_and_generate(
                input={'text': question},
                retrieveAndGenerateConfiguration={
                    'type': 'KNOWLEDGE_BASE',
                    'knowledgeBaseConfiguration': {
                        'knowledgeBaseId': self.kb_id,
                        'modelArn': self.model_arn
                    }
                }
            )
            
            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Parse response
            result = self._parse_response(response, question, response_time_ms)
            
            logger.info(f"Query successful (took {response_time_ms}ms, "
                       f"{len(result.citations)} citations)")
            
            return result
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            
            logger.error(f"AWS ClientError: {error_code} - {error_msg}")
            
            # Retry on throttling
            if error_code == 'ThrottlingException' and retry_count < Config.MAX_RETRIES:
                wait_time = Config.RETRY_DELAY * (2 ** retry_count)  # Exponential backoff
                logger.warning(f"Throttled. Retrying in {wait_time}s... (attempt {retry_count + 1}/{Config.MAX_RETRIES})")
                time.sleep(wait_time)
                return self.query(question, retry_count + 1)
            
            return QueryResult(
                success=False,
                query=question,
                error=f"{error_code}: {error_msg}",
                response_time_ms=int((time.time() - start_time) * 1000)
            )
            
        except BotoCoreError as e:
            logger.error(f"BotoCoreError: {str(e)}")
            return QueryResult(
                success=False,
                query=question,
                error=f"BotoCoreError: {str(e)}",
                response_time_ms=int((time.time() - start_time) * 1000)
            )
            
        except ValueError as e:
            logger.error(f"ValidationError: {str(e)}")
            return QueryResult(
                success=False,
                query=question,
                error=f"ValidationError: {str(e)}",
                response_time_ms=int((time.time() - start_time) * 1000)
            )
            
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return QueryResult(
                success=False,
                query=question,
                error=f"Unexpected error: {str(e)}",
                response_time_ms=int((time.time() - start_time) * 1000)
            )
    
    def _parse_response(self, response: Dict, question: str, 
                       response_time_ms: int) -> QueryResult:
        """
        Parse the API response into a structured QueryResult
        
        Args:
            response: Raw API response
            question: Original question
            response_time_ms: Response time in milliseconds
        
        Returns:
            Parsed QueryResult object
        """
        try:
            # Extract answer text
            answer = response.get('output', {}).get('text', '')
            
            if not answer:
                logger.warning("Empty answer received from KB")
            
            # Extract and parse citations
            citations = []
            raw_citations = response.get('citations', [])
            
            for citation in raw_citations:
                references = citation.get('retrievedReferences', [])
                
                for ref in references:
                    citation_data = {
                        'text': ref.get('content', {}).get('text', ''),
                        'source': self._extract_source(ref),
                        'metadata': ref.get('metadata', {})
                    }
                    citations.append(citation_data)
            
            # Extract metadata
            metadata = {
                'session_id': response.get('sessionId', ''),
                'citation_count': len(citations),
                'model_arn': self.model_arn,
                'kb_id': self.kb_id
            }
            
            return QueryResult(
                success=True,
                query=question,
                answer=answer,
                citations=citations,
                response_time_ms=response_time_ms,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Error parsing response: {str(e)}", exc_info=True)
            return QueryResult(
                success=False,
                query=question,
                error=f"Response parsing error: {str(e)}",
                response_time_ms=response_time_ms
            )
    
    def _extract_source(self, reference: Dict) -> str:
        """Extract source URI from reference"""
        try:
            location = reference.get('location', {})
            s3_location = location.get('s3Location', {})
            uri = s3_location.get('uri', 'Unknown source')
            
            # Extract just the filename for cleaner display
            if uri and uri != 'Unknown source':
                return uri.split('/')[-1]
            return uri
            
        except Exception as e:
            logger.warning(f"Error extracting source: {str(e)}")
            return 'Unknown source'

# Response Formatter
class ResponseFormatter:
    """Format and display query results"""
    
    @staticmethod
    def print_result(result: QueryResult):
        """Print a formatted query result to console"""
        
        print("\n" + "="*80)
        
        if not result.success:
            print(" QUERY FAILED")
            print("="*80)
            print(f"Error: {result.error}")
            print(f"Response time: {result.response_time_ms}ms")
            print("="*80)
            return
        
        # Print answer
        print(" ANSWER:")
        print("="*80)
        print(result.answer)
        
        # Print citations
        if result.citations:
            print("\n" + "="*80)
            print(f" SOURCES ({len(result.citations)} citations):")
            print("="*80)
            
            for i, citation in enumerate(result.citations, 1):
                print(f"\nSource {i}: {citation['source']}")
                excerpt = citation['text'][:Config.MAX_CITATION_LENGTH]
                if len(citation['text']) > Config.MAX_CITATION_LENGTH:
                    excerpt += "..."
                print(f"Excerpt: {excerpt}")
        
        # Print metadata
        print("\n" + "="*80)
        print("📊 METADATA:")
        print(f"Response time: {result.response_time_ms}ms")
        print(f"Citations: {result.metadata.get('citation_count', 0)}")
        print(f"Session ID: {result.metadata.get('session_id', 'N/A')[:20]}...")
        print("="*80)
    
    @staticmethod
    def save_result(result: QueryResult, filename: Optional[str] = None):
        """Save query result to JSON file"""
        
        if not Config.SAVE_RESPONSES:
            return
        
        try:
            # Create responses directory
            response_dir = Path(Config.RESPONSE_DIR)
            response_dir.mkdir(exist_ok=True)
            
            # Generate filename if not provided
            if not filename:
                timestamp = result.timestamp.strftime('%Y%m%d_%H%M%S')
                filename = f"query_{timestamp}.json"
            
            filepath = response_dir / filename
            
            # Save to JSON
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved response to: {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving response: {str(e)}")

# Main Application
def main():
    """Main application entry point"""
    
    print("="*80)
    print(" Healthcare Knowledge Base Query System")
    print("="*80)
    print(f"Knowledge Base ID: {Config.KNOWLEDGE_BASE_ID}")
    print(f"Region: {Config.AWS_REGION}")
    print(f"Model: DeepSeek R1")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Log file: logs/{Config.LOG_FILE}")
    print("="*80)
    
    # Initialize client
    try:
        client = BedrockKnowledgeBaseClient()
    except Exception as e:
        logger.error(f"Failed to initialize client: {str(e)}")
        sys.exit(1)
    
    # Example questions
    questions = [
        "What is Protected Health Information under HIPAA?",
        "Explain the difference between HIPAA Privacy Rule and Security Rule",
        "What are the normal ranges for a Complete Blood Count?",
        "What is the ICD-10 coding system?",
        "What are HIPAA breach notification requirements?"
    ]
    
    # Process questions
    results = []
    formatter = ResponseFormatter()
    
    for i, question in enumerate(questions, 1):
        print(f"\n\n{'#'*80}")
        print(f"QUESTION {i}/{len(questions)}: {question}")
        print(f"{'#'*80}")
        
        # Query KB
        result = client.query(question)
        results.append(result)
        
        # Display result
        formatter.print_result(result)
        
        # Save result
        formatter.save_result(result)
        
        # Delay between queries
        if i < len(questions):
            time.sleep(1)
    
    # Summary statistics
    print("\n\n" + "="*80)
    print(" SUMMARY STATISTICS")
    print("="*80)
    
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful
    avg_time = sum(r.response_time_ms for r in results if r.success) / max(successful, 1)
    total_citations = sum(len(r.citations) for r in results if r.success)
    
    print(f"Total queries: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Average response time: {avg_time:.0f}ms")
    print(f"Total citations: {total_citations}")
    print(f"Responses saved to: {Config.RESPONSE_DIR}/")
    print("="*80)
    
    logger.info("Query session completed")

if __name__ == "__main__":
    main()
