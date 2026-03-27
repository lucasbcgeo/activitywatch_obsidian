# Design: Isolamento de Dependências e Redirecionamento - activitywatch_obsidian

**Data:** 2026-03-26  
**Status:** Em Revisão  
**Tópico:** Criação de ambiente virtual Python (`venv`) e script de inicialização local para garantir isolamento das dependências do ActivityWatch Client.

---

## 1. Objetivo
Isolar as dependências do projeto `activitywatch_obsidian` em um ambiente virtual local (`.venv`) e criar um ponto de entrada local (`launch_sync.bat`) que garanta a execução utilizando as bibliotecas do projeto. Este script será o ponto de integração para o Agendador de Tarefas unificado, permitindo que a tarefa externa orquestre a execução mantendo o isolamento técnico do projeto.

## 2. Arquitetura e Ambiente
- **Diretório do Projeto:** `G:\Projetos\activitywatch_obsidian`
- **Ambiente de Execução:** Python 3.13 (via `.venv` local).
- **Gerenciamento de Dependências:** `requirements.txt` e `pip`.
- **Fonte de Dados:** API do ActivityWatch (Localhost:5600).
- **Destino de Dados:** `VAULT_PATH` configurado no `.env`.

## 3. Componentes e Mudanças

### 3.1. Ambiente Virtual (`.venv`)
- Será criado em `G:\Projetos\activitywatch_obsidian\.venv`.
- Dependências a instalar:
    - `aw-client`
    - `pyyaml`
    - `python-dotenv`

### 3.2. Script de Inicialização (`launch_sync.bat`)
- **Localização:** `G:\Projetos\activitywatch_obsidian\launch_sync.bat`
- **Ação:** Executar o script `src/main.py` utilizando o interpretador Python do `.venv` local.
- **Conteúdo Sugerido:**
  ```batch
  @echo off
  "G:\Projetos\activitywatch_obsidian\.venv\Scripts\python.exe" "G:\Projetos\activitywatch_obsidian\src\main.py" %*
  ```

### 3.3. Configuração (.env)
- Garantir que o `VAULT_PATH` no arquivo `.env` utilize um caminho absoluto para evitar ambiguidades durante a execução automática.

## 4. Estratégia de Teste e Validação
1. **Verificação do Venv:** Confirmar que `aw-client` está instalado apenas no `.venv`.
2. **Teste de Sincronização:** Executar o `launch_sync.bat` manualmente e verificar se os dados do ActivityWatch aparecem na nota diária do Obsidian.
3. **Teste de Argumentos:** Validar se o `.bat` aceita o argumento `--date` corretamente (passando `%*`).

## 5. Próximos Passos
- Criação do `.venv`.
- Instalação de dependências.
- Criação do `launch_sync.bat`.
- Validação.
