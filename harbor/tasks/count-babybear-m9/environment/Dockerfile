# Shared by every count task (agent and separate verifier). Python only.
FROM python:3.12-slim
RUN pip install --no-cache-dir numpy==2.3.3
COPY certify.py baseline.py pack_instance.py /opt/proven/
RUN chmod 0755 /opt/proven/*.py && mkdir -p /workspace
WORKDIR /workspace
