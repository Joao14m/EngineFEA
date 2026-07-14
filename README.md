# EngineFEA

## Visualizar resultados FEA

Os resultados numericos sao salvos em `output/Resultados_FEA.npz`, com
metadados em `output/Resultados_FEA_metadata.json`.

Para acrescentar a malha derivada para OpenGL ao `.npz`:

```powershell
python -m modelo_matematico.gerar_malha_opengl
```

O script adiciona buffers `opengl_*` ao arquivo de resultados, incluindo
vertices de linha neutra, vertices da viga e indices para `GL_LINES` e
`GL_TRIANGLES`.

Para gerar os graficos principais:

```powershell
python -m modelo_matematico.visualizar_resultados
```

As figuras sao salvas em `output/visualizacao`:

- `frequencias_por_composicao.png`
- `convergencia_por_composicao.png`
- `forma_modal_config_000_modo_01.png`
- `historico_convergencia_config_000.png`

Para escolher outra configuracao e outro modo:

```powershell
python -m modelo_matematico.visualizar_resultados --config 100 --modo 3
```

`--config` usa indice em base 0. `--modo` usa numeracao fisica do modo,
em base 1.

Para abrir as janelas interativas alem de salvar os PNGs:

```powershell
python -m modelo_matematico.visualizar_resultados --mostrar
```
