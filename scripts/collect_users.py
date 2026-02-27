"""
Script para coletar todos os usuários da API NextFit
Executa todo domingo às 2h da manhã
CRÍTICO: Sempre deleta o arquivo users.json existente e cria um novo do zero
"""
import os
import sys
import json
import time
import logging
from datetime import datetime
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Adicionar o diretório raiz ao path para importar config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import config.config as config

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


def delete_existing_users_file():
    """Deleta o arquivo users.json existente"""
    users_file = Path(config.USERS_JSON_PATH)
    if users_file.exists():
        try:
            users_file.unlink()
            logger.info(f"Arquivo {config.USERS_JSON_PATH} deletado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao deletar arquivo {config.USERS_JSON_PATH}: {e}")
            raise
    else:
        logger.info(f"Arquivo {config.USERS_JSON_PATH} não existe, prosseguindo...")


def fetch_users_page(session, skip, take):
    """Busca uma página de usuários da API"""
    url = f"{config.BASE_URL}{config.ENDPOINT_CLIENTES}"
    params = {
        "Skip": skip,
        "Take": take,
        "version": config.API_VERSION
    }
    
    try:
        logger.info(f"Buscando usuários: Skip={skip}, Take={take}")
        response = session.get(url, headers=config.API_HEADERS, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro ao buscar página (Skip={skip}): {e}")
        raise


def extract_user_data(user):
    """Extrai os campos necessários de um usuário"""
    # ID
    user_id = user.get("id") or user.get("Id") or user.get("codigoCliente")
    
    # Nome
    nome = user.get("nome") or user.get("Nome") or ""
    
    # Telefone - a API retorna dddFone e fone separados
    ddd_fone = user.get("dddFone") or user.get("ddd") or ""
    fone = user.get("fone") or user.get("telefone") or user.get("Telefone") or ""
    
    # Combinar DDD + telefone
    telefone = ""
    if ddd_fone and fone:
        telefone = f"{ddd_fone}{fone}".strip()
    elif fone:
        telefone = fone.strip()
    elif ddd_fone:
        telefone = ddd_fone.strip()
    
    # Data de nascimento
    data_nascimento = user.get("dataNascimento") or user.get("DataNascimento") or user.get("data_nascimento") or ""
    
    return {
        "id": user_id,
        "nome": nome,
        "telefone": telefone,
        "data_nascimento": data_nascimento
    }


def collect_all_users():
    """Coleta todos os usuários da API NextFit com paginação"""
    logger.info("Iniciando coleta de usuários da API NextFit")
    
    # CRÍTICO: Deletar arquivo existente antes de começar
    delete_existing_users_file()
    
    # Garantir que o diretório existe
    data_dir = Path(config.DATA_DIR)
    data_dir.mkdir(parents=True, exist_ok=True)
    
    session = create_session_with_retry()
    all_users = []
    skip = 0
    total_collected = 0
    
    try:
        while True:
            # Buscar página
            users_data = fetch_users_page(session, skip, config.ITEMS_PER_PAGE)
            
            # Verificar se recebeu dados
            if not users_data:
                logger.warning(f"Nenhum dado retornado para Skip={skip}")
                break
            
            # Processar resposta da API
            # A API retorna um dicionário com chave "items" e "temProximaPagina"
            users_list = []
            tem_proxima_pagina = False
            
            if isinstance(users_data, list):
                users_list = users_data
            elif isinstance(users_data, dict):
                # A API NextFit retorna: {"items": [...], "temProximaPagina": true/false}
                users_list = users_data.get("items") or users_data.get("data") or users_data.get("usuarios") or users_data.get("clientes") or []
                tem_proxima_pagina = users_data.get("temProximaPagina", False)
                if not users_list and isinstance(users_data, dict):
                    # Se não encontrar lista, pode ser que o objeto seja o próprio usuário
                    users_list = [users_data]
            else:
                logger.warning(f"Formato de resposta inesperado: {type(users_data)}")
                break
            
            # Se não há mais usuários, parar
            if not users_list or len(users_list) == 0:
                logger.info("Não há mais usuários para coletar")
                break
            
            # Extrair dados dos usuários
            for user in users_list:
                user_data = extract_user_data(user)
                if user_data["id"]:  # Só adicionar se tiver ID
                    all_users.append(user_data)
            
            total_collected += len(users_list)
            logger.info(f"Coletados {len(users_list)} usuários nesta página. Total acumulado: {total_collected}")
            
            # Verificar se há próxima página
            # Se temProximaPagina estiver disponível, usar ele
            # Caso contrário, verificar se recebeu menos que o Take
            if isinstance(users_data, dict) and "temProximaPagina" in users_data:
                if not tem_proxima_pagina:
                    logger.info("Última página alcançada (temProximaPagina = false)")
                    break
            elif len(users_list) < config.ITEMS_PER_PAGE:
                logger.info("Última página alcançada (menos itens que Take)")
                break
            
            # Próxima página
            skip += config.ITEMS_PER_PAGE
            
            # Delay para não sobrecarregar a API
            delay = getattr(config, 'REQUEST_DELAY', 1.0)
            logger.debug(f"Aguardando {delay}s antes da próxima requisição...")
            time.sleep(delay)
        
        # Salvar todos os usuários em um novo arquivo JSON
        output_data = {
            "last_updated": datetime.now().isoformat(),
            "total_users": len(all_users),
            "users": all_users
        }
        
        # Garantir que o diretório existe
        users_file_path = Path(config.USERS_JSON_PATH)
        users_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Mostrar caminho completo onde será salvo
        full_path = users_file_path.resolve()
        logger.info(f"Salvando dados em: {full_path}")
        
        with open(config.USERS_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✓ Coleta concluída! Total de {len(all_users)} usuários salvos")
        logger.info(f"✓ Arquivo salvo em: {full_path}")
        return True
        
    except Exception as e:
        logger.error(f"Erro crítico durante a coleta: {e}", exc_info=True)
        # Tentar salvar o que foi coletado até agora (backup parcial)
        if all_users:
            backup_path = config.USERS_JSON_PATH.replace('.json', '_backup.json')
            try:
                output_data = {
                    "last_updated": datetime.now().isoformat(),
                    "total_users": len(all_users),
                    "users": all_users,
                    "error": str(e),
                    "partial": True
                }
                with open(backup_path, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=2)
                logger.warning(f"Dados parciais salvos em {backup_path}")
            except Exception as backup_error:
                logger.error(f"Erro ao salvar backup: {backup_error}")
        raise


if __name__ == "__main__":
    try:
        success = collect_all_users()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Falha na execução: {e}", exc_info=True)
        sys.exit(1)
