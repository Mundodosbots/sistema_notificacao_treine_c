"""
Script principal que gerencia os agendamentos dos jobs
Usa APScheduler para executar:
- Coleta de usuários: Todo domingo às 1h da manhã
- Verificação de contas: Todo dia às 8h da manhã
"""
import os
import sys
import logging
import signal
from pathlib import Path

# Garantir que está rodando em venv (antes de importar outras dependências)
# Isso cria o venv automaticamente se não existir
try:
    import setup_venv
    # Configurar logging básico antes de chamar ensure_venv
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    setup_venv.ensure_venv()
except Exception as e:
    # Se falhar, continuar mesmo assim (pode estar no Docker ou venv já ativo)
    pass

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

# Adicionar scripts ao path
sys.path.insert(0, os.path.dirname(__file__))

# Importar scripts
from scripts import collect_users, check_accounts

# Garantir que diretórios existem
log_dir = os.getenv('LOG_DIR', 'logs')
Path(log_dir).mkdir(exist_ok=True)
Path('data').mkdir(exist_ok=True)

# Configurar logging
log_file = os.path.join(log_dir, 'scheduler.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file)
    ]
)
logger = logging.getLogger(__name__)

# Timezone de Brasília
TZ_BRASILIA = pytz.timezone('America/Sao_Paulo')

# Criar scheduler
scheduler = BlockingScheduler(timezone=TZ_BRASILIA)


def job_collect_users():
    """Job para coletar usuários todo domingo às 1h"""
    logger.info("=" * 60)
    logger.info("INICIANDO JOB: Coleta de usuários (Domingo 1h)")
    logger.info("=" * 60)
    try:
        collect_users.collect_all_users()
        logger.info("Job de coleta de usuários concluído com sucesso")
    except Exception as e:
        logger.error(f"Erro no job de coleta de usuários: {e}", exc_info=True)


def job_check_accounts():
    """Job para verificar contas e aniversariantes todo dia às 8h"""
    logger.info("=" * 60)
    logger.info("INICIANDO JOB: Verificação de contas e aniversariantes (8h)")
    logger.info("=" * 60)
    try:
        check_accounts.check_accounts_and_birthdays()
        logger.info("Job de verificação de contas concluído com sucesso")
    except Exception as e:
        logger.error(f"Erro no job de verificação de contas: {e}", exc_info=True)


def setup_signal_handlers():
    """Configura handlers para encerramento graceful"""
    def signal_handler(signum, frame):
        logger.info("Sinal de encerramento recebido. Parando scheduler...")
        scheduler.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main():
    """Função principal"""
    logger.info("Iniciando scheduler NextFit API")
    logger.info(f"Timezone: {TZ_BRASILIA}")
    
    # Configurar handlers de sinal
    setup_signal_handlers()
    
    # Executar coleta de usuários UMA VEZ ao iniciar (não esperar domingo)
    logger.info("=" * 60)
    logger.info("EXECUTANDO COLETA INICIAL DE USUÁRIOS")
    logger.info("=" * 60)
    try:
        collect_users.collect_all_users()
        logger.info("✓ Coleta inicial de usuários concluída com sucesso")
    except Exception as e:
        logger.error(f"✗ Erro na coleta inicial de usuários: {e}", exc_info=True)
        logger.warning("Continuando com scheduler mesmo com erro na coleta inicial...")
    
    # Agendar job de coleta de usuários: Todo domingo às 1h da manhã
    scheduler.add_job(
        job_collect_users,
        trigger=CronTrigger(day_of_week='sun', hour=1, minute=0, timezone=TZ_BRASILIA),
        id='collect_users',
        name='Coleta de usuários (Domingo 1h)',
        replace_existing=True
    )
    logger.info("Job agendado: Coleta de usuários - Todo domingo às 1:00")
    
    # Agendar job de verificação de contas: Todo dia às 8h da manhã
    scheduler.add_job(
        job_check_accounts,
        trigger=CronTrigger(hour=8, minute=0, timezone=TZ_BRASILIA),
        id='check_accounts',
        name='Verificação de contas e aniversariantes (8h)',
        replace_existing=True
    )
    logger.info("Job agendado: Verificação de contas - Todo dia às 8:00")
    
    # Listar jobs agendados
    logger.info("\nJobs agendados:")
    for job in scheduler.get_jobs():
        # APScheduler pode variar a API dependendo da versão/implementação (ex: next_run_time pode não existir)
        try:
            next_run = getattr(job, "next_run_time", None)
        except Exception:
            next_run = None

        if next_run is not None:
            logger.info(f"  - {job.name} (ID: {job.id}) - Próxima execução: {next_run}")
        else:
            logger.info(f"  - {job.name} (ID: {job.id})")
    
    logger.info("\nScheduler iniciado. Aguardando execução dos jobs...")
    logger.info("Pressione Ctrl+C para parar\n")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler encerrado pelo usuário")
        scheduler.shutdown()


if __name__ == "__main__":
    main()
