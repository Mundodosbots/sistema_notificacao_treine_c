"""
Script para verificar contas a receber e identificar aniversariantes
Executa todo dia às 9h da manhã
Busca contas em múltiplos períodos e envia mensagens
"""
import os
import sys
import json
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dateutil import parser as date_parser

# Adicionar o diretório raiz ao path para importar config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import config.config as config
from scripts import send_messages

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_session_with_retry():
    """Cria uma sessão requests com retry automático"""
    session = requests.Session()
    retry_strategy = Retry(
        total=config.MAX_RETRIES,
        backoff_factor=config.RETRY_DELAY,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def load_users():
    """Carrega os usuários do arquivo JSON"""
    users_file = Path(config.USERS_JSON_PATH)
    
    if not users_file.exists():
        logger.error(f"Arquivo {config.USERS_JSON_PATH} não encontrado!")
        return []
    
    try:
        with open(users_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            users = data.get("users", [])
            logger.info(f"Carregados {len(users)} usuários do arquivo")
            return users
    except Exception as e:
        logger.error(f"Erro ao carregar usuários: {e}", exc_info=True)
        return []


def fetch_accounts_receber(session, data_inicio: str, data_fim: str) -> List[Dict]:
    """Busca contas a receber para um período"""
    url = f"{config.BASE_URL}{config.ENDPOINT_CONTAS_RECEBER}"
    params = {
        "DataVencimentoInicio": data_inicio,
        "DataVencimentoFim": data_fim,
        "Take": config.ITEMS_PER_PAGE,
        "version": config.API_VERSION
    }
    
    all_accounts = []
    skip = 0
    
    try:
        while True:
            params["Skip"] = skip
            logger.debug(f"Buscando contas: Skip={skip}, DataInicio={data_inicio}, DataFim={data_fim}")
            
            response = session.get(url, headers=config.API_HEADERS, params=params, timeout=30)
            response.raise_for_status()
            accounts_data = response.json()
            
            # Processar resposta
            if isinstance(accounts_data, list):
                accounts_list = accounts_data
            elif isinstance(accounts_data, dict):
                accounts_list = accounts_data.get("data") or accounts_data.get("items") or accounts_data.get("contas") or []
                if not accounts_list and isinstance(accounts_data, dict):
                    accounts_list = [accounts_data]
            else:
                logger.warning(f"Formato de resposta inesperado: {type(accounts_data)}")
                break
            
            if not accounts_list or len(accounts_list) == 0:
                break
            
            all_accounts.extend(accounts_list)
            
            if len(accounts_list) < config.ITEMS_PER_PAGE:
                break
            
            skip += config.ITEMS_PER_PAGE
        
        return all_accounts
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao buscar contas a receber: {e}", exc_info=True)
        raise


def get_accounts_with_user_info(accounts: List[Dict], users: List[Dict]) -> List[Dict]:
    """Associa contas a receber com informações dos usuários"""
    users_dict = {str(user.get("id")): user for user in users}
    
    accounts_with_users = []
    
    for account in accounts:
        cliente_id = (
            account.get("CodigoCliente") or 
            account.get("codigoCliente") or 
            account.get("ClienteId") or 
            account.get("clienteId") or
            account.get("IdCliente") or
            account.get("idCliente")
        )
        
        user_info = None
        if cliente_id:
            user_info = users_dict.get(str(cliente_id))
        
        accounts_with_users.append({
            "conta": account,
            "cliente_id": cliente_id,
            "user_info": user_info
        })
    
    return accounts_with_users


def find_birthday_users(users: List[Dict], target_date: date = None) -> List[Dict]:
    """Identifica usuários que fazem aniversário na data especificada"""
    if target_date is None:
        target_date = date.today()
    
    birthday_users = []
    
    for user in users:
        data_nascimento_str = user.get("data_nascimento") or user.get("DataNascimento") or ""
        
        if not data_nascimento_str:
            continue
        
        try:
            data_nascimento = date_parser.parse(data_nascimento_str).date()
            if data_nascimento.month == target_date.month and data_nascimento.day == target_date.day:
                birthday_users.append(user)
        except (ValueError, TypeError):
            continue
    
    return birthday_users


def get_date_range_strings(target_date: date) -> Dict[str, tuple]:
    """Retorna strings de data para diferentes períodos"""
    hoje = target_date
    
    return {
        "vencendo_hoje": (
            f"{hoje}T00:00:00",
            f"{hoje}T23:59:59"
        ),
        "vencendo_3_dias": (
            f"{(hoje + timedelta(days=3))}T00:00:00",
            f"{(hoje + timedelta(days=3))}T23:59:59"
        ),
        "vencido_3_dias": (
            f"{(hoje - timedelta(days=3))}T00:00:00",
            f"{(hoje - timedelta(days=3))}T23:59:59"
        ),
        "vencido_5_dias": (
            f"{(hoje - timedelta(days=5))}T00:00:00",
            f"{(hoje - timedelta(days=5))}T23:59:59"
        ),
        "vencido_30_dias": (
            f"{(hoje - timedelta(days=30))}T00:00:00",
            f"{(hoje - timedelta(days=30))}T23:59:59"
        ),
    }


def prepare_message_data(user: Dict, conta_data: Dict = None, message_type: str = "aniversariante") -> Dict:
    """Prepara dados para envio de mensagem"""
    phone = user.get("telefone") or user.get("Telefone") or ""
    first_name = user.get("nome") or user.get("Nome") or ""
    
    if not phone:
        return None
    
    # Limpar telefone (remover caracteres não numéricos, exceto +)
    phone = ''.join(c for c in phone if c.isdigit() or c == '+')
    
    # Construir field_mappings
    field_mappings = {}
    
    # Adicionar campos customizados se configurados
    if config.MESSAGE_CUSTOM_FIELDS.get("campo1"):
        field_mappings[config.MESSAGE_CUSTOM_FIELDS["campo1"]] = first_name
    
    if conta_data:
        valor = conta_data.get("valor") or conta_data.get("Valor") or ""
        vencimento = conta_data.get("vencimento") or conta_data.get("DataVencimento") or conta_data.get("dataVencimento") or ""
        plano = conta_data.get("descricao") or conta_data.get("Descricao") or ""  # Nome do plano
        
        # Extrair apenas a data (sem hora) do vencimento
        data_vencimento_apenas = ""
        if vencimento:
            try:
                # Se for string ISO (ex: "2026-02-24T07:09:43"), pegar apenas a parte da data
                if "T" in str(vencimento):
                    data_vencimento_apenas = str(vencimento).split("T")[0]
                elif " " in str(vencimento):
                    data_vencimento_apenas = str(vencimento).split(" ")[0]
                else:
                    # Se já for só data, usar como está
                    data_vencimento_apenas = str(vencimento)[:10]  # Primeiros 10 caracteres (YYYY-MM-DD)
            except Exception:
                data_vencimento_apenas = ""
        
        if config.MESSAGE_CUSTOM_FIELDS.get("campo2"):
            field_mappings[config.MESSAGE_CUSTOM_FIELDS["campo2"]] = valor
        
        if config.MESSAGE_CUSTOM_FIELDS.get("campo3"):
            field_mappings[config.MESSAGE_CUSTOM_FIELDS["campo3"]] = vencimento
        
        # Adicionar plano se campo4 estiver configurado
        if config.MESSAGE_CUSTOM_FIELDS.get("campo4") and plano:
            field_mappings[config.MESSAGE_CUSTOM_FIELDS["campo4"]] = plano
        
        # Adicionar data de vencimento (apenas data, sem hora) se campo5 estiver configurado
        if config.MESSAGE_CUSTOM_FIELDS.get("campo5") and data_vencimento_apenas:
            field_mappings[config.MESSAGE_CUSTOM_FIELDS["campo5"]] = data_vencimento_apenas
    
    # Obter flow_id baseado no tipo
    flow_id = config.FLOW_IDS.get(message_type, 0)
    
    if flow_id == 0:
        logger.warning(f"Flow ID não configurado para {message_type}")
        return None
    
    return {
        "phone": phone,
        "first_name": first_name,
        "field_mappings": field_mappings,
        "flow_id": flow_id
    }


def check_accounts_and_birthdays():
    """Função principal: verifica contas a receber e aniversariantes em múltiplos períodos"""
    logger.info("Iniciando verificação de contas a receber e aniversariantes")
    
    # Carregar usuários
    users = load_users()
    if not users:
        logger.warning("Nenhum usuário carregado. Verificação pode estar incompleta.")
        return None
    
    hoje = datetime.now().date()
    session = create_session_with_retry()
    
    # Obter ranges de datas
    date_ranges = get_date_range_strings(hoje)
    
    result = {
        "date": hoje.isoformat(),
        "timestamp": datetime.now().isoformat(),
        "accounts": {},
        "birthdays": {
            "total": 0,
            "users": []
        },
        "messages_sent": {
            "boleto_vencendo_hoje": 0,
            "boleto_vencendo_3_dias": 0,
            "boleto_vencido_3_dias": 0,
            "boleto_vencido_5_dias": 0,
            "boleto_vencido_30_dias": 0,
            "aniversariante": 0,
        }
    }
    
    messages_to_send = []
    
    try:
        # Buscar contas para cada período
        for period_name, (data_inicio, data_fim) in date_ranges.items():
            logger.info(f"Buscando contas: {period_name} ({data_inicio} a {data_fim})")
            accounts = fetch_accounts_receber(session, data_inicio, data_fim)
            logger.info(f"Encontradas {len(accounts)} contas para {period_name}")
            
            accounts_with_users = get_accounts_with_user_info(accounts, users)
            accounts_with_valid_users = [
                acc for acc in accounts_with_users 
                if acc["user_info"] is not None
            ]
            
            result["accounts"][period_name] = {
                "total": len(accounts),
                "with_user_info": len(accounts_with_valid_users),
                "accounts": []
            }
            
            # Preparar mensagens para este período
            message_type_map = {
                "vencendo_hoje": "boleto_vencendo_hoje",
                "vencendo_3_dias": "boleto_vencendo_3_dias",
                "vencido_3_dias": "boleto_vencido_3_dias",
                "vencido_5_dias": "boleto_vencido_5_dias",
                "vencido_30_dias": "boleto_vencido_30_dias",
            }
            
            message_type = message_type_map.get(period_name)
            
            for acc in accounts_with_valid_users:
                conta_status = acc["conta"].get("Status") or acc["conta"].get("status") or ""
                
                conta_data = {
                    "valor": acc["conta"].get("Valor") or acc["conta"].get("valor"),
                    "vencimento": acc["conta"].get("DataVencimento") or acc["conta"].get("dataVencimento"),
                    "status": conta_status,
                    "descricao": acc["conta"].get("descricao") or acc["conta"].get("Descricao") or "",  # Plano do aluno
                    "codigoOrigem": None
                }
                
                # Extrair código do contrato/plano se disponível
                receber_origem = acc["conta"].get("receberOrigem") or []
                if receber_origem and isinstance(receber_origem, list) and len(receber_origem) > 0:
                    origem = receber_origem[0]
                    conta_data["codigoOrigem"] = origem.get("codigoOrigem")
                    conta_data["origem"] = origem.get("origem")  # Ex: "Contrato", "Item", etc.
                
                # Sempre adicionar à lista de contas (para histórico)
                result["accounts"][period_name]["accounts"].append({
                    "cliente_id": acc["cliente_id"],
                    "user": acc["user_info"],
                    "conta_data": conta_data
                })
                
                # Filtrar por status: apenas enviar mensagem para status válidos
                if conta_status in config.VALID_ACCOUNT_STATUSES:
                    # Preparar mensagem apenas para contas com status válido
                    msg_data = prepare_message_data(acc["user_info"], conta_data, message_type)
                    if msg_data:
                        messages_to_send.append(msg_data)
                else:
                    logger.debug(f"Conta do cliente {acc['cliente_id']} com status '{conta_status}' ignorada (não está em VALID_ACCOUNT_STATUSES)")
        
        # Identificar aniversariantes
        logger.info(f"Identificando aniversariantes para {hoje}")
        birthday_users = find_birthday_users(users, hoje)
        logger.info(f"Encontrados {len(birthday_users)} aniversariantes hoje")
        
        result["birthdays"]["total"] = len(birthday_users)
        result["birthdays"]["users"] = birthday_users
        
        # Preparar mensagens para aniversariantes
        for user in birthday_users:
            msg_data = prepare_message_data(user, None, "aniversariante")
            if msg_data:
                messages_to_send.append(msg_data)
        
        # Enviar mensagens (se habilitado)
        if messages_to_send:
            if config.SEND_MESSAGES:
                logger.info(f"Enviando {len(messages_to_send)} mensagens...")
                stats = send_messages.send_batch_messages(messages_to_send)
                
                # Atualizar contadores
                for msg in messages_to_send:
                    # Identificar tipo pela flow_id
                    for msg_type, flow_id in config.FLOW_IDS.items():
                        if msg.get("flow_id") == flow_id and flow_id > 0:
                            if stats['sent'] > 0:  # Simplificado - contar todas como enviadas se stats positivo
                                result["messages_sent"][msg_type] += 1
            else:
                logger.info(f"[MODO TESTE] {len(messages_to_send)} mensagens preparadas mas NÃO enviadas (SEND_MESSAGES=false)")
                logger.info(f"[MODO TESTE] Mensagens preparadas por tipo:")
                for msg in messages_to_send:
                    for msg_type, flow_id in config.FLOW_IDS.items():
                        if msg.get("flow_id") == flow_id and flow_id > 0:
                            result["messages_sent"][msg_type] += 1
                            break
        else:
            logger.info("Nenhuma mensagem para enviar")
        
        # Salvar resultados
        data_dir = Path(config.DATA_DIR)
        data_dir.mkdir(parents=True, exist_ok=True)
        
        with open(config.ACCOUNTS_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Verificação concluída! Resultados salvos em {config.ACCOUNTS_JSON_PATH}")
        
        # Resumo
        total_accounts = sum(r["with_user_info"] for r in result["accounts"].values())
        logger.info(f"Resumo: {total_accounts} contas encontradas, {len(birthday_users)} aniversariantes")
        logger.info(f"Mensagens enviadas: {sum(result['messages_sent'].values())}")
        
        return result
        
    except Exception as e:
        logger.error(f"Erro durante a verificação: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        result = check_accounts_and_birthdays()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Falha na execução: {e}", exc_info=True)
        sys.exit(1)
