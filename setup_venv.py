"""
Módulo para garantir que a aplicação rode em um ambiente virtual
Cria o venv automaticamente se não existir e instala dependências
"""
import os
import sys
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def is_venv():
    """Verifica se está rodando em um ambiente virtual"""
    return (hasattr(sys, 'real_prefix') or 
            (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))


def create_venv(venv_path):
    """Cria um ambiente virtual"""
    logger.info(f"Criando ambiente virtual em {venv_path}...")
    try:
        subprocess.check_call([sys.executable, '-m', 'venv', str(venv_path)])
        logger.info("✓ Ambiente virtual criado com sucesso")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Erro ao criar ambiente virtual: {e}")
        return False


def install_requirements(venv_python):
    """Instala dependências do requirements.txt no venv"""
    requirements_file = Path(__file__).parent / 'requirements.txt'
    
    if not requirements_file.exists():
        logger.warning("Arquivo requirements.txt não encontrado")
        return False
    
    logger.info("Instalando dependências do requirements.txt...")
    try:
        # Atualizar pip primeiro
        subprocess.check_call([str(venv_python), '-m', 'pip', 'install', '--upgrade', 'pip'], 
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Instalar dependências
        subprocess.check_call([str(venv_python), '-m', 'pip', 'install', '-r', str(requirements_file)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info("✓ Dependências instaladas com sucesso")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Erro ao instalar dependências: {e}")
        return False


def ensure_venv():
    """
    Garante que a aplicação está rodando em um venv.
    Se não estiver, cria o venv e reinicia a aplicação nele.
    Funciona tanto localmente quanto no Docker/Docker Swarm.
    """
    # Se já está em um venv, não fazer nada
    if is_venv():
        logger.debug("Aplicação já está rodando em um ambiente virtual")
        return True
    
    # Caminho do venv (na raiz do projeto)
    project_root = Path(__file__).parent
    venv_path = project_root / 'venv'
    
    # Determinar caminho do Python do venv
    if sys.platform == 'win32':
        venv_python = venv_path / 'Scripts' / 'python.exe'
    else:
        venv_python = venv_path / 'bin' / 'python'
    
    # Se venv não existe, criar
    if not venv_path.exists():
        logger.info("=" * 60)
        logger.info("AMBIENTE VIRTUAL NÃO ENCONTRADO")
        logger.info("=" * 60)
        logger.info("Criando ambiente virtual e instalando dependências...")
        logger.info("Isso pode levar alguns minutos na primeira execução.")
        logger.info("")
        
        if not create_venv(venv_path):
            logger.error("Falha ao criar ambiente virtual")
            return False
        
        if not install_requirements(venv_python):
            logger.error("Falha ao instalar dependências")
            return False
        
        logger.info("")
        logger.info("✓ Ambiente virtual configurado com sucesso!")
        logger.info("=" * 60)
        logger.info("")
    
    # Reiniciar aplicação usando o Python do venv
    if sys.platform == 'win32':
        venv_python = venv_path / 'Scripts' / 'python.exe'
    else:
        venv_python = venv_path / 'bin' / 'python'
    
    if not venv_python.exists():
        logger.error(f"Python do venv não encontrado em {venv_python}")
        logger.error("Por favor, execute manualmente:")
        if sys.platform == 'win32':
            logger.error(f"  {venv_python} main.py")
        else:
            logger.error(f"  {venv_python} main.py")
        return False
    
    logger.info("Reiniciando aplicação com Python do ambiente virtual...")
    logger.info("")
    
    # Reiniciar com o Python do venv
    try:
        os.execv(str(venv_python), [str(venv_python)] + sys.argv)
    except Exception as e:
        logger.error(f"Erro ao reiniciar com venv: {e}")
        logger.error("Por favor, execute manualmente:")
        if sys.platform == 'win32':
            logger.error(f"  {venv_python} main.py")
        else:
            logger.error(f"  {venv_python} main.py")
        return False
    
    # Não deve chegar aqui, mas por segurança:
    return False


if __name__ == "__main__":
    # Teste do módulo
    logging.basicConfig(level=logging.INFO)
    ensure_venv()
