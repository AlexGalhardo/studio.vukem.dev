# Fotos, recortes e texturas

Todo o visual depende de **fotos reais**. Rode os comandos da raiz do projeto (depois do `setup.sh`).

## 1. Lista de fotos por cena

Antes de buscar, liste o que cada cena precisa. Para o exemplo (microchips):

| Cena | Fotos | Tipo |
|---|---|---|
| 2 | válvula (×2 modelos), foto do ENIAC | recortes + foto inteira |
| 3 | mão aberta, caneta, marca-texto, válvula, chip | recortes |
| 4 | 4–5 objetos do tema | recortes pequenos |
| 5 | frente e verso do objeto + "miolo" | recortes + foto quadrada |
| 6 | foto de lugar/pessoa (fábrica, laboratório, rua…) | foto inteira |
| 7 | 1–2 objetos de mesa | recortes |

Prefira objetos **fotografados sozinhos em fundo liso** (branco, preto ou cinza): o recorte sai limpo. Para a cena 6 escolha uma foto com **um detalhe que dá para circular** (algo na mão de alguém, uma placa, um equipamento).

## 2. Buscar e baixar (Wikimedia Commons, com crédito)

```bash
audio/.venv/bin/python tools/commons.py buscar "Vacuum tube" --n 16 --folha previews/c_valvula.jpg
audio/.venv/bin/python tools/commons.py baixar "File:Mullard el34.jpg" videos/<nome>/img/valvula.jpg --largura 1024
```

- Busque em **inglês** e com termos simples ("Vacuum tube", "Integrated circuit chip", "Human hand palm", "Wood texture", "Clean room semiconductor"). Termos longos não acham nada.
- Abra a folha de contato (`--folha`) e escolha olhando.
- O download grava título, licença e autor em `img/creditos.json`. O script só aceita CC0, domínio público, CC BY e CC BY-SA.
- **CC BY e CC BY-SA exigem crédito no vídeo.** Gere a linha com `tools/commons.py creditos videos/<nome>/img` e ponha no rodapé da última cena (Inter Tight 15 px, cinza escuro).

## 3. Recortar (Vision do macOS)

```bash
audio/.venv/bin/python tools/recortar.py videos/<nome>/img/valvula.jpg videos/<nome>/img/valvula_cut.png --max 1200
```

Abra a prova em `previews/recorte-*.jpg` (o recorte sobre verde). O Vision perde partes finas (pernas de chip, fios, dedos muito abertos). Com dois objetos na foto, use `--caixa x0,y0,x1,y1` (frações de 0 a 1) para cortar antes.

## 4. Versões leves e texturas

Muitas cópias na tela (padrão, adesivos) pedem arquivos pequenos. As mãos de passagem pedem uma versão desfocada.

```bash
audio/.venv/bin/python tools/texturas.py reduzir  videos/<nome>/img/chip_cut.png videos/<nome>/img/chip_s.png --max 440
audio/.venv/bin/python tools/texturas.py desfocar videos/<nome>/img/mao_cut.png  videos/<nome>/img/mao_blur.png
audio/.venv/bin/python tools/texturas.py papel    videos/<nome>/img/papel_cinza.jpg
audio/.venv/bin/python tools/texturas.py tecido   videos/<nome>/img/tecido_escuro.jpg
audio/.venv/bin/python tools/texturas.py mesa     videos/<nome>/img/mesa_clara.jpg
audio/.venv/bin/python tools/texturas.py madeira  videos/<nome>/img/madeira.jpg --foto videos/<nome>/img/madeira_foto.jpg --girar
```

- As texturas saem com 114,8% do tamanho do vídeo (1240×2204 para 1080×1920): é a folga do `.bgimg`. Para outro formato, passe `--w` e `--h`.
- `madeira` transforma **qualquer** foto de madeira (até bambu claro) na nogueira escura e quente da referência. Use `--girar` para os veios ficarem na vertical no 9:16.
- `papel`, `tecido` e `mesa` aceitam `--cor r,g,b` para mudar o tom.

## 5. Tamanhos de arquivo

Recorte grande pode ter até ~1,6× a largura em que aparece; padrões e adesivos, até 440 px. Fotos inteiras até 1920 px. Imagem pesada deixa o render lento sem ganho visível.
