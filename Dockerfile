FROM python:3.11-slim

# Configurar timezone para Brasília
ENV TZ=America/Sao_Paulo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Instalar dependências do sistema (se necessário)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Criar diretório de trabalho
WORKDIR /app

# Copiar arquivos de dependências
COPY requirements.txt .

# Criar e ativar ambiente virtual
RUN python3 -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Instalar dependências Python no venv
RUN /app/venv/bin/pip install --upgrade pip && \
    /app/venv/bin/pip install --no-cache-dir -r requirements.txt

# Copiar código da aplicação
COPY . .

# Criar diretórios de dados e logs
RUN mkdir -p /app/data /app/logs

# Variáveis de ambiente padrão
ENV DATA_DIR=/app/data
ENV NEXTFIT_API_KEY=N5dTS6i7mSu9pQ4PUeN_zuvIDiT4qmGv

# Comando padrão: executar o scheduler usando o Python do venv
CMD ["/app/venv/bin/python", "main.py"]
