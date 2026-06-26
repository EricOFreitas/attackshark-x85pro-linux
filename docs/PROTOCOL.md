# Protocolo — notas de engenharia reversa

Documento vivo. Tudo aqui é **observado**, não oficial.

## Dispositivo

```
USB VID:PID = 3151:5002   ("Gaming Keyboard")
```

Três interfaces HID:

| Interface | wMaxPacketSize | Papel provável |
|-----------|----------------|----------------|
| 0 | 8 bytes  | Teclado boot (Usage Page 0x01 / Usage 0x06) |
| 1 | 32 bytes | Consumer / teclas de mídia (Usage Page 0x0C) |
| 2 | 8 bytes  | **Vendor — canal de controle da tela** |

### Report descriptor do canal vendor (`hidraw4`)

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

`get_feature_report(0, 65)` no `/dev/hidraw4` retorna 64 bytes (todos `0x00` no estado
ocioso) — o canal abre, lê e escreve sem erro. A interface da tela é a de **maior
interface_number entre as vendor** (iface 2, usage `0x0002`), não a iface 1 (usage `0x0001`).
Acesso sem root via regra udev `MODE="0666"`.

## Pista do parente K86 (AttackManatee)

O K86 (`3151:4015`, mesmo vendor) também usa Feature reports no canal vendor. Vale comparar:
o app oficial hooka `HIDDevice.prototype.sendReport` **e** `sendFeatureReport`. Nossa hipótese
inicial é que o pacote de "set clock" tenha a forma:

```
[ cmd, ... , ano, mês, dia, hora, min, seg, ... ]   (a confirmar)
```

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
| Área visível | tela inteira (sem offset) | 135×135 nas colunas 86..220 |

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

## A confirmar (TODO da captura)

- [ ] Byte(s) de comando (primeiro byte costuma ser opcode).
- [ ] Layout do pacote de relógio (BCD? binário? ano em 1 ou 2 bytes?).
- [ ] Existe checksum/terminador?
- [ ] Como é o ACK / get_feature_report de status (bateria?).
- [ ] Pacote de upload de GIF (provável: chunked, vários reports).
