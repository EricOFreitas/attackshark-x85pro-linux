# xshark

![status](https://img.shields.io/badge/status-funcional-brightgreen)
![python](https://img.shields.io/badge/python-%E2%89%A53.10-blue)
![license](https://img.shields.io/badge/license-MIT-green)

Driver/CLI open-source em Linux para o teclado **Attack Shark X85 Pro** (e parentes com a
mesma telinha TFT). Foco inicial: **acertar o relógio da tela** sem depender do app oficial
Windows/Mac — e, depois, enviar GIFs e ler bateria.

## Modelos

| Modelo | VID:PID | `set-time` |
|--------|---------|------------|
| X85 Pro | `3151:5002` | ✅ confirmado |
| K86 | `3151:4015` | ↗ via [AttackManatee](https://github.com/Jinori/AttackManatee) |
| outros Attack Shark com tela | ? | [reporte aqui](../../issues/new?template=modelo-compativel.md) |

> ✅ **Status: `set-time` funcionando no X85 Pro.** O protocolo da tela (reversado pelo
> [AttackManatee](https://github.com/Jinori/AttackManatee) para o K86) é compatível com o
> X85 Pro. Próximos alvos: GIF e bateria. Veja [`docs/PROTOCOL.md`](docs/PROTOCOL.md).

## Por que existe

O app oficial ("ATTACK SHARK WEB") exige um helper nativo `iot_manager_rs` que só tem build
para Windows e Mac. No Linux a telinha fica órfã — inclusive com o **relógio errado** e sem
como sincronizar. Este projeto resolve isso no Linux puro.

## Hardware alvo

| Item | Valor |
|------|-------|
| Modelo | Attack Shark X85 Pro |
| USB VID:PID | `3151:5002` |
| Canal de controle | interface vendor, **usage page `0xFFFF`**, Feature reports de **64 bytes** |
| Parente conhecido | K86 (`3151:4015`) — protocolo reversado em [Jinori/AttackManatee](https://github.com/Jinori/AttackManatee) |

## Como ajudar a reversar (você não precisa de Windows)

A ideia é capturar os bytes que o app oficial manda **ao acertar a hora**, usando o próprio
Chrome no Linux com um hook em `HIDDevice.prototype.sendFeatureReport`. Passo a passo em
[`tools/webhid-capture.js`](tools/webhid-capture.js).

## Instalação (dev)

```bash
# dependência de sistema (lib C do hidapi)
sudo apt install libhidapi-hidraw0     # Debian/Ubuntu

# regra udev p/ acessar o dispositivo sem root
sudo cp tools/99-attackshark.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger

# ambiente Python
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Uso

```bash
xshark probe          # lista o dispositivo e lê um feature report
xshark set-time       # ✅ sincroniza o relógio da tela com o do sistema
xshark set-gif a.gif  # (TODO) envia imagem para a tela
```

## Sincronizar a hora automaticamente (systemd user)

A tela mantém a hora sozinha, mas pode dessincronizar se a bateria interna zerar.
Para corrigir no boot e a cada 6h:

```bash
mkdir -p ~/.config/systemd/user
cp systemd/xshark-synctime.* ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now xshark-synctime.timer
```

## Créditos

Protocolo da tela reversado pelo projeto [AttackManatee](https://github.com/Jinori/AttackManatee)
(K86). Este repo confirma a compatibilidade com o X85 Pro e empacota como CLI/serviço Linux.

## Licença

MIT.
