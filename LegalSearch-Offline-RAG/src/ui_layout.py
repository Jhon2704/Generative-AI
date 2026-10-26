from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from logging_setup import get_logger, setup_logging
from utils import get_app_data_dir


def get_stylesheet() -> str:
    return """
QMainWindow { background: #f4f1ec; }
QWidget { color: #1d1b19; font-family: 'Segoe UI', 'Arial', sans-serif; font-size: 13px; }
QFrame#Sidebar { background: #f7f3ed; border-right: 1px solid #ddd3c8; }
QFrame#Card { background: #ffffff; border: 1px solid #e1d8cd; border-radius: 14px; }
QLabel#BrandTitle { font-size: 22px; font-weight: 700; }
QLabel#BrandSubtitle { color: #5b544d; font-size: 13px; }
QPushButton#NavButton { text-align: left; padding: 10px 12px; border-radius: 10px; border: 1px solid #d9cec2; background: #ffffff; font-weight: 600; }
QPushButton#NavButton:hover { background: #f4ece2; }
QPushButton#NavButton:checked { background: #e7f0f9; border: 1px solid #7ea2c7; }
QPushButton#PrimaryButton { background: #20384e; color: #ffffff; border: 1px solid #1b3145; border-radius: 10px; padding: 10px 14px; font-weight: 700; }
QPushButton#PrimaryButton:hover { background: #2f4d6b; }
QPushButton#SecondaryButton { background: #fff8f0; color: #473a2e; border: 1px solid #cdbda9; border-radius: 10px; padding: 10px 14px; font-weight: 600; }
QPushButton#SecondaryButton:hover { background: #f8eddf; }
QLineEdit { background: #ffffff; border: 1px solid #d6cbc0; border-radius: 10px; padding: 12px; font-size: 14px; }
QLineEdit:focus { border: 1px solid #7f9db8; }
QTextEdit { background: #ffffff; border: 1px solid #e1d8cd; border-radius: 10px; padding: 10px; }
QListWidget, QTableWidget { background: #ffffff; border: 1px solid #e1d8cd; border-radius: 10px; }
QHeaderView::section { background: #f1e9df; border: none; border-bottom: 1px solid #e1d8cd; padding: 8px; font-weight: 700; }
QStatusBar { background: #efe7dc; border-top: 1px solid #d9cec2; }
"""


def apply_shadow(widget: QWidget, blur: float = 24.0, y_offset: float = 4.0) -> None:
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setXOffset(0)
    shadow.setYOffset(y_offset)
    shadow.setColor(Qt.black)
    widget.setGraphicsEffect(shadow)


class MainWindow(QMainWindow):
    def __init__(self, adapter: Any) -> None:
        super().__init__()
        setup_logging()
        self.logger = get_logger("ui_layout")
        self.adapter = adapter
        self.current_sources: list[dict[str, Any]] = []
        self.documents_cache: list[dict[str, Any]] = []
        self.app_dir = get_app_data_dir("LegalSearchOffline")
        self._has_docs = False
        self._has_index = False
        self._is_busy = False

        self.setWindowTitle("LegalSearch Offline - Qt")
        self.resize(1300, 820)
        self.setStyleSheet(get_stylesheet())
        self._build_ui()
        self._connect_signals()
        self.adapter.initialize()

    def _build_ui(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)
        main_layout = QHBoxLayout(root)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = self._build_sidebar()
        main_layout.addWidget(self.sidebar)

        self.stack = QStackedWidget(self)
        self.stack.setContentsMargins(16, 16, 16, 16)
        main_layout.addWidget(self.stack, 1)

        self.search_page = self._build_search_page()
        self.documents_page = self._build_documents_page()
        self.stack.addWidget(self.search_page)
        self.stack.addWidget(self.documents_page)

        self.status = QStatusBar(self)
        self.setStatusBar(self.status)
        self.status_mode = QLabel("Modo: offline")
        self.status_db = QLabel("DB: NO")
        self.status_ollama = QLabel("Ollama: NO")
        self.status_model = QLabel("Modelo: phi3:mini")
        self.status.addPermanentWidget(self.status_mode)
        self.status.addPermanentWidget(self.status_db)
        self.status.addPermanentWidget(self.status_ollama)
        self.status.addPermanentWidget(self.status_model)

        self.nav_search.setChecked(True)
        self.stack.setCurrentIndex(0)

    def _build_sidebar(self) -> QWidget:
        panel = QFrame(self)
        panel.setObjectName("Sidebar")
        panel.setFixedWidth(320)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("LegalSearch Offline", panel)
        title.setObjectName("BrandTitle")
        subtitle = QLabel("Buscador legal privado sin nube", panel)
        subtitle.setObjectName("BrandSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.nav_search = QPushButton("Buscar", panel)
        self.nav_search.setObjectName("NavButton")
        self.nav_search.setCheckable(True)
        self.nav_docs = QPushButton("Mis documentos", panel)
        self.nav_docs.setObjectName("NavButton")
        self.nav_docs.setCheckable(True)
        layout.addWidget(self.nav_search)
        layout.addWidget(self.nav_docs)

        self.index_card = QFrame(panel)
        self.index_card.setObjectName("Card")
        apply_shadow(self.index_card, blur=18.0, y_offset=3.0)
        index_layout = QVBoxLayout(self.index_card)
        index_layout.setContentsMargins(12, 12, 12, 12)
        index_layout.setSpacing(6)
        index_layout.addWidget(QLabel("Estado del indice", self.index_card))
        self.index_state = QLabel("Estado: Sin indice", self.index_card)
        self.index_docs = QLabel("Documentos indexados: 0", self.index_card)
        index_layout.addWidget(self.index_state)
        index_layout.addWidget(self.index_docs)

        self.btn_rebuild = QPushButton("Reconstruir indice", panel)
        self.btn_rebuild.setObjectName("SecondaryButton")
        self.btn_rebuild.setEnabled(False)

        self.btn_import_files = QPushButton("Importar archivos", panel)
        self.btn_import_files.setObjectName("SecondaryButton")
        self.btn_import_folder = QPushButton("Importar carpeta", panel)
        self.btn_import_folder.setObjectName("SecondaryButton")
        self.storage_hint = QLabel(f"Se guardan en:\n{self.app_dir / 'documents'}", panel)
        self.storage_hint.setStyleSheet("color:#5b544d;font-size:12px;")
        self.storage_hint.setWordWrap(True)

        layout.addWidget(self.index_card)
        layout.addWidget(self.btn_rebuild)
        layout.addWidget(self.btn_import_files)
        layout.addWidget(self.btn_import_folder)
        layout.addWidget(self.storage_hint)
        layout.addStretch(1)
        return panel

    def _build_search_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        card = QFrame(page)
        card.setObjectName("Card")
        apply_shadow(card)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(6)
        title = QLabel("Busqueda legal", card)
        title.setStyleSheet("font-size: 26px; font-weight: 700;")
        card_layout.addWidget(title)
        card_layout.addWidget(QLabel("Consulta tus documentos locales con RAG offline.", card))

        row = QHBoxLayout()
        self.search_input = QLineEdit(page)
        self.search_input.setPlaceholderText("Ej: Clausulas de terminacion anticipada...")
        self.search_input.setMinimumHeight(44)
        self.btn_search = QPushButton("Buscar", page)
        self.btn_search.setObjectName("PrimaryButton")
        self.btn_search.setMinimumHeight(44)
        self.btn_search.setEnabled(False)
        self.btn_summary = QPushButton("Resumen", page)
        self.btn_summary.setObjectName("SecondaryButton")
        self.btn_summary.setMinimumHeight(44)
        self.btn_summary.setEnabled(False)
        row.addWidget(self.search_input, 1)
        row.addWidget(self.btn_search)
        row.addWidget(self.btn_summary)

        answer_card = QFrame(page)
        answer_card.setObjectName("Card")
        apply_shadow(answer_card)
        answer_layout = QVBoxLayout(answer_card)
        answer_layout.setContentsMargins(14, 14, 14, 14)
        self.response_text = QTextEdit(answer_card)
        self.response_text.setReadOnly(True)
        self.response_text.setPlaceholderText("La respuesta aparecera aqui.")
        self.sources_list = QListWidget(answer_card)
        self.sources_list.setMinimumHeight(130)
        answer_layout.addWidget(QLabel("Respuesta", answer_card))
        answer_layout.addWidget(self.response_text)
        answer_layout.addWidget(QLabel("Fuentes / Documentos usados", answer_card))
        answer_layout.addWidget(self.sources_list)

        layout.addWidget(card)
        layout.addLayout(row)
        layout.addWidget(answer_card, 1)
        return page

    def _build_documents_page(self) -> QWidget:
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        card = QFrame(page)
        card.setObjectName("Card")
        apply_shadow(card)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 14, 14, 14)
        card_layout.setSpacing(8)
        card_layout.addWidget(QLabel("Mis documentos", card))

        self.documents_table = QTableWidget(0, 6, card)
        self.documents_table.setHorizontalHeaderLabels(
            ["Nombre", "Ext", "KB", "Modificado", "Ruta", "Accion"]
        )
        self.documents_table.horizontalHeader().setStretchLastSection(True)
        self.documents_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.documents_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.documents_table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        row = QHBoxLayout()
        self.refresh_docs_button = QPushButton("Refrescar", card)
        self.refresh_docs_button.setObjectName("SecondaryButton")
        self.open_doc_button = QPushButton("Abrir seleccionado", card)
        self.open_doc_button.setObjectName("SecondaryButton")
        self.delete_doc_button = QPushButton("Eliminar seleccionado", card)
        self.delete_doc_button.setObjectName("PrimaryButton")
        self.delete_doc_button.setStyleSheet(
            "QPushButton#PrimaryButton { background: #8b1a1a; border-color: #6e1515; }"
            "QPushButton#PrimaryButton:hover { background: #a82020; }"
        )
        row.addWidget(self.refresh_docs_button)
        row.addWidget(self.open_doc_button)
        row.addWidget(self.delete_doc_button)
        row.addStretch(1)

        card_layout.addWidget(self.documents_table, 1)
        card_layout.addLayout(row)
        layout.addWidget(card, 1)
        return page

    def _connect_signals(self) -> None:
        self.nav_search.clicked.connect(self._go_search_page)
        self.nav_docs.clicked.connect(self._go_docs_page)

        # Conexiones obligatorias de acciones principales.
        self.btn_rebuild.clicked.connect(self._on_rebuild_index)
        self.btn_import_files.clicked.connect(self._on_import_files)
        self.btn_import_folder.clicked.connect(self._on_import_folder)
        self.btn_search.clicked.connect(self._on_search)
        self.btn_summary.clicked.connect(self._on_summary)

        self.refresh_docs_button.clicked.connect(self.adapter.refresh_documents)
        self.open_doc_button.clicked.connect(self._open_selected_document)
        self.delete_doc_button.clicked.connect(self._on_delete_document)
        self.sources_list.itemDoubleClicked.connect(self._open_source_item)

        self.adapter.error.connect(self._on_error)
        if hasattr(self.adapter, "info"):
            self.adapter.info.connect(self._on_info)
        self.adapter.busy.connect(self._on_busy_changed)
        self.adapter.index_status_changed.connect(self._on_index_status_changed)
        self.adapter.doc_count_changed.connect(self._on_doc_count_changed)
        self.adapter.search_finished.connect(self._on_search_finished)
        self.adapter.summary_finished.connect(self._on_summary_finished)
        self.adapter.ollama_status_changed.connect(self._on_ollama_status_changed)
        self.adapter.db_status_changed.connect(self._on_db_status_changed)

        self.adapter.documents_listed.connect(self._on_documents_listed)
        self.adapter.import_finished.connect(self._on_import_finished)
        if hasattr(self.adapter, "system_status"):
            self.adapter.system_status.connect(self._on_system_status)

        quick_action = QAction("Buscar", self)
        quick_action.setShortcut("Return")
        quick_action.triggered.connect(self._on_search)
        self.addAction(quick_action)

    def _go_search_page(self) -> None:
        self._set_page(0)

    def _go_docs_page(self) -> None:
        self._set_page(1)

    def _set_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        self.nav_search.setChecked(index == 0)
        self.nav_docs.setChecked(index == 1)

    def _on_import_files(self) -> None:
        print("DEBUG: clicked import_files")
        self.logger.info("click _on_import_files")
        self.status.showMessage("Abriendo dialogo: importar archivos...", 2500)
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Importar archivos",
            str(Path.home()),
            "Documents (*.pdf *.docx *.txt *.md)",
        )
        if file_paths:
            self.adapter.import_files(file_paths)
        else:
            self.status.showMessage("Importacion cancelada por el usuario.", 2500)

    def _on_import_folder(self) -> None:
        print("DEBUG: clicked import_folder")
        self.logger.info("click _on_import_folder")
        self.status.showMessage("Abriendo dialogo: importar carpeta...", 2500)
        folder = QFileDialog.getExistingDirectory(self, "Importar carpeta", str(Path.home()))
        if folder:
            self.adapter.import_folder(folder)
        else:
            self.status.showMessage("Importacion de carpeta cancelada.", 2500)

    def _on_rebuild_index(self) -> None:
        print("DEBUG: clicked rebuild_index")
        self.logger.info("click _on_rebuild_index")
        self.status.showMessage("Ejecutando: reconstruir indice...", 2500)
        self.adapter.rebuild_index()

    def _on_search(self) -> None:
        if self._is_busy:
            return
        print("DEBUG: clicked search")
        self.logger.info("click _on_search")
        self.status.showMessage("Ejecutando: buscar...", 2500)
        query = self.search_input.text().strip()
        self.adapter.run_search(query)

    def _on_summary(self) -> None:
        if self._is_busy:
            return
        print("DEBUG: _on_summary called")
        self.logger.info("click _on_summary")
        self.status.showMessage("Ejecutando: resumen...", 2500)
        query = self.search_input.text().strip()
        self.adapter.run_summary(query)

    def _update_button_states(self) -> None:
        self.btn_import_files.setEnabled(True)
        self.btn_import_folder.setEnabled(True)
        self.btn_rebuild.setEnabled(self._has_docs and not self._is_busy)
        self.btn_search.setEnabled(self._has_index and not self._is_busy)
        self.btn_summary.setEnabled(self._has_index and not self._is_busy)
        self.refresh_docs_button.setEnabled(not self._is_busy)
        self.open_doc_button.setEnabled(not self._is_busy)
        self.delete_doc_button.setEnabled(not self._is_busy)

    def _on_index_status_changed(self, status: str) -> None:
        self.index_state.setText(f"Estado: {status}")
        self.status.showMessage(status, 3000)
        self._has_index = status == "Listo"
        self._update_button_states()

    def _on_doc_count_changed(self, count: int) -> None:
        self.index_docs.setText(f"Documentos indexados: {count}")
        self._has_docs = count > 0
        self._update_button_states()

    def _on_ollama_status_changed(self, ok: bool, message: str) -> None:
        self.status_ollama.setText(f"Ollama: {'OK' if ok else 'NO'}")
        if message:
            self.status.showMessage(message, 5000)

    def _on_db_status_changed(self, ok: bool, message: str) -> None:
        self.status_db.setText(f"DB: {'OK' if ok else 'NO'}")
        if message:
            self.status.showMessage(f"DB: {message}", 3000)

    def _on_search_finished(self, answer: str, sources: list) -> None:
        self.logger.info("search_finished received answer_len=%s sources=%s", len(answer or ""), len(sources or []))
        self.response_text.setPlainText(answer)
        self.sources_list.clear()
        self.current_sources = list(sources or [])
        if not self.current_sources:
            self.sources_list.addItem("Sin fuentes para mostrar.")
            self.status.showMessage("Busqueda finalizada sin fuentes.", 3500)
            return

        for src in self.current_sources:
            source = str(src.get("source", "desconocido"))
            page = str(src.get("page", "-"))
            score = str(src.get("score", "-"))
            item = QListWidgetItem(f"{source}  pag {page}  score {score}")
            item.setData(Qt.UserRole, src)
            self.sources_list.addItem(item)
        self.status.showMessage(f"Busqueda finalizada. Fuentes: {len(self.current_sources)}", 3500)

    def _on_summary_finished(self, summary: str) -> None:
        self.response_text.setPlainText(summary)
        self.status.showMessage("Resumen generado.", 3000)

    def _on_documents_listed(self, docs: list[dict[str, Any]]) -> None:
        self.documents_cache = docs
        self.documents_table.setRowCount(len(docs))
        for row, doc in enumerate(docs):
            self.documents_table.setItem(row, 0, QTableWidgetItem(str(doc.get("name", ""))))
            self.documents_table.setItem(row, 1, QTableWidgetItem(str(doc.get("ext", ""))))
            self.documents_table.setItem(row, 2, QTableWidgetItem(str(doc.get("size_kb", ""))))
            self.documents_table.setItem(row, 3, QTableWidgetItem(str(doc.get("modified", ""))))
            self.documents_table.setItem(row, 4, QTableWidgetItem(str(doc.get("path", ""))))
            button = QPushButton("Abrir")
            button.setObjectName("SecondaryButton")
            button.setProperty("doc_path", str(doc.get("path", "")))
            button.clicked.connect(self._open_path_from_button)
            self.documents_table.setCellWidget(row, 5, button)
        self.documents_table.resizeColumnsToContents()

    def _open_path_from_button(self) -> None:
        sender = self.sender()
        if isinstance(sender, QPushButton):
            self._open_path(str(sender.property("doc_path") or ""))

    def _on_import_finished(self, payload: dict[str, int]) -> None:
        imported = int(payload.get("imported", 0))
        failed = int(payload.get("failed", 0))
        self.status.showMessage(f"Importados: {imported} | Fallidos: {failed}", 5000)
        if imported > 0:
            QMessageBox.information(
                self,
                "Importacion completada",
                f"Importados: {imported} | Fallidos: {failed}",
            )

    def _on_system_status(self, payload: dict[str, Any]) -> None:
        self.status_mode.setText(f"Modo: {payload.get('mode', 'offline')}")
        self.status_model.setText(f"Modelo: {payload.get('model', 'phi3:mini')}")

    def _selected_document_path(self) -> str:
        selected = self.documents_table.selectedItems()
        if not selected:
            return ""
        row = selected[0].row()
        path_item = self.documents_table.item(row, 4)
        return path_item.text().strip() if path_item else ""

    def _open_source_item(self, item: QListWidgetItem) -> None:
        source = item.data(Qt.UserRole)
        if not isinstance(source, dict):
            return
        path = str(source.get("path", "")).strip()
        if path:
            self._open_path(path)

    def _open_selected_document(self) -> None:
        self._open_path(self._selected_document_path())

    def _open_path(self, path: str) -> None:
        if not path:
            self._on_error("Selecciona un documento para abrir.")
            return
        if not Path(path).is_file():
            self._on_error(f"No existe el archivo: {path}")
            return
        if not QDesktopServices.openUrl(QUrl.fromLocalFile(path)):
            self._on_error("No se pudo abrir el documento seleccionado.")

    def _on_delete_document(self) -> None:
        path = self._selected_document_path()
        if not path:
            self._on_error("Selecciona un documento de la lista para eliminar.")
            return
        name = Path(path).name
        confirm = QMessageBox.question(
            self,
            "Confirmar eliminacion",
            f"¿Eliminar '{name}'?\n\nEsta accion no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        self.adapter.delete_document(path)

    def _on_error(self, message: str) -> None:
        clean = message.strip().splitlines()[0]
        self.logger.error("ui error: %s", clean)
        self.status.showMessage(clean, 6000)
        QMessageBox.critical(self, "Error", clean)

    def _on_info(self, message: str) -> None:
        clean = message.strip().splitlines()[0]
        self.logger.info("ui info: %s", clean)
        self.status.showMessage(clean, 4000)
        QMessageBox.information(self, "Info", clean)

    def _on_busy_changed(self, busy: bool, message: str) -> None:
        self.logger.info("busy changed busy=%s message=%s", busy, message)
        self.status.showMessage(message if busy else "Listo", 2500)
        self._is_busy = busy
        self._update_button_states()
        self.nav_search.setEnabled(True)
        self.nav_docs.setEnabled(True)
