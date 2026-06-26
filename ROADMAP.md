# Ideias futuras (sem compromisso)

Isto aqui é um **hobby**. O xshark já faz o que eu precisava — acertar a hora e botar imagem
na telinha — e talvez eu nunca mais mexa nele. Esta lista é só um despejo de ideias, pra mim
mesmo do futuro ou pra quem quiser pegar.

**Nada aqui é promessa de entrega.** O projeto é distribuído como está (as-is), sem garantia
de manutenção. PRs são bem-vindos, mas podem demorar ou nem ser respondidos — sem ressentimentos.

## Ideias de recursos
- `battery` — ler nível de bateria (provável via `get_feature`; opcode `0x8F`).
- `brightness` — ajustar brilho da tela (opcode `0x07`, 0–4).
- `clear` na CLI — expor o `0xAC` (limpar tela).
- `set-gif` a partir de uma URL.
- Relógio/texto custom desenhado por nós e enviado como imagem.

## Refino / qualidade
- Suavizar o flash branco da animação: o firmware limpa a tela pra branco entre frames.
  Talvez exista um opcode de "trocar frame sem limpar" — seria um alvo de engenharia reversa.
- Otimizar o encoding com numpy (hoje é loop puro em Python).
- Empacotar no PyPI / AUR.

## Reverse ainda em aberto
- Confirmar o layout de bateria/firmware (capturar a resposta de `get_feature`).
- Comando de slot/persistência (a imagem sobreviver a reiniciar o teclado?).
- Limites de animação (nº de frames, intervalo mínimo).
