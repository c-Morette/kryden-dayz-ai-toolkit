# Kryden DayZ AI Toolkit

Skills, agentes e ferramentas para fazer mod de DayZ com IA, empacotados como plugin para Claude Code e OpenAI Codex. É o que eu uso nos meus mods. Cobrem código em Enforce Script, roupa e equipamento gerados a partir de modelo 3D, e interface de DayZ.

Feito por Morette (Kryden). In English: [README.md](README.md)

## Log limpo não prova que funciona

Um mod de DayZ pode carregar sem nenhum `SCRIPT (E)` e continuar quebrado. Das 129 armadilhas do `dayz-gotchas`, 84% falham sem deixar uma linha no log. Cada uma traz o sintoma que você vê, como detectar e a regra para evitar.

A IA ajuda a escrever e revisar o código. O teste no jogo continua com você.

## O que vem no pacote

| Parte | Tipo | O que faz |
|---|---|---|
| `dayz-gotchas` | skill | 129 armadilhas de DayZ e Enforce Script, 108 delas silenciosas. Formato: sintoma, como detectar, regra. Medidas em projeto real. |
| `dayz-modder` | agente | Escreve e revisa Enforce Script (`.c`, `config.cpp`, `model.cfg`) com o `dayz-gotchas` carregado. |
| `dayz-model-forge` | skill e agente | Conduz o Model Forge: confere a licença do modelo, roda o build, lê as checagens e acompanha o teste no jogo. |
| Model Forge | ferramenta em Python | Gera o item de vestir de DayZ a partir de um modelo 3D, sem Object Builder. Detalhes abaixo. |
| `dayz-layout-hud` | skill, em desenvolvimento | Monta menus e painéis de HUD com o Layout HUD Designer e conhece as regras de widget que falham em silêncio. |
| Layout HUD Designer | ferramenta, em desenvolvimento | Design system no estilo shadcn/ui para interface de DayZ, em Enforce Script. Detalhes abaixo. |

## Instalação

### Claude Code

```
/plugin marketplace add c-Morette/kryden-dayz-ai-toolkit
/plugin install kryden-dayz-ai-toolkit@kryden-dayz-ai-toolkit
```

### OpenAI Codex

```
codex plugin marketplace add c-Morette/kryden-dayz-ai-toolkit
codex plugin add kryden-dayz-ai-toolkit@kryden-dayz-ai-toolkit
```

Ou, depois de adicionar o marketplace, abra `/plugins` dentro do Codex e instale o `kryden-dayz-ai-toolkit` por lá.

As skills funcionam no Codex. Os dois agentes, `dayz-modder` e `dayz-model-forge`, são do Claude Code. Para o Codex há versões opcionais em `codex/agents/`. Se quiser usar, copie para `~/.codex/agents/` (passo a passo em [codex/README.md](codex/README.md), em inglês).

### Sem o plugin

Copie as pastas de dentro de `skills/` para:

- `~/.agents/skills/` no Codex
- `.claude/skills/` no Claude Code

As skills `dayz-model-forge` e `dayz-layout-hud` procuram a ferramenta em `../../tools/` a partir da pasta da skill. Copie `tools/` ao lado da pasta `skills` de destino: `~/.agents/tools/` no Codex, `.claude/tools/` no Claude Code.

## Model Forge

O Model Forge pega um modelo 3D (`.glb` ou zip do Sketchfab) e gera o item de vestir sem Object Builder.

Saem os `.p3d` MLOD masculino, feminino e de chão, as texturas `.paa`, o `.rvmat` e o `model.cfg`.

O que ele faz:

- ajusta o item aos corpos vanilla masculino e feminino
- aplica os pesos dos ossos do personagem (skinning)
- gera os LODs
- confere se o `binarize` aceita o resultado
- renderiza uma imagem de prova a partir dos arquivos gerados

Situação:

- testado no jogo: colete, e jaqueta (masculino e feminino)
- mochila: uns 90%, testada no personagem masculino
- calça, capacete, máscara e outros itens: ainda sem suporte

Build sem erro e render certo não provam que o item funciona no jogo. Teste com o roteiro do [INGAME-TEST.md](skills/dayz-model-forge/references/INGAME-TEST.md) (em inglês).

### Requisitos

- Windows
- Blender 4.4
- Python 3 com Pillow
- DayZ Tools
- drive `P:` montado
- os corpos vanilla (`character_male.p3d` e `character_female.p3d`), baixados do repositório oficial da Bohemia, o [DayZ-Misc](https://github.com/BohemiaInteractive/DayZ-Misc)
- um `.blend` com o rig do personagem, montado por você. Ele não vem no pacote por causa da licença. O [README do Model Forge](tools/model-forge/README.md) (em inglês) explica o que o rig precisa ter.

### Licença do modelo e do que sai dele

- Use só modelo com licença que permita: CC0 ou CC-BY com download liberado, ou comprado com licença para mod de jogo. CC-BY exige crédito ao autor na descrição do seu mod.
- Um `.p3d` gerado a partir dos corpos vanilla é material derivado de arquivos da Bohemia. Ele fica sob a [ADPL-SA](https://www.bohemia.net/community/licenses/arma-and-dayz-public-license-share-alike-adpl-sa) (uso não comercial, só em Arma e DayZ, e quem compartilhar usa a mesma licença), e não sob a licença deste pacote.

## Layout HUD Designer (em desenvolvimento)

**Esta ferramenta ainda está em desenvolvimento e não está pronta.** Nomes, tokens e API podem mudar.

É um design system no estilo shadcn/ui para interface de DayZ, escrito em Enforce Script. Tem:

- tokens de cor
- atlas nine-slice próprio, com cantos arredondados
- os componentes `Button`, `Badge`, `Card` e `Separator`
- um lab dentro do jogo que grava no log o tamanho e a posição de cada widget

Esses quatro componentes foram testados no jogo em 1280x720, 1600x900 e 1920x1080. O que ainda não foi testado ou construído está no [README da ferramenta](tools/layout-hud-designer/README.md) (em inglês).

## Recomendados (não vêm no pacote)

Os dois são de terceiros, com licença MIT.

- [StarDZ-Team/Dayz-Modding-Skills](https://github.com/StarDZ-Team/Dayz-Modding-Skills), skill `dayz-modding`: cobre a API geral de DayZ. O `dayz-gotchas` deixa de fora o que ela já cobre, então use as duas juntas.
- [willy92wins/dayz-mcp](https://github.com/willy92wins/dayz-mcp): servidor MCP que controla o DayZDiag, para a IA rodar testes dentro do jogo.

## Meus mods

Os mods não vêm neste pacote. Os meus mods abertos estão listados, com link do GitHub e da Steam Workshop, no [DayZ-OpenSource](https://github.com/c-Morette/DayZ-OpenSource).

## Licença

MIT + Commons Clause. Você pode usar, estudar e modificar o pacote, inclusive no seu servidor e nos seus mods, de graça. Não pode vender o pacote nem um serviço cujo valor venha dele. Texto completo em [LICENSE](LICENSE).
