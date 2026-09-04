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

Diga também **como o teclado estava conectado** (cabo ou receptor 2.4G): o `probe` informa
isso, e o mesmo teclado enumera com `idProduct` diferente em cada modo. No Bluetooth o canal
vendor não é exposto, então não há o que testar.

## Ambiente de dev

A regra udev é comum a todas as distros — sem ela o `/dev/hidraw*` da tela só abre como root:

```bash
sudo cp tools/99-attackshark.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

> Ela só passa a valer no **próximo evento de conexão**: reconecte o cabo ou o dongle 2.4G.
> Recarregar as regras não basta.

Depois, as dependências:

```bash
# Arch / Omarchy — tudo nos repos oficiais
sudo pacman -S --needed hidapi python-hidapi python-pillow
python3 -m venv --system-site-packages .venv && . .venv/bin/activate
pip install -e . --no-deps

# Debian / Ubuntu
sudo apt install libhidapi-hidraw0
python3 -m venv .venv && . .venv/bin/activate
pip install -e .
```

Detalhes de instalação e a nota sobre os dois bindings Python chamados `hid` estão no
[README](README.md#instalação).

Rodar lint e testes antes de abrir o PR (é o mesmo que a CI faz):

```bash
ruff check .
pytest -q
```

## Reversar novos comandos (sem Windows)

O canal vendor é `/dev/hidraw*` com usage page `0xFFFF`, usage `0x0002`, feature reports de
64 bytes (report id 0). Comandos conhecidos estão em `xshark/protocol.py` e `docs/PROTOCOL.md`.

Frame: `[opcode][reservado...][checksum][payload][zero-pad até 64]`, checksum =
`(0xFF - (sum(header[0:7]) & 0xFF)) & 0xFF`.

Para descobrir novos opcodes com segurança: monte o pacote, envie com `XSharkDevice.send_feature`
e observe a tela. Documente o achado em `docs/PROTOCOL.md`.

## Estilo

Python puro, sem dependências além de `hid` (o binding do hidapi) e `pillow` (só para
processar imagem). Mantenha funções pequenas e documente os bytes.
