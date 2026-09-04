# xshark

![CI](https://github.com/EricOFreitas/attackshark-x85pro-linux/actions/workflows/ci.yml/badge.svg)
![status](https://img.shields.io/badge/status-funcional-brightgreen)
![python](https://img.shields.io/badge/python-%E2%89%A53.10-blue)
![license](https://img.shields.io/badge/license-MIT-green)

Driver/CLI open-source em Linux para o teclado **Attack Shark X85 Pro** (e parentes com a
mesma telinha TFT): **acertar o relógio da tela** e **enviar imagens/GIFs**, sem depender do
app oficial Windows/Mac.

> **Projeto hobby, distribuído como está (as-is).** Funciona e resolve o que eu precisava, mas
> não há garantia de manutenção nem promessa de novos recursos. Use à vontade; PRs são bem-vindos,
> mas podem demorar ou não ser respondidos.

## Modelos

| Modelo | VID:PID | `set-time` |
|--------|---------|------------|
| X85 Pro | `3151:5002` (cabo)<br>`3151:5006` (2.4G) | ✅ `set-time` + `set-gif` (tela 138×180) |
| K86 | `3151:4015` | ↗ via [AttackManatee](https://github.com/Jinori/AttackManatee) (tela 240×135) |
| outros Attack Shark com tela | ? | [reporte aqui](../../issues/new?template=modelo-compativel.md) |

> ✅ **`set-time` e `set-gif` funcionando no X85 Pro.** O protocolo da tela (reversado pelo
> [AttackManatee](https://github.com/Jinori/AttackManatee) para o K86) é compatível com o
> X85 Pro. Veja [`docs/PROTOCOL.md`](docs/PROTOCOL.md).

## Por que existe

O app oficial ("ATTACK SHARK WEB") exige um helper nativo `iot_manager_rs` que só tem build
para Windows e Mac. No Linux a telinha fica órfã — inclusive com o **relógio errado** e sem
como sincronizar. Este projeto resolve isso no Linux puro.

## Hardware alvo

| Item | Valor |
|------|-------|
| Modelo | Attack Shark X85 Pro |
| USB VID:PID | `3151:5002` (cabo USB) · `3151:5006` (receptor 2.4G) |
| Bluetooth | ❌ não expõe o canal vendor — use cabo ou dongle |
| Canal de controle | interface vendor, **usage page `0xFFFF`**, Feature reports de **64 bytes** |
| Parente conhecido | K86 (`3151:4015`) — protocolo reversado em [Jinori/AttackManatee](https://github.com/Jinori/AttackManatee) |

## Como ajudar a reversar (você não precisa de Windows)

A ideia é capturar os bytes que o app oficial manda **ao acertar a hora**, usando o próprio
Chrome no Linux com um hook em `HIDDevice.prototype.sendFeatureReport`. Passo a passo em
[`tools/webhid-capture.js`](tools/webhid-capture.js).

## Instalação

A regra udev é comum a todas as distros — sem ela o `/dev/hidraw*` da tela só abre como root:

```bash
sudo cp tools/99-attackshark.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

> A regra só passa a valer no **próximo evento de conexão**: reconecte o cabo ou o dongle 2.4G.

### Arch / Omarchy

Tudo está nos repositórios oficiais — não precisa de venv, `pip` nem AUR:

```bash
sudo pacman -S --needed hidapi python-hidapi python-pillow
python3 -m venv --system-site-packages .venv && source .venv/bin/activate
pip install -e . --no-deps
```

O `--no-deps` é proposital: as dependências já vieram do `pacman`, e sem ele o `pip`
baixaria uma segunda cópia do binding pelo PyPI.

> **Sobre o binding `hid`:** existem dois pacotes Python diferentes com esse mesmo nome de
> módulo — o [pyhidapi](https://github.com/apmorton/pyhidapi) (PyPI `hid`, usado pelo
> `pip install`) e o [cython-hidapi](https://github.com/trezor/cython-hidapi) (o que o Arch
> empacota como `python-hidapi`). As APIs de abertura são incompatíveis; o `xshark` detecta
> qual está instalado e usa a certa, então qualquer um dos dois serve.

### Debian / Ubuntu

```bash
sudo apt install libhidapi-hidraw0
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

### Sincronizar a hora sozinho (systemd)

A unit chama `%h/.local/bin/xshark`. Se você instalou num venv, deixe um symlink lá
(o `ExecStart` **precisa** de caminho absoluto — sem barra, o systemd procura num PATH
fixo que não inclui `~/.local/bin` nem venvs, e falha com `203/EXEC`):

```bash
ln -sf "$PWD/.venv/bin/xshark" ~/.local/bin/xshark

cp systemd/xshark-synctime.* ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now xshark-synctime.timer
```

Conferir: `systemctl --user list-timers xshark-synctime.timer`

## Uso

```bash
xshark probe          # lista o dispositivo e lê um feature report
xshark set-time       # ✅ sincroniza o relógio da tela com o do sistema
xshark set-gif a.png  # ✅ envia imagem (PNG/JPG) para a tela
xshark set-gif a.gif  # ✅ envia GIF animado (multi-frame, em loop)
xshark playlist ~/telinha --interval 30 [--shuffle]  # rotaciona imagens/GIFs de uma pasta
```

> A telinha não guarda playlist — o `playlist` fica reenviando cada imagem a cada `--interval`
> segundos (Ctrl+C para parar). Cada envio leva alguns segundos, então use intervalos folgados.

A tela do X85 Pro é **138×180, RGB565 big-endian, column-major** (frame de 49680 bytes), mas
só **138×126 são visíveis** (as linhas de baixo ficam off-screen). As imagens já respeitam
essa área; use `--fit` para preservar a proporção (letterbox). Geometria decifrada por
calibração visual — ver [`docs/PROTOCOL.md`](docs/PROTOCOL.md). Outros modelos: ajuste com
`--width/--height/--xoff`.

## Sincronizar a hora automaticamente (systemd user)

A tela mantém a hora sozinha, mas pode dessincronizar se a bateria interna zerar.
Para corrigir no boot e a cada 6h:

```bash
mkdir -p ~/.config/systemd/user
cp systemd/xshark-synctime.* ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now xshark-synctime.timer
```

## Próximos passos

Ideias e tarefas futuras estão em [`ROADMAP.md`](ROADMAP.md) (bateria, brilho, PyPI, refino do GIF…).

## Desenvolvimento e testes

```bash
pip install -e ".[dev]"
ruff check .     # lint
pytest -q        # testes das funções puras (protocolo + encoding, sem hardware)
```

> Os comandos que tocam o hardware (`set-time`, `set-gif`) foram validados ao vivo no X85 Pro.
> Os testes cobrem a montagem de pacotes e o encoding RGB565, que é onde mora a lógica.

## Créditos

Protocolo da tela reversado pelo projeto [AttackManatee](https://github.com/Jinori/AttackManatee)
(K86). Este repo confirma a compatibilidade com o X85 Pro e empacota como CLI/serviço Linux.

## Licença

MIT.
