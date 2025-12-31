#!/bin/bash
set -e

echo "🏗️  Building Lambda deployment package for Linux (Python 3.12)..."

# Clean up old deployment
rm -rf lambda-deployment
mkdir lambda-deployment

echo "📦 Installing ALL dependencies in Docker (Linux environment)..."
# Use --entrypoint to override the default Lambda entrypoint
docker run --rm \
  --entrypoint /bin/bash \
  -v "$PWD/lambda-deployment:/packages" \
  -v "$PWD:/src" \
  public.ecr.aws/lambda/python:3.12 \
  -c "
    echo '📥 Installing dependencies from requirements.txt...' && \
    pip install \
      boto3 \
      botocore \
      python-dotenv \
      -t /packages && \
    echo '✅ All dependencies installed' && \
    echo '' && \
    echo '📄 Copying source files...' && \
    cp /src/healthcare_assistant.py /packages/ && \
    echo '✅ Copied healthcare_assistant.py' && \
    cp /src/lambda_handler.py /packages/ && \
    echo '✅ Copied lambda_handler.py' && \
    echo '' && \
    echo '📂 Package contents:' && \
    ls -la /packages/ | head -20
  "

echo ""
echo "📦 Creating deployment ZIP..."
cd lambda-deployment
zip -r ../healthcare-rag-lambda.zip . > /dev/null
cd ..

echo ""
echo "✅ Deployment package created successfully!"
echo "📊 Package size:"
ls -lh healthcare-rag-lambda.zip
echo ""
echo "📁 Detailed package contents:"
unzip -l healthcare-rag-lambda.zip | head -25
echo ""
echo "📤 Next step: Upload healthcare-rag-lambda.zip to AWS Lambda"
