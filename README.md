# Recorte.ai

Aplicativo desktop para Windows que remove o fundo de imagens com inteligência
artificial, **100% local** — nenhuma imagem sai do seu computador.

Três passos: selecionar → remover fundo → salvar PNG transparente.

---

## Recursos

- Seleção por clique **ou arrastar e soltar** (arquivos ou pastas inteiras)
- Formatos aceitos: **PNG, JPG, JPEG, WEBP**
- Pré-visualização **antes / depois** lado a lado, com xadrez de transparência
- Modelo `isnet-general-use` com **alpha matting**, e **fallback automático** para `u2net`
- Ajustes: manter resolução, melhorar bordas, suavizar contorno, recorte automático
- **Troca de fundo**: transparente, cor sólida, imagem personalizada ou desfoque do fundo original
- **Pré-visualização ao vivo**: qualquer ajuste (bordas, suavização, fundo, redimensionamento) atualiza
  o resultado instantaneamente, reaproveitando o recorte da IA — sem precisar rodar o modelo de novo
- **Processamento em lote** com progresso ("Imagem 3 de 15…"), cancelamento e pré-visualização ao vivo de cada resultado
- Exportação em **PNG ou WEBP** (com controle de qualidade), preservando a resolução original ou
  **redimensionando para um tamanho máximo**, além de **cópia direta para a área de transferência**
- **Atalhos de teclado**: Ctrl+O selecionar, Enter processar, Ctrl+S salvar, Ctrl+C copiar, Delete limpar
- Layout **responsivo**, com barra lateral de largura **ajustável arrastando a divisória** e rolagem
  interna nos ajustes quando não cabem na tela
- Botões de **Opções** (troca de idioma: português/inglês, fácil de estender) e **Ajuda** no cabeçalho
- Preferências (idioma, largura da barra lateral) salvas entre execuções
- Interface responsiva: todo o processamento roda em thread separada

---

## Instalação

Requer **Python 3.12+**.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Na primeira execução o modelo de IA (~180 MB) é baixado uma única vez para
`~/.u2net`. Depois disso o aplicativo funciona totalmente offline.

## Executar

```bash
python app.py
```

---

## Estrutura do projeto

```text
removedor-fundo-ia/
│
├── app.py                      # ponto de entrada, janela raiz e tratamento global de erros
├── config.py                   # tema, formatos, modelos e dataclasses compartilhadas
├── i18n.py                     # traduções da interface (pt/en) e idioma ativo
├── preferences.py              # idioma e largura da barra lateral, salvos entre execuções
│
├── ui/
│   ├── components.py           # Card, botões, toggles, progresso, status, lista de arquivos
│   ├── preview.py              # painéis "antes/depois" com xadrez de transparência
│   └── main_window.py          # layout responsivo, estados e comunicação com as threads
│
├── services/
│   ├── errors.py               # exceções de domínio com mensagens amigáveis
│   ├── background_remover.py   # sessão do rembg, lazy loading e fallback de modelo
│   ├── image_processor.py      # carregar, validar, refinar bordas, suavizar, recortar, trocar fundo
│   ├── export_service.py       # gravação de PNG e nomes de arquivo sem colisão
│   ├── clipboard.py            # cópia de imagens para a área de transferência do Windows
│   └── pipeline.py             # orquestra o fluxo completo (unitário e em lote)
│
├── assets/
│   ├── icon.ico
│   ├── logo.png
│   └── generate_assets.py      # recria os assets
│
├── requirements.txt
└── app.spec                    # build do executável
```

### Como as camadas se separam

- **`services/`** não importa nada de interface — pode ser usado em scripts ou testes.
- **`ui/`** não contém regra de negócio: apenas dispara o pipeline e reage a eventos.
- A comunicação thread → interface acontece por uma `queue.Queue` lida a cada 80 ms,
  então a janela nunca congela e não há acesso ao Tkinter fora da thread principal.

---

## Uso em script (sem interface)

```python
from pathlib import Path
from config import ProcessingOptions
from services.pipeline import RemovalPipeline

pipeline = RemovalPipeline()
report = pipeline.process_batch(
    paths=Path("fotos").glob("*.jpg"),
    destination_dir=Path("saida"),
    options=ProcessingOptions(auto_crop=True),
    on_progress=lambda i, total, name: print(f"{i}/{total} {name}"),
)
print(f"{report.succeeded} ok, {report.failed} com erro")
```

---

## Gerar o executável

Forma simples:

```bash
pyinstaller --onefile --windowed --icon assets/icon.ico ^
  --collect-all rembg --collect-all onnxruntime --collect-all customtkinter ^
  --collect-all tkinterdnd2 --add-data "assets;assets" app.py
```

Ou usando o spec já pronto (recomendado):

```bash
pyinstaller app.spec
```

O executável fica em `dist/`.

> **Nota:** `--onefile` deixa a inicialização mais lenta porque descompacta tudo
> a cada execução. Para uso diário, remova `--onefile` (ou use `onedir` no spec)
> e o app abre bem mais rápido.

### Gerar o instalador (opcional)

Para distribuir o app como um instalador de verdade (atalho no menu Iniciar,
desinstalador, sem precisar de permissão de administrador):

1. Instale o [Inno Setup](https://jrsoftware.org/isdl.php) (gratuito).
2. Gere `dist/app_gui.exe` primeiro (`pyinstaller app_gui.spec`).
3. Abra `installer.iss` no Inno Setup Compiler e clique em **Compile**
   — ou pela linha de comando:
   ```bash
   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
   ```
4. O instalador fica em `Output\Recorte.ai-Setup-1.0.0.exe`.

Ao lançar uma nova versão, atualize `MyAppVersion` em `installer.iss` para
bater com `APP_VERSION` em `config.py`.

---

## Tratamento de erros

Nenhuma falha fecha o aplicativo. Cada situação tem uma mensagem própria:

| Situação | Mensagem |
|---|---|
| Formato não suportado | "Formato não suportado… use PNG, JPG, JPEG ou WEBP" |
| Arquivo corrompido | "O arquivo parece estar corrompido ou incompleto" |
| Falha ao salvar | "Sem permissão para salvar…" / "Verifique o espaço em disco" |
| Modelo de IA | "Não foi possível carregar o modelo de IA…" |
| Erro inesperado | Diálogo genérico + traceback no console; o app segue aberto |

No modo lote, uma imagem com erro **não interrompe** as demais — o resumo final
lista o que falhou.

---

## Próximos passos possíveis

A arquitetura já comporta, sem alterar a interface:

- Histórico/desfazer entre ajustes → aproveitaria o mesmo cache de recorte bruto da pré-visualização ao vivo
- Novos formatos de saída (TIFF) → mais um ramo em `ExportService._save_as`
- Outros modelos de IA (`isnet-anime`, `birefnet`) → parâmetro em `BackgroundRemover`
- Mais idiomas na interface → nova entrada em `i18n._TRANSLATIONS`
