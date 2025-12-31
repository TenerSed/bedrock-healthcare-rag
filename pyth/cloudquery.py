#!/usr/bin/env python3
"""
Healthcare RAG API Client - CLI
Query the Lambda API endpoint from command line
"""

import requests
import json
import sys
from datetime import datetime
import argparse
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Configuration
api_endpoint = os.getenv("API_ENDPOINT", "")


def query_api(subject_id: int, question: str, session_id: str = None) -> dict:
	"""Send query to Lambda API"""

	payload = {
		"subject_id": subject_id,
		"question": question
	}

	if session_id:
		payload["session_id"] = session_id

	print(f"\n Sending request to API...")
	print(f"   Subject ID: {subject_id}")
	print(f"   Question: {question}")

	try:
		start_time = datetime.now()
		response = requests.post(
			api_endpoint,
			json=payload,
			headers={"Content-Type": "application/json"},
			timeout=120  # 2 minute timeout
		)
		client_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

		return {
			"status_code": response.status_code,
			"data": response.json(),
			"client_time_ms": client_time_ms
		}

	except requests.exceptions.Timeout:
		return {
			"status_code": 408,
			"data": {"error": "Request timed out after 120 seconds"},
			"client_time_ms": 120000
		}

	except requests.exceptions.ConnectionError:
		return {
			"status_code": 503,
			"data": {"error": f"Could not connect to API endpoint: {api_endpoint}"},
			"client_time_ms": 0
		}

	except Exception as e:
		return {
			"status_code": 500,
			"data": {"error": f"Unexpected error: {str(e)}"},
			"client_time_ms": 0
		}


def print_response(result: dict):
	"""Pretty print the API response"""

	status_code = result["status_code"]
	data = result["data"]
	client_time = result["client_time_ms"]

	print("\n" + "=" * 80)

	if status_code == 200:
		print(" SUCCESS")
		print("=" * 80)

		# Main answer
		print("\n ANSWER:")
		print("-" * 80)
		answer = data.get("answer", "No answer provided")
		print(answer)
		print("-" * 80)

		# Metadata
		print("\n METADATA:")
		print(f"   Subject ID: {data.get('subject_id')}")
		print(f"   Query Type: {data.get('query_type', 'unknown')}")
		print(f"   Session ID: {data.get('session_id', 'N/A')}")
		print(f"   Server Response Time: {data.get('response_time_ms', 0)} ms")
		print(f"   Total Round Trip Time: {client_time} ms")
		print(f"   Timestamp: {data.get('timestamp', 'N/A')}")

		# Citations
		citations = data.get('citations', [])
		if citations:
			print(f"\n CITATIONS: ({len(citations)})")
			for i, citation in enumerate(citations, 1):
				refs = citation.get('retrievedReferences', [])
				for ref in refs:
					source = ref.get('location', {}).get('s3Location', {}).get('uri', '')
					if source:
						source_name = source.split('/')[-1]
						print(f"   [{i}] {source_name}")
		else:
			print(f"\n CITATIONS: None")

	else:
		print(f" ERROR (HTTP {status_code})")
		print("=" * 80)
		error_msg = data.get('error', 'Unknown error')
		print(f"\n{error_msg}")

		if 'details' in data:
			print(f"\nDetails: {json.dumps(data['details'], indent=2)}")

		print(f"\nResponse Time: {client_time} ms")

	print("\n" + "=" * 80)


def _print_final_stats(conversation: list, session_start: datetime, subject_id: int, session_id: str = None):
	total_queries = len(conversation)
	total_client_ms = sum(item.get('client_time_ms', 0) for item in conversation)
	avg_ms = int(total_client_ms / total_queries) if total_queries else 0
	duration_s = int((datetime.now() - session_start).total_seconds())

	print("\n" + "=" * 60)
	print("SESSION SUMMARY")
	print("=" * 60)
	print(f" Subject ID: {subject_id}")
	print(f" Session ID: {session_id or 'N/A'}")
	print(f" Questions asked: {total_queries}")
	print(f" Total client round-trip time: {total_client_ms} ms")
	print(f" Average response time: {avg_ms} ms")
	print(f" Session duration: {duration_s} seconds")
	if total_queries:
		print("\n Recent questions:")
		for i, q in enumerate(conversation[-10:], 1):
			ts = q.get('timestamp').strftime("%Y-%m-%d %H:%M:%S")
			print(f"  [{i}] {ts} | {q.get('question')[:120]} ... | {q.get('client_time_ms')} ms | HTTP {q.get('status_code')}")
	print("=" * 60 + "\n")


def interactive_mode():
	"""Interactive CLI mode where subject ID is entered once, then a conversation follows."""
	print("\n" + "=" * 80)
	print(" HEALTHCARE RAG API CLIENT - Interactive Mode")
	print("=" * 80)
	print(f"API Endpoint: {api_endpoint}")
	print("Type 'quit' or 'exit' to end session")
	print("Type 'summary' to view a short session summary (will not end session)")
	print("=" * 80 + "\n")

	# Ask subject ID once
	subject_id = None
	while True:
		try:
			subject_input = input("Enter Subject ID (or 'quit'): ").strip()
			if subject_input.lower() in ['quit', 'exit', 'q']:
				print("\n Goodbye!\n")
				return
			subject_id = int(subject_input)
			break
		except ValueError:
			print(" Invalid Subject ID. Must be a number.\n")
		except KeyboardInterrupt:
			print("\n\n Interrupted. Goodbye!\n")
			return

	session_id = None
	conversation = []
	session_start = datetime.now()

	print(f"\nStarting conversation for Subject ID: {subject_id}. You may now ask questions.\n")

	while True:
		try:
			question = input("Your question (or 'quit'/'summary'): ").strip()
			if not question:
				continue

			if question.lower() in ['quit', 'exit', 'q']:
				_print_final_stats(conversation, session_start, subject_id, session_id)
				print("\n Goodbye!\n")
				break

			if question.lower() == 'summary':
				_print_final_stats(conversation, session_start, subject_id, session_id)
				continue

			# Query API
			result = query_api(subject_id, question, session_id)
			print_response(result)

			# Track conversation entry
			conversation.append({
				'question': question,
				'status_code': result.get('status_code'),
				'client_time_ms': result.get('client_time_ms', 0),
				'timestamp': datetime.now()
			})

			# Update session_id for follow-ups if provided by server
			if result["status_code"] == 200:
				session_id = result["data"].get("session_id", session_id)

			print()  # Blank line before next question

		except KeyboardInterrupt:
			_print_final_stats(conversation, session_start, subject_id, session_id)
			print("\n\n Interrupted. Goodbye!\n")
			break
		except Exception as e:
			print(f"\n Error: {str(e)}\n")


def main():
  global api_endpoint 

  parser = argparse.ArgumentParser(
    description="Healthcare RAG API Client - Query Lambda endpoint",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
Examples:
  # Interactive mode
  python query_api.py

  # Direct query
  python query_api.py --subject-id 10000032 --question "What are my diagnoses?"

  # With session ID (for follow-up)
  python query_api.py -s 10000032 -q "What medications?" --session abc-123
    """
  )

  parser.add_argument(
    '-s', '--subject-id',
    type=int,
    help='Patient subject ID'
  )

  parser.add_argument(
    '-q', '--question',
    type=str,
    help='Clinical question to ask'
  )

  parser.add_argument(
    '--session',
    type=str,
    help='Session ID for follow-up questions'
  )

  parser.add_argument(
    '--endpoint',
    type=str,
    default=api_endpoint, # Now this correctly reads the global variable
    help='Override API endpoint URL'
  )

  args = parser.parse_args()

  # Update endpoint if provided
  if args.endpoint:
    # This now updates the global variable, so query_api() sees the change
    api_endpoint = args.endpoint

  # Direct query mode or interactive mode
  if args.subject_id and args.question:
    result = query_api(args.subject_id, args.question, args.session)
    print_response(result)
  else:
    if args.subject_id or args.question:
      print(" Error: Both --subject-id and --question are required for direct query mode.")
      print("   Run without arguments for interactive mode.\n")
      sys.exit(1)

    interactive_mode()


if __name__ == "__main__":
	main()
