# Categoria Games no frontmatter

## Objetivo

Preencher a propriedade raiz `games` da nota diária com a duração da categoria `Games` já calculada pelo ActivityWatch.

## Comportamento

- Manter a estrutura atual sob `pc` sem alterações.
- Procurar `Games` em `DailyActivity.categories` sem diferenciar maiúsculas de minúsculas.
- Quando a categoria existir e sua duração for positiva, gerar `games` como duração ISO 8601 compacta usando o formatter existente (`seconds_to_iso`), por exemplo `games: PT1H30M`.
- Quando a categoria estiver ausente ou tiver duração zero, omitir `games`.
- Não agregar subcategorias como `Games > Steam`; somente a categoria exata `Games` entra nesta propriedade.

## Implementação

A mudança ficará em `format_frontmatter`, que já recebe as categorias calculadas e monta as propriedades da nota. Não haverá nova consulta ao ActivityWatch, alteração no modelo de dados ou dependência adicional.

## Verificação

Um teste automatizado deve comprovar que:

1. `Games` com duração positiva gera a propriedade raiz no formato ISO 8601.
2. A ausência de `Games` omite a propriedade.
3. A propriedade `pc` continua sendo gerada.
