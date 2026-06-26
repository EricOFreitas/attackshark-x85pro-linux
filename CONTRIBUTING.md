# Contribuindo

Obrigado por ajudar! Este projeto controla a tela TFT de teclados Attack Shark no Linux.
A base do protocolo veio do reverse do [AttackManatee](https://github.com/Jinori/AttackManatee)
(K86) e foi confirmada no X85 Pro.

## Reportar um modelo compatível (ou não)

Abra uma issue com o template "Modelo compatível" e inclua a saída de:

```bash
xshark probe
```

E o resultado de `xshark set-time` (a hora mudou na telinha? mostrou lixo? nada?).
Isso nos diz se o opcode `0x28` vale para o seu modelo.

## Ambiente de dev

```bash
sudo apt install libhidapi-hidraw0
sudo cp tools/99-attackshark.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger   # depois reconecte o USB
python3 -m venv .venv && . .venv/bin/activate && pip install -e .
```

## Reversar novos comandos (sem Windows)

O canal vendor é `/dev/hidraw*` com usage page `0xFFFF`, usage `0x0002`, feature reports de
64 bytes (report id 0). Comandos conhecidos estão em `xshark/protocol.py` e `docs/PROTOCOL.md`.

Frame: `[opcode][reservado...][checksum][payload][zero-pad até 64]`, checksum =
`(0xFF - (sum(header[0:7]) & 0xFF)) & 0xFF`.

Para descobrir novos opcodes com segurança: monte o pacote, envie com `XSharkDevice.send_feature`
e observe a tela. Documente o achado em `docs/PROTOCOL.md`.

## Estilo

Python puro, sem dependências além de `hid`. Mantenha funções pequenas e documente os bytes.
