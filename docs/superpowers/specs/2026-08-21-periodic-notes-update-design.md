# Atualização de notas periódicas no sync

## Objetivo

Quando o sync atualiza a nota diária do dia D, as notas periódicas que contêm D (semanal, mensal, trimestral, anual) devem ter seus agregados recalculados a partir das diárias do período — hoje eles são calculados só na criação (scripts Templater `*_TP_media.js`) e ficam desatualizados para sempre.

## Contexto

- Notas periódicas guardam médias no frontmatter (`pc.tempo_ativo_media`, `exercicio.media`, etc.) renderizadas por callouts dataview no corpo.
- 16 scripts JS em `99_Sistema/_templates/../Templater/*_TP_media.js` calculam essas médias **apenas na criação** da nota, lendo o frontmatter das diárias via metadataCache.
- Periódicas existentes hoje: semanais em `Jornada/{ano}/Semanas/{ano}-Www.md` e `Jornada/{ano}/{ano}-Qn.md`. Mensais/anuais ainda não existem.
- O projeto já tem `yaml_helpers.parse_note`/`rebuild_note`/`deep_merge` para editar frontmatter preservando corpo.

## Escopo

### Fase 1 (este spec) — médias escalares

| Campo na periódica | Fonte na diária | Tipo de média |
|---|---|---|
| `pc.tempo_ativo_media` | `pc.tempo_ativo` | duração ISO 8601 |
| `pc.tempo_total_media` | `pc.tempo_total` | ISO |
| `cel.tempo_total_media` | `cel.tempo_total` | ISO |
| `tempo_tela_media` | `tempo_tela` | ISO |
| `redesSociais_media` | `redesSociais` | ISO |
| `exercicio.media` | `exercicio` | número, round 2 |
| `lazer.media` | `lazer` | número, round 2 |
| `leitura.media` | `leitura` | número, round 2 |
| `procrastinacao.media` | `procrastinacao` | número, round 2 |

Fase 2 (futuro, fora deste spec): listas `sono`/`alimentacao` e objeto `estudo`.

## Comportamento

### `src/handlers/periodic.py` (novo)

`update_periodic_notes(target_date: date, vault: str) -> list[str]`

1. Calcular períodos contendo D: semana ISO (`{ano}-Www`), mês (`{ano}-{mm}`), trimestre (`{ano}-Q{n}`, n = (month-1)//3+1), ano (`{ano}`).
2. Resolver caminhos candidatos por período; atualizar todos que existirem:
   - Semana: `{vault}/01_Arquivos/Jornada/{ano}/Semanas/{ano}-Www.md`
   - Trimestre: `{vault}/01_Arquivos/Jornada/{ano}/{ano}-Q{n}.md`
   - Mês: `{vault}/01_Arquivos/Jornada/{ano}/{ano}-{mm}.md` **e** `{vault}/01_Arquivos/Jornada/{ano-MM}.md`
   - Ano: `{vault}/01_Arquivos/Jornada/{ano}.md` **e** `{vault}/01_Arquivos/Jornada/{ano}/{ano}.md`
   - Nunca criar arquivo novo; ausente = pula silenciosamente.
3. Para cada periódica existente:
   - Listar diárias do período: todos os dias entre início/fim do período (inclusive), caminho padrão das diárias; ler frontmatter via `parse_note`; diária inexistente/sem campo-fonte → excluída do denominador (mesma regra dos JS: só conta valor não-nulo).
   - Durações ISO: parser `PT(nH)(nM)(nS)` → minutos; média aritmética dos dias válidos; formatar de volta como `PT{h}H{m}M{s}S` omitindo zeros (igual `minutesToISO`); zero → `PT0S`. Sem dia válido → remover/chave vazia? Não tocar na chave (mantém valor atual).
   - Números: média simples com `round(2)`; sem dia válido → não toca.
   - Merge: `deep_merge(frontmatter_atual, medias_calculadas)` + `rebuild_note` — corpo e campos não-relacionados intactos. Idempotente por construção.

### `src/main.py`

Após `update_note(...)` da diária:

```python
from handlers.periodic import update_periodic_notes
...
updated = update_periodic_notes(target_date, vault_path)
logger.info("Notas periódicas atualizadas: %s", updated)
```

### Fora de escopo

- Criação de periódicas (continua pela extensão Periodic Notes/Obsidian).
- Fase 2 (sono/alimentação/estudo).
- Notas mensais/trimestrais de outros sistemas (Financeira etc.).

## Testes (`tests/test_periodic.py`, vault temporário)

Fixture: 3 diárias (valores mistos: pc ativo/total, cel, tempo_tela, redesSociais, exercicio/lazer/leitura/procrastinacao; uma diária sem alguns campos) + periódica semanal pré-existente com valores velhos e corpo marcador.

1. `test_medias_iso_e_numericas_calculadas` — médias batem com cálculo manual; ISO no formato `PT{h}H{m}M`.
2. `test_dias_sem_campo_nao_contam_no_denominador` — diária sem `cel` não entra na média de cel.
3. `test_preserva_corpo_e_campos_extras` — corpo intacto, chaves não-relacionadas mantidas.
4. `test_periodica_inexistente_pula_sem_erro` — nenhum arquivo criado.
5. `test_idempotencia` — segunda rodada = mesma saída.
6. `test_trimestre_e_mes_quando_existem` — Q existente atualizada; mês ausente ignorado.

## Verificação

```powershell
python -m unittest discover -s tests -v
python src/main.py --date <hoje>          # log "Notas periódicas atualizadas"
# conferir no Obsidian: W32 e Q2 com médias novas
```

## Decision Log

| Decisão | Alternativas | Motivo |
|---------|-------------|--------|
| Python replica cálculo dos JS | Disparar Templater/Obsidian headless | Projeto é CLI autônomo; sem dependência do Obsidian aberto |
| Só atualiza periódicas existentes | Criar do template | Escolha do usuário; criação continua manual/Periodic Notes |
| Fase 1 só escalares | Tudo de uma vez | Listas/objetos (sono/alimentação/estudo) têm semântica complexa; isolar risco |
| Dias sem valor saem do denominador | Contar como 0 | Mesma regra dos scripts JS originais |
| deep_merge só das chaves média | Reescrever frontmatter inteiro | Preserva campos manuais e edições do usuário |
| Caminhos candidatos p/ mês/ano | Fixar um único padrão | Convenção ainda não existe no vault; atualizar o que existir |
