"""
Módulo para enviar mensagens via API mundodosbots
"""
import os
import sys
import logging
from typing import Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Adicionar o diretório raiz ao path para importar config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import config.config as config

logger = logging.getLogger(__name__)


def create_message_session():
    """Cria uma sessão requests com retry para envio de mensagens"""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def send_message(phone: str, first_name: str, field_mappings: Dict[str, str], flow_id: int) -> bool:
    """
    Envia mensagem via API mundodosbots
    
    Args:
        phone: Número de telefone
        first_name: Primeiro nome
        field_mappings: Dicionário com mapeamento campo -> valor
        flow_id: ID do fluxo a ser enviado
    
    Returns:
        True se enviado com sucesso, False caso contrário
    """
    if not config.MESSAGE_API_TOKEN:
        logger.warning("Token da API de mensagens não configurado. Pulando envio.")
        return False
    
    url = config.MESSAGE_API_URL
    headers = {
        "accept": "application/json",
        "X-ACCESS-TOKEN": config.MESSAGE_API_TOKEN,
        "Content-Type": "application/json"
    }
    
    # Construir actions
    actions = []
    
    # Adicionar set_field_value para cada campo
    for field_name, value in field_mappings.items():
        if value:  # Só adicionar se tiver valor
            actions.append({
                "action": "set_field_value",
                "field_name": field_name,
                "value": str(value)
            })
    
    # Adicionar send_flow
    actions.append({
        "action": "send_flow",
        "flow_id": flow_id
    })
    
    payload = {
        "phone": phone,
        "first_name": first_name,
        "actions": actions
    }
    
    try:
        session = create_message_session()
        response = session.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        logger.info(f"Mensagem enviada com sucesso para {phone} (flow_id: {flow_id})")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao enviar mensagem para {phone}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Resposta da API: {e.response.text}")
        return False


def send_batch_messages(messages: List[Dict]) -> Dict[str, int]:
    """
    Envia múltiplas mensagens
    
    Args:
        messages: Lista de dicionários com phone, first_name, field_mappings, flow_id
    
    Returns:
        Dicionário com estatísticas: {'sent': X, 'failed': Y, 'total': Z}
    """
    stats = {'sent': 0, 'failed': 0, 'total': len(messages)}
    
    for msg in messages:
        success = send_message(
            phone=msg.get('phone'),
            first_name=msg.get('first_name', ''),
            field_mappings=msg.get('field_mappings', {}),
            flow_id=msg.get('flow_id')
        )
        
        if success:
            stats['sent'] += 1
        else:
            stats['failed'] += 1
    
    logger.info(f"Envio em lote concluído: {stats['sent']} enviadas, {stats['failed']} falharam de {stats['total']} total")
    return stats
