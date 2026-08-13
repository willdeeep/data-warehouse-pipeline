FROM quay.io/astronomer/astro-runtime:11.8.0

# Copy requirements
COPY requirements.txt test-requirements.txt /

# Install git and system dependencies as root
USER root
RUN apt-get update && \
    apt-get install -y git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Switch back to astro user
USER astro

# Install requirements efficiently without airflow constraints (for dbt compatibility)
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /requirements.txt && \
    pip install --no-cache-dir -r /test-requirements.txt
