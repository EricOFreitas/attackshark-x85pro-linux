# Protocolo — notas de engenharia reversa

Documento vivo. Tudo aqui é **observado**, não oficial.

## Dispositivo

O teclado **enumera com PID diferente conforme o modo de conexão** — o mesmo hardware,
dois `idProduct`:

| Modo | USB VID:PID | Nome USB | Canal da tela |
|------|-------------|----------|---------------|
| Cabo USB | `3151:5002` | `Gaming Keyboard` | ✅ |
| Receptor 2.4G (dongle) | `3151:5006` | `2.4G Wireless Keyboard` | ✅ |
| Bluetooth | — | — | ❌ não expõe o canal vendor |

Isso importa na prática: código ou regra udev que case só com `5002` **não funciona no
dongle**, e vice-versa. O `xshark` procura os dois (`XSHARK_PRODUCT_IDS` sobrescreve, para
quem for testar outro modelo).

> No Bluetooth o perfil HID exposto não inclui a coleção vendor, então não há como falar com
> a tela. Use cabo ou dongle.

Três interfaces HID, nos dois modos:

| Interface | wMaxPacketSize | Papel provável |
|-----------|----------------|----------------|
| 0 | 8 bytes  | Teclado boot (Usage Page 0x01 / Usage 0x06) |
| 1 | 32 bytes | Consumer / teclas de mídia (Usage Page 0x0C) |
| 2 | 8 bytes  | **Vendor — canal de controle da tela** |

O que muda entre os modos é o **número de coleções HID enumeradas** (o dongle expõe mais
usages na iface 1) e, claro, **o número do nó `/dev/hidrawN`**, que depende da ordem de
conexão e não é estável. Nunca fixe o caminho: localize pelo par
`usage_page=0xFFFF` + `usage=0x0002`, que é a iface 2 nos dois modos.

Enumeração observada pelo dongle 2.4G (`3151:5006`):

```
iface= 0  usage_page=0x0001  usage=0x0006   <- teclado
iface= 1  usage_page=0x000c  usage=0x0001   <- consumer/mídia
iface= 1  usage_page=0x0001  usage=0x0080
iface= 1  usage_page=0x0001  usage=0x0006
iface= 1  usage_page=0x0001  usage=0x0002
iface= 1  usage_page=0xffff  usage=0x0001   <- vendor, NÃO é o da tela
iface= 2  usage_page=0xffff  usage=0x0002   <- vendor, canal da TELA
```

### Report descriptor do canal vendor

```
06 ff ff   Usage Page (Vendor 0xFFFF)
09 02      Usage (0x02)
a1 01      Collection (Application)
09 02        Usage (0x02)
15 80        Logical Minimum (-128)
25 7f        Logical Maximum (127)
95 40        Report Count (64)
75 08        Report Size (8)
b1 02        Feature (Data,Var,Abs)
c0         End Collection
```

Conclusões:
- Comunicação por **Feature report** (não Output) — usar `send_feature_report` /
  `get_feature_report`.
- **Report ID = 0** (não há `85 xx` no descriptor), payload de **64 bytes**.

### Acesso confirmado ✅

`get_feature_report(0, 65)` retorna 64 bytes (todos `0x00` no estado ocioso) — o canal abre,
lê e escreve sem erro. A interface da tela é a de **maior interface_number entre as vendor**
(iface 2, usage `0x0002`), não a iface 1 (usage `0x0001`). Acesso sem root via regra udev
`MODE="0666"`.

Confirmado **nos dois modos de conexão**, com o report descriptor byte a byte idêntico e o
mesmo comportamento no `set-time` (opcode `0x28`) e no upload de imagem:

| | Cabo USB | Receptor 2.4G |
|---|---|---|
| VID:PID | `3151:5002` | `3151:5006` |
| Nó observado | `/dev/hidraw4` | `/dev/hidraw2` |
| Report descriptor | idêntico | idêntico |
| `set-time` / `set-gif` | ✅ | ✅ |

> **Armadilha da regra udev:** ela só passa a valer no **próximo evento de `add`**.
> `udevadm control --reload-rules && udevadm trigger` não basta — é preciso reconectar
> fisicamente o cabo ou o dongle.

### Nota para quem for implementar noutra linguagem/binding

Em Python há **dois pacotes distintos que instalam um módulo chamado `hid`**, com APIs de
abertura incompatíveis:

| Pacote | Origem | Abre com |
|--------|--------|----------|
| [pyhidapi](https://github.com/apmorton/pyhidapi) | PyPI `hid` | `hid.Device(path=...)` |
| [cython-hidapi](https://github.com/trezor/cython-hidapi) | Arch `python-hidapi`, PyPI `hidapi` | `hid.device()` + `.open_path(...)` |

Depois de aberto, os dois expõem `send_feature_report` / `get_feature_report` / `close` com a
mesma assinatura — só a abertura difere. O `xshark` detecta qual está instalado.

## Pista do parente K86 (AttackManatee)

O K86 (`3151:4015`, mesmo vendor) também usa Feature reports no canal vendor. A hipótese
inicial era que o pacote de "set clock" tivesse a forma `[cmd, ..., ano, mês, dia, hora, min,
seg]` — **confirmada**, e o protocolo do K86 se mostrou compatível byte a byte com o X85 Pro.
Ver a seção seguinte.

## Geometria da tela do X85 Pro (decifrada por calibração visual)

Diferente do K86. Descoberta enviando padrões (split, linha, grade, seta) e medindo o
shear/emenda em fotos:

| Parâmetro | X85 Pro | K86 |
|-----------|---------|-----|
| Largura (colunas) | **138** | 240 |
| Altura / stride (linhas por coluna) | **180** | 135 |
| Pixel | RGB565 big-endian | idem |
| Ordem | column-major | idem |
| Frame | **49680 bytes** (138×180×2, sem padding) | 64800 |
| Área **visível** | **138 × 126** (topo; ~54 linhas de baixo ficam off-screen) | 135×135 nas colunas 86..220 |

O framebuffer é 138×180, mas só as **126 primeiras linhas** aparecem no painel — as de
baixo são buffer off-screen (mesma ideia do K86, que tinha colunas off-screen). A largura
inteira (138) é visível. Logo a área útil é **138×126, alinhada ao topo**.

Como medimos (e onde erramos):
- **Cuidado com padrões periódicos.** Grade, split topo/base e listras igualmente espaçadas
  ENGANAM: um deslocamento que seja múltiplo do período "encaixa" nas linhas e parece perfeito.
  Foi o que nos levou por horas a uma geometria errada (180×179) que parecia certa na grade.
- **Use sempre uma imagem assimétrica** (um personagem, um rosto) como prova final. Foi um
  Rock Lee chibi que revelou a emenda real no meio da tela.
- O sintoma decisivo: com 180 colunas, ~30% da esquerda saía deslocada (wrap horizontal) —
  estávamos mandando colunas demais. Reduzir a largura até a emenda sumir deu **138 colunas**.
- A altura (stride) 180 estava certa: o lado direito nunca tinha quebra vertical.

### Comportamento do firmware na animação
Ao tocar uma animação (vários frames), o firmware limpa a tela para **branco** entre os
frames — então a animação pisca branco a cada quadro. Imagem estática (1 frame) fica perfeita.
Suavizar isso (intervalo, ou um opcode de "não limpar") é um bom first issue.

## Formato dos pacotes (confirmado no X85 Pro)

Frame de saída, sempre 64 bytes (o zero-pad é feito na camada de transporte):

```
[opcode][reservado/parametros...][checksum][payload opcional][zero-pad ate 64]
```

**Checksum** — cobre apenas o header de 7 bytes (posições 0..6); o payload fica de fora:

```
csum = (0xFF - (sum(header[0:7]) & 0xFF)) & 0xFF
```

**Opcodes.** Os testados no X85 Pro estão marcados; os demais vêm do protocolo do K86 e ainda
não foram exercitados aqui:

| Opcode | Comando | X85 Pro |
|--------|---------|---------|
| `0x28` | set clock | ✅ testado |
| `0xA5` | init de imagem/animação | ✅ testado |
| `0x25` | chunk de pixels | ✅ testado |
| `0xAC` | limpar tela | ⚠️ implementado, sem teste em hardware |
| `0x07` | brilho | ❓ não implementado |
| `0x8F` | firmware | ❓ não implementado |

**`0x28` (set clock)** — binário puro, **não** BCD; ano em uint16 **big-endian**:

```
byte 0     opcode 0x28
byte 1-6   reservado (0x00)
byte 7     checksum (0xD7 para este header)
byte 8-9   ano (uint16 big-endian)
byte 10    mes (1-12)
byte 11    dia (1-31)
byte 12    hora (0-23)
byte 13    minuto (0-59)
byte 14    segundo (0-59)
```

Exemplo real capturado em 2026-09-04 14:20:39:

```
28 00 00 00 00 00 00 d7 07 ea 09 04 0e 14 27
                     ^csum ^--^ 0x07ea = 2026
```

**`0xA5` (init) e `0x25` (chunk)** — o upload é *chunked*, com 56 bytes de pixel por report.
Nos dois, os bytes finais (trailing/pixels) **não** entram no checksum:

```
A5 00 <nframes> <interval> <size_lo> <size_hi> 00 <csum> | <x_lo> <x_hi> <w> <h>
25 <frame_idx> <nframes> <interval> <chunk_lo> <chunk_hi> <data_len> <csum> | <pixels...>
```

`size_per_frame` e `chunk_idx` são uint16 **little-endian** (repare: o oposto do ano no `0x28`).

## A confirmar

- [ ] Como é o ACK / `get_feature_report` de status — no estado ocioso volta só `0x00`.
      Bateria e nível de sinal do dongle presumivelmente saem por aqui.
- [ ] Opcode de brilho (`0x07`) e leitura de firmware (`0x8F`), herdados do K86.
- [ ] Existe algum opcode de "não limpar entre frames"? O firmware pisca branco a cada
      quadro da animação (ver acima).
- [ ] O `0xAC` (limpar tela) está implementado em `build_clear()` mas nunca foi disparado
      contra o hardware.
