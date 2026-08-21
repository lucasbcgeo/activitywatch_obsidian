# Tempo ativo inclui AFK de categorias específicas

## Objetivo

Eventos `afk` do `aw-watcher-afk` cujo período coincide com janelas em primeiro plano pertencentes a categorias específicas do ActivityWatch devem contar como **tempo ativo** (`active_seconds`), e não apenas eventos `not-afk`.

## Contexto

- Hoje: `active_seconds` = soma das durações dos eventos com `status == "not-afk"` (src/handlers/fetch.py). AFK é ignorado; fica implícito em `total - ativo`.
- Problema: café.exe, almoço.exe, TogglTrack rodando afastado etc. são atividades válidas que o watcher marca como afk → subestima o tempo ativo.
- As categorias vêm das regras regex configuradas no ActivityWatch (`/api/0/settings` → `classes`), já consumidas por `_fetch_categories`/`_classify_event` para a seção de categorias da nota.
- `_build_categories` pula apps dummy (`INTERVALO_APPS`) ao exibir categorias — esse skip continua; a classificação para tempo ativo é caminho separado e NÃO pula dummies (regras "Intervalo > ..." do AW batem neles).

## Lista de categorias (constante em fetch.py)

```python
COUNT_AFK_CATEGORIES = {
    "Intervalo > Pausa Rápida",
    "Intervalo > Café da manhã",
    "Intervalo > Almoço",
    "Intervalo > Jantar",
    "Intervalo > Pausa Longa",
    "Estudando > TogglTrack",
    "Exercício",
    "X",
}
```

Nomes comparados exatamente ao retorno de `_classify_event` (`" > ".join(cls["name"])`).

## Comportamento

### Refactor mínimo no `fetch_daily`

1. Classes do AW buscadas **uma vez** por run: `classes = _fetch_categories(host, port)`.
2. `_compute_active_seconds(afk_events, window_events, classes)` substitui o loop atual de soma de not-afk.
3. `_build_categories(client, window_bid, start, end, classes)` recebe classes por parâmetro (assinatura muda; comportamento idêntico).

### `_compute_active_seconds(afk_events, window_events, classes) -> float`

1. Pré-classificar janelas: para cada evento de janela, `(start, end, categoria)` onde start/end derivam de timestamp+duration; classificação via `_classify_event(event, classes)` com cache por `(app, title)` (mesma string não roda regex 2x).
2. Eventos `not-afk`: somar duração integral.
3. Eventos `afk`: para cada evento, percorrer janelas com `categoria ∈ COUNT_AFK_CATEGORIES`, calcular interseção `[max(starts), min(ends))` e somar quando `end > start`.
4. Retornar total.

Invariantes:
- Sem dupla contagem: períodos afk/not-afk vêm do mesmo watcher e são disjuntos; contribuições só se somam.
- Interseção parcial conta só o trecho compartilhado.

### Fallbacks

- Sem bucket de janela ou sem classes (settings indisponível): `logger.warning` + comportamento atual (só not-afk).

### Inalterados

`total_seconds`, formatter, writer, main. O novo `active_seconds` flui automaticamente para frontmatter `pc.tempo_ativo` e header "💻 Ativo:".

## Testes (`tests/test_fetch.py`, eventos sintéticos)

1. `test_afk_em_categoria_da_lista_conta_ativo` — afk 30min ∩ janela "Intervalo > Café da manhã" → +30min ativo.
2. `test_afk_fora_da_lista_nao_conta` — afk ∩ janela Uncategorized → não soma.
3. `test_intersecao_parcial` — janela maior que período afk → só o overlap entra.
4. `test_multiplas_janelas_num_afk` — café.exe 20min + navegador 10min dentro do mesmo afk → só os 20min (navegador fora da lista).
5. `test_not_afk_soma_integral` — comportamento atual preservado.
6. `test_sem_classes_fallback_not_afk` — classes `[]` → warning + só not-afk.

## Verificação

```powershell
python -m unittest discover -s tests -v
python src/main.py --date <hoje>   # conferir pc.tempo_ativo >= valor anterior
```

## Decision Log

| Decisão | Alternativas | Motivo |
|---------|-------------|--------|
| Interseção precisa afk×janela | Categoria dominante por evento afk | Exato em bordas; sem dupla contagem |
| Regras regex do AW como fonte de categoria | Match direto hardcoded no código | Fonte única de verdade; usuário já mantém as regras lá |
| Lista hardcoded (`COUNT_AFK_CATEGORIES`) | Env var | Conjunto estável atrelado à config AW; fácil migrar depois se precisar |
| Dummies classificados aqui (sem skip) | Reutilizar skip de `_build_categories` | Skip existe só para não duplicar exibição; tempo ativo precisa deles |
| Buscar classes 1x e injetar | Buscar dentro de cada função | Evita 2 chamadas HTTP por run |
