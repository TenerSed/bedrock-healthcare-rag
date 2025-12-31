# Bedrock Healthcare RAG

This project implements a Retrieval-Augmented Generation (RAG) system for healthcare, using AWS Bedrock, Lambda, S3, and a PostgreSQL database. The system can answer questions about patients, referencing their clinical data and a knowledge base of medical documents.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         HEALTHCARE RAG SYSTEM ARCHITECTURE                  │
└─────────────────────────────────────────────────────────────────────────────┘

                                ┌─────────────┐
                                │    User     │
                                │   (CLI/API) │
                                └──────┬──────┘
                                       │
                                       │ HTTPS POST
                                       │ {subject_id, question}
                                       │
                                       ▼
                          ┌────────────────────────┐
                          │   AWS API Gateway      │
                          │   /prod/query          │
                          └────────────┬───────────┘
                                       │
                                       │ Invoke Lambda
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        AWS Lambda Function                              │
│                     (healthcare-rag-assistant)                          │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Step 1: Query Patient Data                                     │    │
│  └────────────────────┬────────────────────────────────────────────┘    │
│                       │                                                 │
│                       ▼                                                 │
│            ┌──────────────────────┐                                     │
│            │   RDS PostgreSQL     │◄──── psycopg2 Layer                 │
│            │   (MIMIC-IV Data)    │                                     │
│            │   • Patients         │                                     │
│            │   • Admissions       │                                     │
│            │   • Diagnoses        │                                     │
│            │   • Medications      │                                     │
│            │   • Lab Results      │                                     │
│            └──────────┬───────────┘                                     │
│                       │                                                 │
│                       │ Returns patient context                         │
│                       ▼                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Step 2: Route Query (Hybrid Approach)                          │    │
│  │  • Patient-specific? → Direct Query                             │    │
│  │  • General medical? → Knowledge Base Query                      │    │
│  └────────────┬────────────────────────────────────────────────────┘    │
│               │                                                         │
│      ┌────────┴────────┐                                                │
│      │                 │                                                │
│      ▼                 ▼                                                │
│  ┌─────────────┐   ┌──────────────────────┐                             │
│  │  Path A:    │   │  Path B:             │                             │
│  │  Direct     │   │  Knowledge Base      │                             │
│  │  Query      │   │  Query               │                             │
│  └──────┬──────┘   └──────────┬───────────┘                             │
│         │                     │                                         │
│         │                     ▼                                         │
│         │          ┌──────────────────────┐                             │
│         │          │  Bedrock KB          │                             │
│         │          │  Retrieve Documents  │                             │
│         │          │  (S3 Medical Docs)   │                             │
│         │          └──────────┬───────────┘                             │
│         │                     │                                         │
│         │                     │ Retrieved context                       │
│         │                     │                                         │
│         └─────────────────────┴──────────┐                              │
│                                          │                              │
│                                          ▼                              │
│                              ┌──────────────────────────┐               │
│                              │   AWS Bedrock            │               │
│                              │   DeepSeek R1 Model      │               │
│                              │   (LLM Inference)        │               │
│                              └────────────┬─────────────┘               │
│                                           │                             │
│                                           │ Generated answer            │
│                                           │ + citations                 │
│                                           │                             │
│  ┌────────────────────────────────────────┴────────────────────────┐    │
│  │  Step 3: Format Response                                        │    │
│  │  • Save to database (kb_queries, kb_citations)                  │    │
│  │  • Update conversation history                                  │    │
│  │  • Return JSON response                                         │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    │ HTTP 200 OK
                                    │ {answer, metadata, citations}
                                    │
                                    ▼
                          ┌────────────────────┐
                          │   API Response     │
                          │   to User          │
                          └────────────────────┘
```

## Features

- **Clinical Q&A:** Answer questions about patients using their electronic health records.
- **Knowledge Base Integration:** Augments responses with information from a corpus of medical documents.
- **Conversational Context:** Maintains conversation history for follow-up questions.
- **Citations:** Provides citations from the knowledge base to support its answers.
- **Serverless:** Built with AWS Lambda for scalability and cost-effectiveness.
- **MIMIC-IV Demo:** Includes scripts and schema for using the MIMIC-IV clinical dataset.

## Prerequisites

- [AWS CLI](https://aws.amazon.com/cli/) configured with appropriate credentials.
- [Docker](https://www.docker.com/)
- [Python 3.10+](https://www.python.org/downloads/)
- [Conda](https://docs.conda.io/en/latest/miniconda.html) (optional, for local development)
- A PostgreSQL database.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/bedrock-healthcare-rag.git
    cd bedrock-healthcare-rag
    ```

2.  **Set up the PostgreSQL Database:**
    -   Connect to your PostgreSQL database.
    -   Run the `psql/schema.sql` script to create the tables:
        ```bash
        psql -h your-db-host -U your-user -d your-db-name -f psql/schema.sql
        ```
    -   Download the MIMIC-IV CSV files and place them in a directory.
    -   Update the `DATA_DIR` variable in `psql/load_data.py` to point to the directory containing the CSVs.
    -   Run the `psql/load_data.py` script to load the data:
        ```bash
        python psql/load_data.py
        ```

3.  **Configure Environment Variables:**
    Create a `.env` file in the root of the project and add the following, replacing the values with your own:
    ```
    # For psql/load_data.py and pyth/fullquery.py
    DB_HOST=your-db-host
    DB_NAME=your-db-name
    DB_USER=your-user
    DB_PASSWORD=your-password

    # For lambda function and pyth/cloudquery.py
    API_ENDPOINT=your-api-gateway-endpoint
    KNOWLEDGE_BASE_ID=your-bedrock-knowledge-base-id
    MODEL_ID=anthropic.claude-v2
    ```

4.  **Set up the S3 Bucket:**
    -   Create an S3 bucket to store the knowledge base documents.
    -   Upload the markdown files from the `s3 bucket files` directory to the bucket.
    -   Create a Bedrock Knowledge Base and connect it to your S3 bucket. Note the `KNOWLEDGE_BASE_ID`.

5.  **Build and Deploy the Lambda Function:**
    -   Run the `build-lambda.sh` script in the `lambda-package` directory:
        ```bash
        cd lambda-package
        bash build-lambda.sh
        ```
    -   This will create a `healthcare-rag-lambda.zip` file.
    -   Create a new Lambda function in the AWS console:
        -   Author from scratch.
        -   Runtime: Python 3.12.
        -   Architecture: x86_64.
        -   Upload the `healthcare-rag-lambda.zip` file.
        -   Increase the timeout to 2 minutes.
        -   In the Lambda configuration, set the environment variables from your `.env` file.
        -   Attach the necessary IAM roles to the Lambda function to allow access to Bedrock, S3, and your PostgreSQL database.

6.  **Configure API Gateway:**
    -   Create a new REST API in API Gateway.
    -   Create a new resource and a POST method.
    -   Configure the POST method to integrate with your Lambda function.
    -   Deploy the API and note the endpoint URL. Update the `API_ENDPOINT` in your `.env` file.

## Usage

### Cloud API (Recommended)

The `pyth/cloudquery.py` script provides a command-line interface for interacting with the deployed API.

**Interactive Mode:**

```bash
python pyth/cloudquery.py
```
This will start an interactive session where you can ask questions about a patient. To get a patient number, refer to the `demo_subject_id.csv` file.

**Direct Query:**

```bash
python pyth/cloudquery.py --subject-id 10000032 --question "What are my diagnoses?"
```

### Lambda CLI

The `lambda-package/lambda_cli.py` script can be used to invoke the Lambda function directly from the command line, bypassing the API Gateway. This is useful for testing.

```bash
python lambda-package/lambda_cli.py --subject-id 10000032 --question "What are my diagnoses?"
```

## Development

For local development and testing, you can set up a Conda environment.

1.  **Create the Conda environment:**
    ```bash
    conda env create -f lambda-package/environment.yml
    ```
2.  **Activate the environment:**
    ```bash
    conda activate bedrock-rag
    ```
3.  **Run the `fullquery.py` script:**
    The `pyth/fullquery.py` script is designed for local testing. It queries the local database and the Bedrock API directly. You will need to have your AWS credentials configured.

    ```bash
    python pyth/fullquery.py
    ```

## Data

-   **Clinical Data:** The project is designed to work with the [MIMIC-IV Clinical Database](https://physionet.org/content/mimiciv/latest/). I used the free version on Kaggle to demonstrate my capabilities.
-   **Knowledge Base:** The `s3 bucket files` directory contains a set of sample medical documents that can be used as a knowledge base. These documents are derived from various sources and are for demonstration purposes only.
