The following dependency changes will be required on Machine S:

```/tools/mork/pyproject.toml
  "langchain-litellm>=0.1,<0.11",
  "litellm>=1.83.14,<1.103.2",
  "langsmith<0.14.2",
  "python-dotenv<1.2.4",
  "boto3<1.43.106",
  "botocore<1.43.106",
  "langgraph>=0.2",
  ```