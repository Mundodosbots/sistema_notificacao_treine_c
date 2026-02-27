# Sistema de Automação NextFit API

Sistema automatizado para coletar dados de usuários e verificar contas a receber da API NextFit, com envio automático de mensagens via API mundodosbots.

## Funcionalidades

- **Coleta Semanal de Usuários**: Coleta todos os usuários da API NextFit e salva em JSON
  - Executa uma vez ao iniciar o container
  - Depois, todo domingo às 2h da manhã (atualização semanal)
- **Verificação Diária de Contas**: Todo dia às 9h da manhã
  - Busca contas vencendo hoje
  - Busca contas vencendo em 3 dias
  - Busca contas vencidas há 3 dias
  - Busca contas vencidas há 5 dias
  - Busca contas vencidas há 30 dias
  - Identifica aniversariantes do dia
  - Envia mensagens automaticamente via API mundodosbots

## Estrutura do Projeto

```
.
├── scripts/
│   ├── collect_users.py      # Script de coleta semanal de usuários
│   ├── check_accounts.py     # Script de verificação diária (múltiplos períodos)
│   └── send_messages.py      # Módulo de envio de mensagens
├── config/
│   └── config.py             # Configurações da aplicação
├── data/                      # Volume persistente (criado automaticamente)
│   ├── users.json            # Arquivo com todos os usuários coletados
│   └── accounts_today.json   # Arquivo com contas e aniversariantes do dia
├── logs/                      # Logs do sistema
├── main.py                    # Script principal com scheduler
├── Dockerfile
├── docker-compose.yml
├── .env                       # Variáveis de ambiente (não versionado)
├── requirements.txt
└── README.md
```

## Requisitos

- Docker e Docker Compose
- Python 3.11+ (para desenvolvimento local)

## Configuração

### 1. Criar arquivo `.env`

Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```env
# API NextFit
NEXTFIT_API_KEY=sua_chave_api_nextfit

# API de Mensagens (mundodosbots)
MESSAGE_API_TOKEN=seu_token_mundodosbots

# Flow IDs para cada tipo de mensagem
FLOW_ID_VENCENDO_HOJE=12345
FLOW_ID_VENCENDO_3_DIAS=12346
FLOW_ID_VENCIDO_3_DIAS=12347
FLOW_ID_VENCIDO_5_DIAS=12348
FLOW_ID_VENCIDO_30_DIAS=12349
FLOW_ID_ANIVERSARIANTE=12350

# Campos customizados na API de mensagens
# Estes são os nomes dos campos que você criou na plataforma mundodosbots
MESSAGE_FIELD_1=first_name
MESSAGE_FIELD_2=valor_boleto
MESSAGE_FIELD_3=data_vencimento
MESSAGE_FIELD_4=nome_plano
MESSAGE_FIELD_5=data_vencimento_dia
```

### 2. Configurar Campos na API mundodosbots

Na plataforma mundodosbots, você precisa criar os seguintes campos customizados:

| Nome do Campo | Tipo | Descrição |
|---------------|------|-----------|
| `first_name` | Texto | Nome do cliente |
| `valor_boleto` | Número/Texto | Valor do boleto |
| `data_vencimento` | Data/Texto | Data e hora de vencimento completa |
| `nome_plano` | Texto | Nome do plano do aluno |
| `data_vencimento_dia` | Data/Texto | Apenas a data de vencimento (sem hora) |

**Importante**: Os nomes dos campos devem ser exatamente iguais aos configurados no `.env`.

## Uso

### Com Docker Compose (Recomendado)

1. Configure o arquivo `.env` com suas credenciais
2. Execute:

```bash
docker-compose up -d
```

3. Verificar logs:

```bash
docker-compose logs -f
```

4. Parar o container:

```bash
docker-compose down
```

### Desenvolvimento Local

O sistema **cria automaticamente** um ambiente virtual (venv) na primeira execução e instala todas as dependências.

1. Configure o arquivo `.env`

2. Execute a aplicação:

```bash
python main.py
```

**O que acontece automaticamente:**
- O sistema verifica se está rodando em um venv
- Se não estiver, cria o venv automaticamente na pasta `venv/`
- Instala todas as dependências do `requirements.txt`
- Reinicia a aplicação usando o Python do venv

**Nota:** Na primeira execução, pode levar alguns minutos para criar o venv e instalar as dependências. Nas próximas execuções, será instantâneo.

**Execução manual com venv (opcional):**

Se preferir ativar o venv manualmente:

```bash
# Linux/Mac
source venv/bin/activate
python main.py

# Windows
venv\Scripts\activate.bat
python main.py
```

## Agendamento

O sistema usa APScheduler para executar jobs automaticamente:

- **Coleta de Usuários**: 
  - Executa **uma vez ao iniciar o container** (não espera domingo)
  - Depois, todo domingo às 2:00 (horário de Brasília)
- **Verificação de Contas**: Todo dia às 9:00 (horário de Brasília)
  - Busca contas em múltiplos períodos
  - Identifica aniversariantes
  - Envia mensagens automaticamente

## Dados Coletados

### Usuários (users.json)

Arquivo gerado toda semana com todos os usuários:

```json
{
  "last_updated": "2026-02-20T01:00:00",
  "total_users": 8074,
  "users": [
    {
      "id": 123,
      "nome": "João Silva",
      "telefone": "11999999999",
      "data_nascimento": "1990-05-15T00:00:00"
    }
  ]
}
```

**Campos coletados:**
- `id`: ID do cliente na NextFit
- `nome`: Nome completo
- `telefone`: Telefone (DDD + número combinados)
- `data_nascimento`: Data de nascimento

### Contas (accounts_today.json)

Arquivo gerado diariamente com contas a receber e aniversariantes:

```json
{
  "date": "2026-02-20",
  "timestamp": "2026-02-20T08:00:00",
  "accounts": {
    "vencendo_hoje": {
      "total": 56,
      "with_user_info": 56,
      "accounts": [
        {
          "cliente_id": 123,
          "user": {
            "id": 123,
            "nome": "João Silva",
            "telefone": "11999999999",
            "data_nascimento": "1990-05-15T00:00:00"
          },
          "conta_data": {
            "valor": 139.90,
            "vencimento": "2026-02-20T00:00:00",
            "status": "Recebido",
            "descricao": "Nome do Plano do Aluno",
            "codigoOrigem": 457543,
            "origem": "Contrato"
          }
        }
      ]
    },
    "vencendo_3_dias": { ... },
    "vencido_3_dias": { ... },
    "vencido_5_dias": { ... },
    "vencido_30_dias": { ... }
  },
  "birthdays": {
    "total": 28,
    "users": [ ... ]
  },
  "messages_sent": {
    "boleto_vencendo_hoje": 10,
    "boleto_vencendo_3_dias": 5,
    ...
  }
}
```

**Campos coletados das contas:**
- `valor`: Valor do boleto
- `vencimento`: Data de vencimento
- `status`: Status da conta
- `descricao`: Nome do plano do aluno
- `codigoOrigem`: Código do contrato/plano
- `origem`: Tipo de origem (ex: "Contrato", "Item")

## Envio de Mensagens

### Estrutura da Mensagem

O sistema envia mensagens via API mundodosbots com a seguinte estrutura:

```json
{
  "phone": "5511999999999",
  "first_name": "João Silva",
  "actions": [
    {
      "action": "set_field_value",
      "field_name": "first_name",
      "value": "João Silva"
    },
    {
      "action": "set_field_value",
      "field_name": "valor_boleto",
      "value": "139.90"
    },
    {
      "action": "set_field_value",
      "field_name": "data_vencimento",
      "value": "2026-02-24T00:00:00"
    },
    {
      "action": "set_field_value",
      "field_name": "nome_plano",
      "value": "Nome do Plano do Aluno"
    },
    {
      "action": "send_flow",
      "flow_id": 1771882402514
    }
  ]
}
```

### Tipos de Mensagens

1. **Boletos vencendo hoje** - Flow ID: `FLOW_ID_VENCENDO_HOJE`
2. **Boletos vencendo em 3 dias** - Flow ID: `FLOW_ID_VENCENDO_3_DIAS`
3. **Boletos vencidos há 3 dias** - Flow ID: `FLOW_ID_VENCIDO_3_DIAS`
4. **Boletos vencidos há 5 dias** - Flow ID: `FLOW_ID_VENCIDO_5_DIAS`
5. **Boletos vencidos há 30 dias** - Flow ID: `FLOW_ID_VENCIDO_30_DIAS`
6. **Aniversariantes** - Flow ID: `FLOW_ID_ANIVERSARIANTE`

### Dados Enviados nas Mensagens

- **Para boletos**: Nome, telefone, valor, data de vencimento, nome do plano
- **Para aniversariantes**: Nome, telefone

## Logs

Os logs são salvos em:
- Console (stdout)
- Arquivo `logs/scheduler.log` (no container)

Para ver logs do container:

```bash
docker-compose logs -f nextfit-scheduler
```

## Volume Persistente

O diretório `./data` é montado como volume persistente no container, garantindo que os dados JSON sejam mantidos mesmo após reinicializações do container.

## Proteção da API

O sistema implementa proteções para não sobrecarregar a API NextFit:

- **Delay entre requisições**: 1 segundo entre cada requisição
- **Retry automático**: 3 tentativas com backoff exponencial
- **Paginação**: Processa 30 itens por vez

## Troubleshooting

### Container não inicia

Verifique os logs:

```bash
docker-compose logs nextfit-scheduler
```

### Erro de permissão no volume

Certifique-se de que o diretório `data` existe:

```bash
mkdir -p data
```

### API retorna erro

Verifique se:
- A API key está correta no arquivo `.env`
- O token da API de mensagens está configurado
- Os Flow IDs estão corretos

### Mensagens não são enviadas

Verifique se:
- O token da API mundodosbots está configurado
- Os Flow IDs estão corretos no `.env`
- Os campos customizados foram criados na plataforma mundodosbots
- Os nomes dos campos no `.env` correspondem aos criados na plataforma

## Estrutura de Dados da API NextFit

### Resposta da API GetClientes

A API retorna um dicionário com:
- `items`: Lista de usuários
- `temProximaPagina`: Indica se há mais páginas

Cada usuário contém:
- `id`: ID do cliente
- `nome`: Nome completo
- `dddFone`: DDD do telefone
- `fone`: Número do telefone
- `dataNascimento`: Data de nascimento

### Resposta da API ContaReceber

A API retorna um dicionário com:
- `items`: Lista de contas
- `temProximaPagina`: Indica se há mais páginas

Cada conta contém:
- `codigoCliente`: ID do cliente
- `valor`: Valor da conta
- `dataVencimento`: Data de vencimento
- `status`: Status da conta
- `descricao`: Nome do plano do aluno
- `receberOrigem`: Array com informações da origem (contrato, item, etc.)
