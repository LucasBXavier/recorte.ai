"""Internacionalização simples da interface.

Guarda um dicionário de traduções por idioma e o idioma ativo em memória.
Widgets que precisam ser retextualizados quando o idioma muda (botões,
rótulos fixos etc.) chamam :func:`t` de novo: não há binding automático,
quem monta a interface é responsável por reaplicar os textos (veja
``MainWindow._apply_language``).

Adicionar um novo idioma é só acrescentar uma entrada em ``_TRANSLATIONS``
com as mesmas chaves usadas em ``pt``.
"""

from __future__ import annotations

#: Idiomas disponíveis: código -> nome exibido no seletor.
LANGUAGE_LABELS: dict[str, str] = {
    "pt": "Português",
    "en": "English",
}

_DEFAULT_LANGUAGE = "pt"

_TRANSLATIONS: dict[str, dict[str, str]] = {
    "pt": {
        "app.subtitle": "Remoção de fundo local, sem enviar suas imagens para a internet",
        "header.help_button": "❓ Ajuda",
        "header.settings_button": "⚙ Opções",
        "step1.title": "1 · Escolher",
        "step2.title": "2 · Ajustes",
        "step3.and_save": "e salvar",
        "button.select": "Selecionar imagens",
        "button.clear": "Limpar",
        "button.save_png": "Salvar PNG",
        "button.save_webp": "Salvar WEBP",
        "button.copy": "Copiar imagem",
        "button.cancel": "Cancelar",
        "button.processing": "Processando…",
        "queue.empty": "Nenhuma imagem selecionada",
        "queue.one": "1 imagem na fila",
        "queue.many": "{n} imagens na fila",
        "toggle.keep_resolution.title": "Manter resolução",
        "toggle.keep_resolution.desc": "Preserva o tamanho original",
        "toggle.refine_edges.title": "Melhorar bordas",
        "toggle.refine_edges.desc": "Remove o halo do recorte",
        "toggle.smooth_contour.title": "Suavizar contorno",
        "toggle.smooth_contour.desc": "Deixa as bordas menos serrilhadas",
        "toggle.auto_crop.title": "Recorte automático",
        "toggle.auto_crop.desc": "Corta as áreas transparentes",
        "toggle.resize_on_export.title": "Redimensionar ao exportar",
        "toggle.resize_on_export.desc": "Limita o maior lado da imagem salva",
        "slider.smooth_radius": "Intensidade da suavização",
        "slider.blur_radius": "Intensidade do desfoque",
        "slider.export_quality": "Qualidade do WEBP",
        "slider.export_max_size": "Redimensionar para (px)",
        "export.section_title": "Exportação",
        "bg.section_title": "Fundo do resultado",
        "bg.mode.transparent": "Transparente",
        "bg.mode.color": "Cor sólida",
        "bg.mode.image": "Imagem",
        "bg.mode.blur": "Desfoque",
        "bg.action.transparent": "Remover fundo",
        "bg.action.change": "Trocar fundo",
        "bg.action.blur": "Desfocar fundo",
        "bg.color_button.default": "Escolher cor de fundo",
        "bg.color_button.chosen": "Cor de fundo: {hex}",
        "bg.image_button.default": "Escolher imagem de fundo",
        "bg.image_button.chosen": "Fundo: {name}",
        "status.ready": "Pronto",
        "status.processing_file": "Processando {name}…",
        "status.processing_ai": "Processando com IA…",
        "status.batch_preparing": "Preparando o lote…",
        "status.batch_processing": "Processando {n} imagens…",
        "progress.item": "Imagem {current} de {total} · {name}",
        "status.cancelling": "Cancelando após a imagem atual…",
        "status.loaded": "{name} carregada.",
        "status.ignored_files": "{n} arquivo(s) ignorado(s) por formato não suportado.",
        "status.adjust_changed": "Ajuste alterado. Clique em “{action}” para aplicar.",
        "status.single_done": "Pronto! Clique em “{save}” para salvar.",
        "status.batch_success": "{ok} imagem(ns) salva(s) em {dest}",
        "status.batch_partial": "{ok} concluída(s), {fail} com erro.",
        "status.saved": "Salvo em {path}",
        "status.copied": "Imagem copiada para a área de transferência.",
        "status.update_available": "Nova versão disponível: v{version}",
        "status.model_ready": "Modelo de IA pronto ({model}).",
        "status.model_pending": "Modelo de IA será carregado no primeiro uso.",
        "error.unexpected_processing": "Ocorreu um erro inesperado durante o processamento.",
        "error.unexpected_batch": "Ocorreu um erro inesperado durante o lote.",
        "error.generic_title": "Ops, algo deu errado",
        "error.generic_body": "Ocorreu um erro inesperado.\n\n{type}: {error}",
        "error.invalid_image_title": "Imagem inválida",
        "error.corrupted_file_title": "Arquivo corrompido",
        "error.model_title": "Erro no modelo de IA",
        "error.export_title": "Erro ao salvar",
        "error.clipboard_title": "Erro ao copiar",
        "error.file_not_found": "O arquivo não foi encontrado:\n{name}",
        "error.unsupported_format": (
            "Formato não suportado: {ext}.\nUse um destes formatos: {supported}."
        ),
        "error.corrupted_unreadable": (
            "Não foi possível ler a imagem:\n{name}\n"
            "O arquivo pode estar corrompido ou não ser uma imagem válida."
        ),
        "error.corrupted_incomplete": "O arquivo parece estar corrompido ou incompleto:\n{name}",
        "error.rembg_missing": (
            "A biblioteca de IA (rembg) não está instalada.\n"
            "Execute: pip install -r requirements.txt"
        ),
        "error.model_load_failed": (
            "Não foi possível carregar o modelo de IA.\n"
            "Verifique sua conexão na primeira execução. O modelo é "
            "baixado uma única vez."
        ),
        "error.inference_failed": (
            "O modelo de IA não conseguiu processar esta imagem.\n"
            "Tente novamente ou use outra imagem."
        ),
        "error.unexpected_result": "O modelo de IA devolveu um resultado inesperado.",
        "error.export_mkdir_failed": "Não foi possível criar a pasta de destino:\n{folder}",
        "error.export_permission": (
            "Sem permissão para salvar em:\n{path}\n"
            "Feche o arquivo se ele estiver aberto ou escolha outra pasta."
        ),
        "error.export_os_error": (
            "Não foi possível salvar a imagem:\n{name}\n"
            "Verifique o espaço em disco e tente novamente."
        ),
        "error.clipboard_alloc": "Não foi possível alocar memória para copiar a imagem.",
        "error.clipboard_lock": "Não foi possível preparar os dados para a área de transferência.",
        "error.clipboard_open": (
            "Não foi possível abrir a área de transferência.\n"
            "Feche outros programas que possam estar usando-a e tente novamente."
        ),
        "error.clipboard_copy_failed": "Não foi possível copiar a imagem para a área de transferência.",
        "dialog.no_valid_images.title": "Nenhuma imagem válida",
        "dialog.no_valid_images.body": (
            "Não encontrei imagens suportadas nos itens selecionados.\n\n"
            "Formatos aceitos: {formats}."
        ),
        "dialog.batch_done.title": "Lote concluído",
        "dialog.batch_done.body": "{ok} imagem(ns) processada(s) com sucesso.\n\nPasta: {dest}",
        "dialog.batch_warning.title": "Lote concluído com avisos",
        "dialog.batch_warning.body": (
            "{ok} de {total} imagens foram salvas em:\n{dest}\n\n"
            "Não foi possível processar:\n{preview}{extra}"
        ),
        "dialog.batch_warning.extra": "\n… e mais {n}.",
        "filedialog.select_images": "Selecione uma ou mais imagens",
        "filedialog.choose_destination": "Escolha a pasta onde salvar as imagens processadas",
        "filedialog.save_image": "Salvar imagem",
        "filedialog.choose_color": "Escolha a cor de fundo",
        "filedialog.choose_image": "Escolha a imagem de fundo",
        "filedialog.images_label": "Imagens",
        "filedialog.all_files_label": "Todos os arquivos",
        "preview.before_title": "Antes",
        "preview.before_placeholder": "Arraste uma imagem aqui\nou clique em “{select}”",
        "preview.after_title": "Depois",
        "preview.after_placeholder": "O resultado aparece aqui",
        "settings.title": "Opções",
        "settings.language_label": "Idioma",
        "settings.close": "Fechar",
        "help.title": "Ajuda",
        "help.credit_prefix": "Desenvolvido por",
        "help.body": (
            "Como usar:\n"
            "1. Selecione imagens (clique ou arraste e solte).\n"
            "2. Ajuste as opções: recorte, bordas e fundo (transparente, cor, "
            "imagem ou desfoque).\n"
            "3. Clique no botão de ação para processar e salvar, ou copie o "
            "resultado direto para a área de transferência.\n\n"
            "Dicas:\n"
            "• Arraste a divisória entre a barra lateral e a pré-visualização "
            "para redimensionar a janela.\n"
            "• Selecione várias imagens para processar em lote; clique em "
            "cada uma na fila para ver o resultado.\n"
            "• Nenhuma imagem sai do seu computador: todo o processamento é local.\n\n"
            "Atalhos de teclado:\n"
            "Ctrl+O selecionar · Enter processar · Ctrl+S salvar · "
            "Ctrl+C copiar · Delete limpar"
        ),
    },
    "en": {
        "app.subtitle": "Local background removal: your images never leave your computer",
        "header.help_button": "❓ Help",
        "header.settings_button": "⚙ Options",
        "step1.title": "1 · Choose",
        "step2.title": "2 · Adjustments",
        "step3.and_save": "and save",
        "button.select": "Select images",
        "button.clear": "Clear",
        "button.save_png": "Save PNG",
        "button.save_webp": "Save WEBP",
        "button.copy": "Copy image",
        "button.cancel": "Cancel",
        "button.processing": "Processing…",
        "queue.empty": "No image selected",
        "queue.one": "1 image queued",
        "queue.many": "{n} images queued",
        "toggle.keep_resolution.title": "Keep resolution",
        "toggle.keep_resolution.desc": "Preserves the original size",
        "toggle.refine_edges.title": "Improve edges",
        "toggle.refine_edges.desc": "Removes the halo left around the cutout",
        "toggle.smooth_contour.title": "Smooth outline",
        "toggle.smooth_contour.desc": "Makes edges less jagged",
        "toggle.auto_crop.title": "Auto crop",
        "toggle.auto_crop.desc": "Trims the transparent areas",
        "toggle.resize_on_export.title": "Resize on export",
        "toggle.resize_on_export.desc": "Caps the longest side of the saved image",
        "slider.smooth_radius": "Smoothing intensity",
        "slider.blur_radius": "Blur intensity",
        "slider.export_quality": "WEBP quality",
        "slider.export_max_size": "Resize to (px)",
        "export.section_title": "Export",
        "bg.section_title": "Result background",
        "bg.mode.transparent": "Transparent",
        "bg.mode.color": "Solid color",
        "bg.mode.image": "Image",
        "bg.mode.blur": "Blur",
        "bg.action.transparent": "Remove background",
        "bg.action.change": "Change background",
        "bg.action.blur": "Blur background",
        "bg.color_button.default": "Choose background color",
        "bg.color_button.chosen": "Background color: {hex}",
        "bg.image_button.default": "Choose background image",
        "bg.image_button.chosen": "Background: {name}",
        "status.ready": "Ready",
        "status.processing_file": "Processing {name}…",
        "status.processing_ai": "Processing with AI…",
        "status.batch_preparing": "Preparing the batch…",
        "status.batch_processing": "Processing {n} images…",
        "progress.item": "Image {current} of {total} · {name}",
        "status.cancelling": "Cancelling after the current image…",
        "status.loaded": "{name} loaded.",
        "status.ignored_files": "{n} file(s) ignored due to unsupported format.",
        "status.adjust_changed": "Setting changed. Click “{action}” to apply.",
        "status.single_done": "Done! Click “{save}” to save.",
        "status.batch_success": "{ok} image(s) saved to {dest}",
        "status.batch_partial": "{ok} completed, {fail} failed.",
        "status.saved": "Saved to {path}",
        "status.copied": "Image copied to the clipboard.",
        "status.update_available": "New version available: v{version}",
        "status.model_ready": "AI model ready ({model}).",
        "status.model_pending": "The AI model will load on first use.",
        "error.unexpected_processing": "An unexpected error occurred while processing.",
        "error.unexpected_batch": "An unexpected error occurred during the batch.",
        "error.generic_title": "Something went wrong",
        "error.generic_body": "An unexpected error occurred.\n\n{type}: {error}",
        "error.invalid_image_title": "Invalid image",
        "error.corrupted_file_title": "Corrupted file",
        "error.model_title": "AI model error",
        "error.export_title": "Save error",
        "error.clipboard_title": "Copy error",
        "error.file_not_found": "The file was not found:\n{name}",
        "error.unsupported_format": (
            "Unsupported format: {ext}.\nUse one of these formats: {supported}."
        ),
        "error.corrupted_unreadable": (
            "Could not read the image:\n{name}\n"
            "The file may be corrupted or not a valid image."
        ),
        "error.corrupted_incomplete": "The file appears to be corrupted or incomplete:\n{name}",
        "error.rembg_missing": (
            "The AI library (rembg) is not installed.\n"
            "Run: pip install -r requirements.txt"
        ),
        "error.model_load_failed": (
            "Could not load the AI model.\n"
            "Check your connection on first run: the model is downloaded only once."
        ),
        "error.inference_failed": (
            "The AI model could not process this image.\n"
            "Try again or use a different image."
        ),
        "error.unexpected_result": "The AI model returned an unexpected result.",
        "error.export_mkdir_failed": "Could not create the destination folder:\n{folder}",
        "error.export_permission": (
            "No permission to save to:\n{path}\n"
            "Close the file if it's open elsewhere, or choose another folder."
        ),
        "error.export_os_error": (
            "Could not save the image:\n{name}\n"
            "Check your disk space and try again."
        ),
        "error.clipboard_alloc": "Could not allocate memory to copy the image.",
        "error.clipboard_lock": "Could not prepare the data for the clipboard.",
        "error.clipboard_open": (
            "Could not open the clipboard.\n"
            "Close other programs that might be using it and try again."
        ),
        "error.clipboard_copy_failed": "Could not copy the image to the clipboard.",
        "dialog.no_valid_images.title": "No valid images",
        "dialog.no_valid_images.body": (
            "No supported images were found in the selected items.\n\n"
            "Accepted formats: {formats}."
        ),
        "dialog.batch_done.title": "Batch complete",
        "dialog.batch_done.body": "{ok} image(s) processed successfully.\n\nFolder: {dest}",
        "dialog.batch_warning.title": "Batch completed with warnings",
        "dialog.batch_warning.body": (
            "{ok} of {total} images were saved to:\n{dest}\n\n"
            "Could not process:\n{preview}{extra}"
        ),
        "dialog.batch_warning.extra": "\n… and {n} more.",
        "filedialog.select_images": "Select one or more images",
        "filedialog.choose_destination": "Choose the folder to save the processed images",
        "filedialog.save_image": "Save image",
        "filedialog.choose_color": "Choose the background color",
        "filedialog.choose_image": "Choose the background image",
        "filedialog.images_label": "Images",
        "filedialog.all_files_label": "All files",
        "preview.before_title": "Before",
        "preview.before_placeholder": "Drag an image here\nor click “{select}”",
        "preview.after_title": "After",
        "preview.after_placeholder": "The result appears here",
        "settings.title": "Options",
        "settings.language_label": "Language",
        "settings.close": "Close",
        "help.title": "Help",
        "help.credit_prefix": "Developed by",
        "help.body": (
            "How to use it:\n"
            "1. Select images (click or drag and drop).\n"
            "2. Adjust the options: crop, edges and background (transparent, "
            "color, image or blur).\n"
            "3. Click the action button to process and save, or copy the "
            "result straight to the clipboard.\n\n"
            "Tips:\n"
            "• Drag the divider between the sidebar and the preview to "
            "resize the window.\n"
            "• Select several images to process them in batch; click each "
            "one in the queue to see its result.\n"
            "• No image ever leaves your computer: all processing is local.\n\n"
            "Keyboard shortcuts:\n"
            "Ctrl+O select · Enter process · Ctrl+S save · "
            "Ctrl+C copy · Delete clear"
        ),
    },
}

_current_language = _DEFAULT_LANGUAGE


def set_language(code: str) -> None:
    """Define o idioma ativo da interface.

    Args:
        code: Código do idioma (``"pt"`` ou ``"en"``). Códigos desconhecidos
            são ignorados silenciosamente.
    """
    global _current_language
    if code in _TRANSLATIONS:
        _current_language = code


def get_language() -> str:
    """Retorna o código do idioma atualmente ativo."""
    return _current_language


def t(key: str, **kwargs: object) -> str:
    """Traduz uma chave para o idioma ativo.

    Args:
        key: Chave de tradução (ex.: ``"button.save"``).
        **kwargs: Valores para interpolar no texto (ex.: ``name="foto.jpg"``).

    Returns:
        Texto traduzido, com os valores já interpolados. Cai para o
        português se a chave não existir no idioma ativo, e para a própria
        chave como último recurso.
    """
    table = _TRANSLATIONS.get(_current_language, _TRANSLATIONS[_DEFAULT_LANGUAGE])
    text = table.get(key, _TRANSLATIONS[_DEFAULT_LANGUAGE].get(key, key))
    if not kwargs:
        return text
    try:
        return text.format(**kwargs)
    except (KeyError, IndexError):
        return text
