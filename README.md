# Sistema Distribuído de Monitoramento de Pneus - F1 GP Brasil

Este projeto consiste no desenvolvimento de um sistema distribuído para monitoramento em tempo real das condições dos pneus de carros de Fórmula 1 durante o Grande Prêmio de Interlagos. O sistema foi projetado para atender aos requisitos de alta disponibilidade, escalabilidade e comunicação heterogênea, simulando 24 veículos e múltiplos sensores de pista conforme especificado no Trabalho Prático de Sistemas Distribuídos.

## Visão Geral da Arquitetura

O sistema é composto por quatro subsistemas principais, cada um utilizando um estilo arquitetural de comunicação específico para atender aos requisitos de desempenho e desacoplamento:

### 1. SCCP (Subsistema de Coleta das Condições dos Pneus)
* **Componente:** Carros (Clientes Publicadores).
* **Protocolo:** MQTT (Baseado em Eventos).
* **Descrição:** Simula a telemetria física dos pneus (temperatura, pressão e desgaste) baseada na geografia real do circuito de Interlagos. Os carros publicam dados periodicamente em um tópico MQTT.
* **Escala:** 24 instâncias (réplicas).

### 2. ISCCP (Infraestrutura de Coleta)
* **Componente:** Sensores de Pista (Ponte MQTT -> gRPC).
* **Protocolo:** Híbrido (Subscrição MQTT e Cliente gRPC).
* **Descrição:** Atua como *Middleware*. Coleta os dados brutos dos carros via MQTT, realiza *buffering* (acumulação) em memória e transmite lotes de dados (*batching*) periodicamente para o servidor de armazenamento para otimização de rede.
* **Escala:** 15 instâncias (réplicas) distribuídas.

### 3. SACP (Subsistema de Armazenamento)
* **Componente:** Servidores de Aplicação e Cluster de Banco de Dados.
* **Protocolo:** gRPC (Baseado em Objetos) e Replicação de Dados.
* **Descrição:** Recebe lotes de telemetria via gRPC com balanceamento de carga (*Load Balancing*) e persiste as informações em um banco de dados NoSQL distribuído.
* **Infraestrutura:** Cluster MongoDB configurado em *Replica Set* com 3 nós.
* **Escala:** 3 servidores de aplicação.

### 4. SVCP (Subsistema de Visualização)
* **Componente:** Servidor Web e Dashboard.
* **Protocolo:** HTTP/REST (Baseado em Recursos).
* **Descrição:** Disponibiliza uma API REST para consulta dos dados e renderiza um dashboard web para visualização em tempo real do estado da frota. Utiliza *Aggregation Pipelines* do MongoDB para consultas eficientes.

## Tecnologias Utilizadas

* **Linguagem:** Python 3.9+
* **Orquestração:** Docker e Docker Compose
* **Mensageria:** Eclipse Mosquitto (MQTT)
* **RPC:** gRPC e Protocol Buffers (Protobuf)
* **Banco de Dados:** MongoDB (Replica Set)
* **Backend Web:** Flask
* **Frontend:** HTML5, JavaScript (Fetch API) e Bootstrap 5

## Estrutura do Projeto
```
/
├── car/            # Código fonte dos simuladores de carros
├── isccp/          # Código dos sensores de coleta (Gateway)
├── ssacp/          # Servidor de armazenamento gRPC
├── ssvcp/          # Servidor de visualização e API Flask
├── protos/         # Contratos gRPC (.proto) e stubs gerados
├── docker/         # Configurações de infraestrutura (ex: mosquitto.conf)
├── docker-compose.prod.yml  # Orquestração do ambiente de produção (Escalável)
├── docker-compose.dev.yml   # Ambiente de desenvolvimento (Instância única)
└── README.md
```
## Pré-requisitos

* Docker Engine instalado e em execução.
* Docker Compose instalado.
* Portas disponíveis no host: 1883 (MQTT), 5000 (Web), 50051 (gRPC), 27017 (Mongo).

## Instruções de Execução

O sistema deve ser executado utilizando o Docker Compose. Abaixo estão as instruções para o ambiente completo de produção.

### 1. Inicialização do Ambiente

Execute os comandos abaixo no diretório raiz do projeto:

    # 1. Parar containers e remover volumes antigos (Crucial para resetar o cluster do banco)
    docker-compose -f docker-compose.prod.yml down -v

    # 2. Construir as imagens e iniciar o cluster em segundo plano
    docker-compose -f docker-compose.prod.yml up --build -d

**Nota:** A inicialização completa pode levar entre 30 a 60 segundos. Esse tempo é necessário para:
1.  O Cluster MongoDB eleger um nó primário.
2.  Os 24 carros inicializarem e sincronizarem com a simulação.

### 2. Acesso ao Sistema

Após a estabilização do ambiente, acesse o dashboard através do navegador:

* **URL:** `http://localhost:5000`

### 3. Monitoramento de Logs

Para verificar o funcionamento do balanceamento de carga e o fluxo de dados entre os subsistemas:

    docker-compose -f docker-compose.prod.yml logs -f

## Destaques da Implementação Técnica

1.  **Simulação Física Realista:**
    * O algoritmo dos carros utiliza um mapeamento GPS dos 15 setores reais do Autódromo de Interlagos.
    * Variaveis como velocidade, temperatura e desgaste são calculadas baseadas na geometria da pista (retas vs. curvas) e carga lateral (pneus de apoio sofrem maior desgaste).

2.  **Identidade em Sistemas Replicados:**
    * Utilização de identificação dinâmica baseada no *hostname* dos containers Docker para atribuir nomes de pilotos reais (ex: "RedBull - Verstappen") às 24 réplicas genéricas, evitando colisões de identidade.

3.  **Otimização de Tráfego:**
    * Implementação de *Batching* no subsistema ISCCP: mensagens MQTT de alta frequência são acumuladas e enviadas em lotes comprimidos via gRPC a cada 1 segundo, reduzindo drasticamente o *overhead* de conexões no banco de dados.

4.  **Alta Disponibilidade:**
    * Banco de dados configurado com *Replica Set* (1 Primário, 2 Secundários).
    * Serviço de armazenamento (SSACP) escalado em 3 réplicas com *Round-Robin Load Balancing* nativo do Docker.

## Autoria

Projeto desenvolvido para a disciplina de Sistemas Distribuídos.