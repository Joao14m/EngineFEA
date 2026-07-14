# gaveaEngine

Modelo de elementos finitos de uma viga bi-material, com uma engine OpenGL
propria que desenha os modos de vibracao em 2D.

A viga e formada por dois trechos de material em sequencia, aco e titanio. O
modelo discretiza a viga, resolve o problema modal e obtem as **frequencias
naturais** e os **modos de vibracao**. A analise varre a proporcao entre os dois
materiais, e a engine renderiza qualquer combinacao de composicao e modo.

## Requisitos

- Python 3.10+ com `numpy` e `scipy`
- CMake 3.20+, Ninja e um compilador C++17
- vcpkg com `glfw3` e `glm` instalados (modo classico)

## Pipeline

```powershell
python -m modelo_matematico.main               # resolve as 201 vigas -> output/Resultados_FEA.npz
python -m modelo_matematico.exportar_engine    # achata para C++      -> output/viga.bin
cmake --build build --target eng               # compila a engine
.\build\eng.exe                                # renderiza
```

O solver e lento; o exportador e rapido. Depois de qualquer alteracao no solver,
rode os dois. Se so a engine mudou, basta recompilar.

## Configurar o build

```powershell
cmake -B build -S . -G Ninja "-DCMAKE_TOOLCHAIN_FILE=vcpkg/scripts/buildsystems/vcpkg.cmake"
```

As aspas em volta do `-D` sao necessarias: sem elas o PowerShell quebra o caminho
no ponto e o CMake reclama que nao encontrou o toolchain.

## Parametros da analise

Tudo que se ajusta na analise esta em `modelo_matematico/config.py`
(`AnalysisConfig`): geometria da viga, propriedades dos materiais, condicao de
contorno (`cc`), numero de modos, erro de convergencia e o passo da composicao.

Por padrao a analise roda **201 composicoes** (de 100% aco a 100% titanio, em
passos de 0,5%). Para iterar mais rapido, use
`composicoes_aco_interesse = (1.0, 0.5, 0.0)` e apenas essas serao calculadas.

## Engine

| Tecla | Acao |
|---|---|
| `<-` / `->` | Composicao (com `Shift`, passo de 10) |
| `cima` / `baixo` | Modo de vibracao |
| `+` / `-` | Escala da deflexao |
| `,` / `.` | Velocidade da animacao |
| `espaco` | Pausa |
| `S` | Linha neutra |
| `R` | Reset |
| `Esc` | Sair |

O titulo da janela mostra a composicao, o modo e a **frequencia real** em Hz. A
animacao roda num ritmo visual fixo, e nao na frequencia fisica: os modos altos
passam de 380 Hz e, animados em tempo real, viram ruido contra os 60 Hz da tela.

Para abrir direto num caso especifico:

```powershell
.\build\eng.exe --config 98 --mode 6 --scale 0.3 --paused
```

## Saida

Tudo em `output/` e gerado e nao entra no controle de versao:

- `Resultados_FEA.npz` — arrays numericos da analise
- `Resultados_FEA_metadata.json` — nomes das configuracoes, unidades e colunas
- `viga.bin` — malha achatada que a engine le
