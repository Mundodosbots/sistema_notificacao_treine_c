"""
Configurações da aplicação NextFit API
"""
import os
from pathlib import Path

# Carregar variáveis do arquivo .env se existir
try:
    from dotenv import load_dotenv
    # Procurar .env na raiz do projeto
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    # Se python-dotenv não estiver instalado, continuar sem ele
    pass

# API Configuration
API_KEY = os.getenv("NEXTFIT_API_KEY", "N5dTS6i7mSu9pQ4PUeN_zuvIDiT4qmGv")
BASE_URL = "https://integracao.nextfit.com.br/api/v1"
API_VERSION = "1"

# Endpoints
ENDPOINT_CLIENTES = f"/Pessoa/GetClientes"
ENDPOINT_CONTAS_RECEBER = f"/ContaReceber"

# Pagination
ITEMS_PER_PAGE = 30
MAX_RETRIES = 3
RETRY_DELAY = 2  # segundos
REQUEST_DELAY = 1.0  # segundos de espera entre requisições para não sobrecarregar a API

# File paths
# Se rodando localmente (fora do Docker), usar ./data
# Se rodando no Docker, usar /app/data
if os.path.exists("/app/data"):
    DEFAULT_DATA_DIR = "/app/data"  # Docker
else:
    DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")  # Local

DATA_DIR = os.getenv("DATA_DIR", DEFAULT_DATA_DIR)
USERS_JSON_PATH = os.path.join(DATA_DIR, "users.json")
ACCOUNTS_JSON_PATH = os.path.join(DATA_DIR, "accounts_today.json")

# Headers
API_HEADERS = {
    "accept": "text/plain",
    "X-Api-Key": API_KEY
}

# API de Mensagens (mundodosbots)
MESSAGE_API_URL = os.getenv("MESSAGE_API_URL", "https://app.mundodosbots.com.br/api/contacts")
MESSAGE_API_TOKEN = os.getenv("MESSAGE_API_TOKEN", "")

# Configurações de campos e flow_ids (serão configurados depois)
# Mapeamento: qual campo da NextFit vai para qual campo da API de mensagens
MESSAGE_FIELD_MAPPINGS = {
    "nome": "first_name",  # Campo padrão
    # Adicionar outros mapeamentos conforme necessário
}

# Flow IDs para cada tipo de mensagem
FLOW_IDS = {
    "boleto_vencendo_hoje": int(os.getenv("FLOW_ID_VENCENDO_HOJE", "0")),
    "boleto_vencendo_3_dias": int(os.getenv("FLOW_ID_VENCENDO_3_DIAS", "0")),
    "boleto_vencido_3_dias": int(os.getenv("FLOW_ID_VENCIDO_3_DIAS", "0")),
    "boleto_vencido_5_dias": int(os.getenv("FLOW_ID_VENCIDO_5_DIAS", "0")),
    "boleto_vencido_30_dias": int(os.getenv("FLOW_ID_VENCIDO_30_DIAS", "0")),
    "aniversariante": int(os.getenv("FLOW_ID_ANIVERSARIANTE", "0")),
}

# Nomes dos campos customizados na API de mensagens
MESSAGE_CUSTOM_FIELDS = {
    "campo1": os.getenv("MESSAGE_FIELD_1", ""),
    "campo2": os.getenv("MESSAGE_FIELD_2", ""),
    "campo3": os.getenv("MESSAGE_FIELD_3", ""),
    "campo4": os.getenv("MESSAGE_FIELD_4", ""),
    "campo5": os.getenv("MESSAGE_FIELD_5", ""),  # Data de vencimento (apenas data, sem hora)
}

# Controle de envio de mensagens (para testes)
# Se False, o sistema coleta dados mas não envia mensagens
SEND_MESSAGES = os.getenv("SEND_MESSAGES", "true").lower() in ("true", "1", "yes")

# Status de contas que devem receber mensagens
# Apenas contas com esses status serão incluídas no envio de mensagens
VALID_ACCOUNT_STATUSES = [
    "Aberto",
    "EmAndamento"
]
# Status que NÃO devem receber mensagens: "Recebido", "Cancelado"
