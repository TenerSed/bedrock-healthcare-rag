"""
Interactive Healthcare Assistant CLI - Full MIMIC-IV Integration
Patient-specific RAG system using complete MIMIC-IV dataset + AWS Bedrock
"""

import sys
from healthcare_assistant import HealthcareAssistant, PatientDataRetriever


def print_header():
    print("\n" + "="*80)
    print(" HEALTHCARE ASSISTANT - MIMIC-IV Clinical Intelligence System")
    print("="*80)
    print("Powered by AWS Bedrock (DeepSeek R1) + Complete MIMIC-IV Database")
    print("Hybrid Query: Direct for patient data | KB for medical knowledge")
    print("="*80 + "\n")


def print_patient_summary(assistant: HealthcareAssistant):
    print("\n" + assistant.patient_context)


def main():
    print_header()
    
    # Get Subject ID
    while True:
        try:
            subject_id_input = input("Enter MIMIC-IV Subject ID (or 'quit'): ").strip()
            
            if subject_id_input.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye! \n")
                sys.exit(0)
            
            subject_id = int(subject_id_input)
            
            # Validate
            retriever = PatientDataRetriever()
            if not retriever.validate_subject_id(subject_id):
                print(f" Subject ID {subject_id} not found in database.\n")
                retriever.close()
                continue
            
            retriever.close()
            break
            
        except ValueError:
            print(" Please enter a valid numeric Subject ID.\n")
        except Exception as e:
            print(f" Database error: {str(e)}\n")
            sys.exit(1)
    
    # Initialize Assistant
    print(f"\n Loading complete clinical record for Subject ID: {subject_id}...\n")
    
    try:
        assistant = HealthcareAssistant(subject_id)
    except Exception as e:
        print(f" Error initializing assistant: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Show Full Patient Profile
    print_patient_summary(assistant)
    
    # Interactive Loop
    print("\nAsk clinical questions about this patient or general healthcare topics.")
    print("Commands: 'summary' = session stats | 'profile' = show patient data | 'quit' = exit\n")
    
    while True:
        try:
            question = input("\n Your question: ").strip()
            
            if not question:
                continue
            
            if question.lower() in ['quit', 'exit', 'q']:
                print(assistant.get_conversation_summary())
                print("\nThank you for using Healthcare Assistant. Goodbye! \n")
                assistant.close()
                break
            
            if question.lower() == 'summary':
                print(assistant.get_conversation_summary())
                continue
            
            if question.lower() == 'profile':
                print_patient_summary(assistant)
                continue
            
            # Query Assistant
            print("\n Analyzing patient data and retrieving relevant medical knowledge...")
            result = assistant.query(question)
            
            if result['success']:
                print("\n" + "─"*80)
                print(" CLINICAL ANSWER:")
                print("─"*80)
                print(result['answer'])
                
                # Show query type and response time
                query_type_text = "Knowledge Base" if result.get('query_type') == 'kb' else "Patient Data"
                print(f"\n Query type: {query_type_text}")
                print(f"  Response time: {result['response_time_ms']}ms")
                
                if result['citations']:
                    print("\n KNOWLEDGE SOURCES:")
                    seen_sources = set()
                    for i, citation in enumerate(result['citations'], 1):
                        refs = citation.get('retrievedReferences', [])
                        for ref in refs:
                            source = ref.get('location', {}).get('s3Location', {}).get('uri', '')
                            if source:
                                source_name = source.split('/')[-1]
                                if source_name not in seen_sources:
                                    print(f"  [{i}] {source_name}")
                                    seen_sources.add(source_name)
                
                print("─"*80)
            else:
                print(f"\n Error: {result['error']}")
                if 'response_time_ms' in result:
                    print(f"  Failed after: {result['response_time_ms']}ms\n")
        
        except KeyboardInterrupt:
            print("\n" + assistant.get_conversation_summary())
            print("\nInterrupted. Goodbye! \n")
            assistant.close()
            break
        except Exception as e:
            print(f"\n Unexpected error: {str(e)}\n")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
