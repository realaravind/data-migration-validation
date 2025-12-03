# ============================================================
# Ombudsman Migration Testing Framework – Docker Build Image
# ============================================================

FROM python:3.11-slim

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    make \
    zip \
    git \
    curl \
    gnupg \
    default-libmysqlclient-dev \
    unixodbc \
    unixodbc-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Microsoft SQL Server ODBC driver (18)
RUN curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /etc/apt/trusted.gpg.d/microsoft.gpg && \
    curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && ACCEPT_EULA=Y apt-get install -y \
    msodbcsql18 mssql-tools18 && \
    echo 'export PATH="$PATH:/opt/mssql-tools18/bin"' >> ~/.bashrc && \
    rm -rf /var/lib/apt/lists/*

# Create workspace
WORKDIR /app

# Copy project code
COPY . .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -e .

# Default entrypoint (can be overridden by compose)
ENTRYPOINT ["ombudsman"]
CMD ["--help"]