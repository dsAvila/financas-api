# MVP Painel Financeiro - Arquitetura de Software (Back-end API)

Este repositório contém o código-fonte e a documentação técnica da API REST do **Painel Financeiro**, desenvolvida como MVP para a sprint de **Arquitetura de Software** da pós-graduação da PUC-Rio. A aplicação tem como propósito solucionar a complexidade do controle consolidado de fluxo de caixa pessoal integrado à gestão patrimonial multimoeda (BRL e USD), com atualização cambial comercial em tempo real.

O projeto adota uma arquitetura orientada a serviços desacoplada: esta API em **Python/Flask** atua como o núcleo de persistência relacional, validação de regras contábeis e agregação de serviços externos, comunicando-se de forma assíncrona com o ecossistema cliente.

> 🔗 **Repositório Front-end (React/Vite):** [https://github.com/dsAvila/financas-front.git](https://github.com/dsAvila/financas-front.git)

---

## 🏛️ Arquitetura e Decisões de Projeto

A concepção do back-end priorizou simplicidade, manutenibilidade e isolamento de dependências, fundamentando-se nas seguintes decisões arquiteturais:

- **Microsserviço RESTful com Flask:** Escolha orientada à construção de endpoints leves, determinísticos e de alta performance, desacoplados da camada visual.
- **Camada de Persistência com SQLAlchemy e SQLite:** Utilização do padrão ORM (_Object-Relational Mapping_) para mapear os modelos relacionais (`Transacao`), garantindo tipagem forte, integridade estrutural e independência de dialeto SQL, persistido em arquivo local (`financas.db`).
- **Segurança e Comunicação Cross-Origin (CORS):** Integração com `Flask-CORS` configurado para viabilizar o consumo seguro dos recursos a partir de clientes Single Page Application (SPA).
- **Conteinerização com Docker:** Empacotamento completo do ambiente de execução (interpretador Python 3.11, dependências e servidor) via imagem Docker, mitigando incompatibilidades entre ambientes de desenvolvimento e produção.

---

## 💱 Integração com API Externa (AwesomeAPI)

Para viabilizar a consolidação de investimentos estrangeiros sem demandar conversão manual por parte do usuário, a API implementa o consumo direto da **AwesomeAPI** (provedor público de dados econômicos):

- **Endpoint Consumido:** `GET https://economia.awesomeapi.com.br/last/USD-BRL`
- **Mapeamento de Câmbio:** O serviço extrai a taxa de compra comercial (`bid`) no exato momento da listagem de dados.
- **Padrão de Resiliência (Fallback):** Caso ocorra oscilação na rede, indisponibilidade temporária do serviço externo ou tempo limite excedido (_timeout_ de 5 segundos), o back-end aciona uma taxa de contingência segura pré-estabelecida (`5.40`), assegurando que a API nunca falhe ou interrompa o cálculo patrimonial do cliente.

---

## ⚖️ Regras de Negócio e Consistência Contábil

Diferente de planilhas financeiras tradicionais que apenas agrupam valores, a API implementa regras contábeis estritas para evitar a dupla contagem do patrimônio:

1. **Impacto Real no Fluxo de Caixa:**
   - Receitas somam ao saldo disponível em caixa.
   - Despesas operacionais e compras de investimentos (tanto aportes em Reais quanto o custo convertido de ativos em Dólar) **debitam diretamente do saldo em caixa**.
     $$\text{Saldo em Caixa} = \sum \text{Receitas} - \sum \text{Despesas} - \sum \text{Investimentos (BRL)} - \sum \text{Investimentos (USD convertidos)}$$

2. **Integridade do Patrimônio Líquido:**
   - A compra de um ativo é tratada como transferência de custódia (o dinheiro sai do caixa, mas integra a carteira de investimentos). O patrimônio líquido reflete o somatório do saldo remanescente em caixa com o valor consolidado de todos os ativos acumulados.
     $$\text{Patrimônio Líquido Total} = \text{Saldo em Caixa} + \text{Investimentos (BRL)} + \text{Investimentos (USD convertidos)}$$

3. **Automação Temporal:**
   - Transações cadastradas sem data explícita recebem automaticamente o carimbo de data da operação (`YYYY-MM-DD`) no padrão ISO-8601 através do servidor.

---

## 🔌 Endpoints da API (Rotas REST)

A API disponibiliza operações completas de CRUD seguindo os verbos HTTP e códigos de status padronizados:

|    Método    | Endpoint               | Descrição                                                                   | Status Sucesso |
| :----------: | :--------------------- | :-------------------------------------------------------------------------- | :------------: |
|  **`GET`**   | `/api/transacoes`      | Retorna a listagem de transações e o objeto consolidado `resumo`.           |    `200 OK`    |
|  **`POST`**  | `/api/transacoes`      | Cadastra uma nova transação com data automática e validações de tipo/moeda. | `201 Created`  |
|  **`PUT`**   | `/api/transacoes/<id>` | Atualiza os atributos de um registro existente.                             |    `200 OK`    |
| **`DELETE`** | `/api/transacoes/<id>` | Remove permanentemente o registro da base de dados relacional.              |    `200 OK`    |

### Exemplo de Carga Útil (Payload) - `POST /api/transacoes`

```json
{
  "descricao": "Tesouro IPCA+ 2035",
  "valor": 500.0,
  "tipo": "investimento",
  "moeda": "BRL",
  "categoria": "Renda Fixa"
}
```

### Exemplo de Resposta - `GET /api/transacoes` (Estrutura Resumo)

```json
{
  "resumo": {
    "cotacao_usd": 5.18,
    "saldo_caixa": 917.62,
    "investimentos_brl": 850.0,
    "investimentos_usd": 300.0,
    "investimentos_usd_em_brl": 1555.98,
    "patrimonio_liquido_total": 3323.6
  },
  "transacoes": [
    {
      "id": 1,
      "descricao": "Salário Mensal",
      "valor": 5000.0,
      "tipo": "receita",
      "moeda": "BRL",
      "categoria": "Trabalho",
      "data": "2026-09-26"
    }
  ]
}
```

---

## 🐳 Como Executar via Docker (Recomendado)

### Pré-requisitos

- [Docker](https://www.docker.com/) instalado e em execução na máquina.

### 1. Construir a Imagem Docker

Na raiz da pasta do back-end, execute:

```bash
docker build -t api-financas .
```

### 2. Iniciar o Container

Suba o container mapeando a porta 5000:

```bash
docker run -d -p 5000:5000 --name api-financas api-financas
```

### 3. Validar a Execução

Verifique se o container está ativo executando:

```bash
docker ps
```

A API estará disponível e pronta para receber chamadas em: **`http://localhost:5000/api/transacoes`**.

---

## 💻 Execução Local sem Docker (Opcional para Desenvolvimento)

Caso opte por executar fora do container Docker:

```bash
# 1. Criar e ativar o ambiente virtual Python
python -m venv venv
# No Windows:
.\venv\Scripts\activate
# No Linux/macOS:
source venv/bin/activate

# 2. Instalar as dependências do projeto
pip install -r requirements.txt

# 3. Iniciar o servidor Flask
python app.py
```
