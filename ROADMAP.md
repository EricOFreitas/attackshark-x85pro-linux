# Roadmap

Ideias para evoluir o xshark. Sem prazo — pega o que tiver vontade quando voltar.

## Recursos novos
- [ ] **`battery`** — ler nível de bateria do teclado (provável via `get_feature` após
      um comando; opcode de firmware `0x8F` mapeado em `docs/PROTOCOL.md`).
- [ ] **`brightness`** — ajustar brilho da tela (opcode `0x07`, valor 0–4; checksum no byte 8).
- [ ] **`clear`** — expor o comando `0xAC` (limpar tela) na CLI.
- [ ] **`set-gif` a partir de URL** — baixar, cortar quadrado e enviar direto de um link.
- [ ] Texto/relógio custom desenhado por nós (montar a imagem com hora/data e enviar como frame).

## Qualidade / refino
- [ ] **Resíduo de ~1px na emenda esquerda do GIF** — 179 não divide 32400 exato; investigar
      offset/wrap exato (bom *good first issue*). Ver seção "Resíduo conhecido" em `docs/PROTOCOL.md`.
- [ ] Otimizar o encoding (hoje é loop puro em Python; numpy deixaria GIFs grandes bem mais rápidos).
- [ ] Tabela de **modelos compatíveis** crescendo via issues da comunidade.
- [ ] Empacotar no **PyPI** (`pip install xshark`) e/ou AUR.

## Divulgação
- [ ] Post no **r/MechanicalKeyboards** e/ou **r/AttackShark** (nicho sem solução parecida).
- [ ] GIF/vídeo curto demonstrando `set-time` + `set-gif` funcionando.

## Reverse pendente
- [ ] Confirmar layout de bateria/firmware (capturar resposta de `get_feature`).
- [ ] Verificar se há comando de slot/persistência (mostrar imagem após reiniciar o teclado).
- [ ] Testar limites de animação (nº de frames, intervalo mínimo).
