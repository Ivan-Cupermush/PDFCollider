# mypy: disable-error-code="assignment"
# ruff: noqa: RUF100
"""Photo to PDF Editor with perspective correction and batch processing.

This module provides a GUI application for loading images, applying
geometric transformations (rotation, flip, perspective correction),
resizing, and exporting to a single PDF file.
"""

import math
import os
import sys
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageOps
from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRectF,
    Qt,
    QThread,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QImage,
    QKeyEvent,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
    QShortcut,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)
from reportlab.pdfgen import canvas

# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------
DEFAULT_THEME = "Dark"
SUPPORTED_IMAGE_EXTENSIONS = "*.jpg *.jpeg *.png *.bmp *.tiff"
RESIZE_OPTIONS = ["Оригинал", "4K (3840x2160)", "2K (2560x1440)", "Full HD (1920x1080)"]
RESIZE_DIMENSIONS = {
    "4K": (3840, 2160),
    "2K": (2560, 1440),
    "Full HD": (1920, 1080),
}


# ----------------------------------------------------------------------
# Background thread for saving PDF without freezing GUI
# ----------------------------------------------------------------------
class PDFSaver(QThread):
    """Generates PDF in a separate thread to keep the UI responsive."""

    finished = Signal(str)  # emits PDF path on success
    error = Signal(str)  # emits error message

    def __init__(
        self,
        image_paths: list[str],
        base_images: dict[str, Image.Image],
        edited_images: dict[str, Image.Image],
        pdf_path: str,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the PDF saver thread.

        Args:
            image_paths: Ordered list of image file paths.
            base_images: Dictionary of original images keyed by path.
            edited_images: Dictionary of edited images keyed by path.
            pdf_path: Destination path for the PDF file.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self.image_paths = list(image_paths)
        self.base_images = base_images
        self.edited_images = edited_images
        self.pdf_path = pdf_path

    def run(self) -> None:  # noqa
        """Execute PDF generation in the background."""
        try:
            c = canvas.Canvas(self.pdf_path)
            for path in self.image_paths:
                # Get the image (edited or original)
                img: Image.Image | None = None
                if path in self.edited_images:
                    img = self.edited_images[path]
                else:
                    img = self.base_images.get(path)
                    if img is None:
                        img = Image.open(path)
                        img = ImageOps.exif_transpose(img)
                        img = PhotoToPDFEditor.ensure_rgb(img)

                if img is None:
                    continue  # should not happen, but satisfies type checker

                # Ensure RGB mode
                if img.mode != "RGB":
                    img = img.convert("RGB")

                w, h = img.size
                c.setPageSize((w, h))
                # Direct embedding – no temporary files!
                c.drawInlineImage(img, 0, 0, width=w, height=h)
                c.showPage()

            c.save()
            self.finished.emit(self.pdf_path)
        except Exception as e:
            self.error.emit(str(e))


# ----------------------------------------------------------------------
# Theme Manager
# ----------------------------------------------------------------------
class ThemeManager:
    """Manages application themes and applies QSS stylesheets."""

    def __init__(self) -> None:
        """Initialize the theme manager with default themes."""
        self.themes: dict[str, dict[str, str]] = {}
        self.current_theme: str | None = None
        self._register_default_themes()

    def _register_default_themes(self) -> None:
        """Register built‑in themes with their color palettes."""
        self.base_style = """
QMainWindow {{
    background-color: {bg_main};
}}
QWidget {{
    background-color: {bg_main};
    color: {fg};
    font-family: 'Segoe UI', 'Arial', sans-serif;
    font-size: 9pt;
}}
QGroupBox {{
    border: 1px solid {border};
    border-radius: 6px;
    margin-top: 1.2ex;
    padding-top: 8px;
    background-color: {bg_widget};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px 0 5px;
    color: {fg};
    background-color: {bg_main};
    border-radius: 4px;
}}
QPushButton {{
    background-color: {bg_secondary};
    border: 1px solid {border};
    border-radius: 4px;
    padding: 4px 6px;
    color: {fg};
    font-weight: 500;
    min-height: 16px;
    text-align: left;
    font-size: 9pt;
}}
QPushButton:hover {{
    background-color: {hover};
    border-color: {border_light};
}}
QPushButton:pressed {{
    background-color: {pressed};
}}
QPushButton:default {{
    background-color: {accent};
    border-color: {accent_dark};
}}
QPushButton:default:hover {{
    background-color: {accent_hover};
}}
QCheckBox {{
    spacing: 4px;
    font-size: 9pt;
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border-radius: 3px;
    border: 1px solid {border_light};
    background-color: {bg_secondary};
}}
QCheckBox::indicator:checked {{
    background-color: {accent};
    border-color: {accent_dark};
}}
QComboBox {{
    background-color: {bg_secondary};
    border: 1px solid {border};
    border-radius: 4px;
    padding: 2px 4px;
    min-height: 16px;
    font-size: 9pt;
}}
QComboBox:hover {{
    border-color: {border_light};
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: right center;
    width: 18px;
    border-left: 1px solid {border};
}}
QListWidget {{
    background-color: {bg_secondary};
    border: 1px solid {border};
    border-radius: 4px;
    outline: none;
    font-size: 9pt;
}}
QListWidget::item {{
    padding: 2px 6px;
    border-radius: 2px;
}}
QListWidget::item:selected {{
    background-color: {accent};
    color: white;
}}
QLineEdit {{
    background-color: {bg_secondary};
    border: 1px solid {border};
    border-radius: 4px;
    padding: 2px 4px;
    color: {fg};
    font-size: 9pt;
    min-height: 16px;
}}
QScrollBar:vertical {{
    background: {bg_secondary};
    width: 10px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: {border};
    border-radius: 5px;
    min-height: 16px;
}}
QScrollBar::handle:vertical:hover {{
    background: {border_light};
}}
QScrollBar:horizontal {{
    background: {bg_secondary};
    height: 10px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background: {border};
    border-radius: 5px;
    min-width: 16px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {border_light};
}}
QLabel#infoLabel {{
    background-color: {bg_widget};
    border-top: 1px solid {border};
    padding: 4px;
    color: {fg};
    font-size: 9pt;
}}
QGraphicsView {{
    background-color: {bg_dark};
    border: 1px solid {border};
    border-radius: 6px;
}}
"""
        # Dark theme (default)
        self.themes["Dark"] = {
            "bg_main": "#1e1e1e",
            "bg_widget": "#252525",
            "bg_secondary": "#2a2a2a",
            "bg_dark": "#1a1a1a",
            "fg": "#e0e0e0",
            "border": "#3a3a3a",
            "border_light": "#5a5a5a",
            "hover": "#4a4a4a",
            "pressed": "#2a2a2a",
            "accent": "#0d6efd",
            "accent_dark": "#0a58ca",
            "accent_hover": "#0b5ed7",
        }
        # Pastel Yellow
        self.themes["Pastel Yellow"] = {
            "bg_main": "#f5edd9",
            "bg_widget": "#efe6cf",
            "bg_secondary": "#e9dfc5",
            "bg_dark": "#f0e8d4",
            "fg": "#4a3e2e",
            "border": "#d8cbad",
            "border_light": "#e3d7bc",
            "hover": "#e6dbb8",
            "pressed": "#e0d2ae",
            "accent": "#d4a017",
            "accent_dark": "#b8860b",
            "accent_hover": "#e0b32a",
        }
        # Pastel Blue
        self.themes["Pastel Blue"] = {
            "bg_main": "#d9e6f2",
            "bg_widget": "#cde0f0",
            "bg_secondary": "#c1daee",
            "bg_dark": "#e0edf5",
            "fg": "#2a405c",
            "border": "#b0c4de",
            "border_light": "#c2d4e8",
            "hover": "#c4d8ec",
            "pressed": "#b6cce4",
            "accent": "#3a7ca5",
            "accent_dark": "#2c5a7a",
            "accent_hover": "#4c8eb8",
        }
        # Pastel White
        self.themes["Pastel White"] = {
            "bg_main": "#f0f0f0",
            "bg_widget": "#eaeaea",
            "bg_secondary": "#e4e4e4",
            "bg_dark": "#f5f5f5",
            "fg": "#4a4a4a",
            "border": "#d0d0d0",
            "border_light": "#dcdcdc",
            "hover": "#e8e8e8",
            "pressed": "#e0e0e0",
            "accent": "#8a8a8a",
            "accent_dark": "#6c6c6c",
            "accent_hover": "#a0a0a0",
        }
        # Pastel Purple
        self.themes["Pastel Purple"] = {
            "bg_main": "#e9e0f5",
            "bg_widget": "#e0d4f0",
            "bg_secondary": "#d7c8eb",
            "bg_dark": "#efe6f8",
            "fg": "#3f2d5c",
            "border": "#cbb7e6",
            "border_light": "#d6c6ed",
            "hover": "#dacced",
            "pressed": "#cfbee8",
            "accent": "#8f6bb3",
            "accent_dark": "#6f4f8c",
            "accent_hover": "#a27fbd",
        }
        # Pastel Pink
        self.themes["Pastel Pink"] = {
            "bg_main": "#f5e0e8",
            "bg_widget": "#efd4df",
            "bg_secondary": "#e9c8d6",
            "bg_dark": "#fae8ef",
            "fg": "#714b5a",
            "border": "#e6b8cc",
            "border_light": "#efc8da",
            "hover": "#eacbd9",
            "pressed": "#e2bed0",
            "accent": "#d97a9e",
            "accent_dark": "#b85c80",
            "accent_hover": "#e58eb0",
        }
        # Pastel Green
        self.themes["Pastel Green"] = {
            "bg_main": "#e0f0e0",
            "bg_widget": "#d4ead4",
            "bg_secondary": "#c8e4c8",
            "bg_dark": "#eaf5ea",
            "fg": "#2c5730",
            "border": "#b8d0b8",
            "border_light": "#c8e0c8",
            "hover": "#cae2ca",
            "pressed": "#bed8be",
            "accent": "#5d9e5d",
            "accent_dark": "#457a45",
            "accent_hover": "#73b073",
        }
        self.current_theme = DEFAULT_THEME

    def apply_theme(self, theme_name: str, target_widget: QWidget) -> None:
        """Apply the named theme to the target widget.

        Args:
            theme_name: Name of the registered theme.
            target_widget: Widget to receive the stylesheet.

        Raises:
            ValueError: If the theme name is not registered.
        """
        if theme_name not in self.themes:
            raise ValueError(f"Theme '{theme_name}' not found.")
        self.current_theme = theme_name
        colors = self.themes[theme_name]
        qss = self.base_style.format(**colors)
        target_widget.setStyleSheet(qss)

    def get_theme_names(self) -> list[str]:
        """Return a list of available theme names."""
        return list(self.themes.keys())

    def get_current_theme(self) -> Optional[str]:  # noqa
        """Return the currently active theme name."""
        return self.current_theme


# ----------------------------------------------------------------------
# Arrow Button
# ----------------------------------------------------------------------
class ArrowButton(QWidget):
    """A clickable arrow that rotates when the dropdown is toggled."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the arrow button."""
        super().__init__(parent)
        self._angle = 0.0
        self.setFixedSize(24, 24)
        self.setCursor(Qt.PointingHandCursor)  # type: ignore[attr-defined]

    def angle(self) -> float:
        """Return the current rotation angle."""
        return self._angle

    def set_angle(self, angle: float) -> None:  # noqa
        """Set the rotation angle and request a repaint."""
        self._angle = angle
        self.update()

    def mousePressEvent(self, event: QEvent) -> None:  # noqa
        """Emit the clicked signal on left mouse press."""
        if event.button() == Qt.LeftButton:  # type: ignore[attr-defined]
            self.clicked.emit()

    def paintEvent(self, event: QEvent) -> None:  # noqa
        """Draw the arrow at the current rotation."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)  # type: ignore[attr-defined]
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(self._angle)

        path = QPainterPath()
        size = 10
        path.moveTo(-size / 2, -size / 3)
        path.lineTo(size / 2, -size / 3)
        path.lineTo(0, size / 2)
        path.closeSubpath()

        painter.fillPath(path, QBrush(self.palette().color(QPalette.WindowText)))  # type: ignore[attr-defined]
        painter.end()


# ----------------------------------------------------------------------
# Theme Dropdown Panel
# ----------------------------------------------------------------------
class ThemeDropdownPanel(QWidget):
    """Popup panel listing available themes."""

    theme_selected = Signal(str)

    def __init__(self, theme_manager: ThemeManager, parent: QWidget | None = None) -> None:
        """Initialize the dropdown panel.

        Args:
            theme_manager: Reference to the application theme manager.
            parent: Parent widget.
        """
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)  # type: ignore[attr-defined]
        self.theme_manager = theme_manager
        self.setAttribute(Qt.WA_TranslucentBackground)  # type: ignore[attr-defined]
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)  # type: ignore[attr-defined]

        self._layout = QVBoxLayout()
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(4)
        self.setLayout(self._layout)

        self.theme_buttons: dict[str, QPushButton] = {}
        for name in theme_manager.get_theme_names():
            btn = QPushButton(name)
            btn.setCursor(Qt.PointingHandCursor)  # type: ignore[attr-defined]
            btn.clicked.connect(lambda _, n=name: self.on_theme_clicked(n))
            self._layout.addWidget(btn)
            self.theme_buttons[name] = btn

        self.adjustSize()

    def on_theme_clicked(self, theme_name: str) -> None:
        """Handle theme selection and close the panel."""
        self.theme_selected.emit(theme_name)
        self.close()

    def show_at(self, pos: QPoint) -> None:
        """Display the panel at the given screen position."""
        self.move(pos)
        self.show()


# ----------------------------------------------------------------------
# Floating Theme Button
# ----------------------------------------------------------------------
class FloatingThemeButton(QWidget):
    """A floating button with an animated arrow that opens the theme dropdown."""

    def __init__(self, theme_manager: ThemeManager, parent: QWidget | None = None) -> None:
        """Initialize the floating button.

        Args:
            theme_manager: Reference to the application theme manager.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.dropdown = ThemeDropdownPanel(theme_manager, self.parentWidget())
        self.dropdown.theme_selected.connect(self.on_theme_selected)

        self.arrow = ArrowButton(self)
        self.arrow.clicked.connect(self.toggle_dropdown)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.arrow)
        self.setLayout(layout)

        self.arrow_anim = QPropertyAnimation(self.arrow, b"angle")
        self.arrow_anim.setDuration(200)
        self.arrow_anim.setEasingCurve(QEasingCurve.InOutQuad)  # type: ignore[attr-defined]
        self.arrow_anim.setStartValue(0.0)
        self.arrow_anim.setEndValue(180.0)

        self.is_open = False
        self.setFixedSize(24, 24)

    def toggle_dropdown(self) -> None:
        """Open or close the dropdown panel."""
        if self.is_open:
            self.close_dropdown()
        else:
            self.open_dropdown()

    def open_dropdown(self) -> None:
        """Animate the arrow and show the dropdown."""
        self.arrow_anim.setDirection(QPropertyAnimation.Forward)  # type: ignore[attr-defined]
        self.arrow_anim.start()
        global_pos = self.mapToGlobal(self.rect().bottomRight())
        dropdown_width = self.dropdown.width()
        x = global_pos.x() - dropdown_width
        y = global_pos.y()
        self.dropdown.show_at(QPoint(x, y))
        self.is_open = True

    def close_dropdown(self) -> None:
        """Animate the arrow back and hide the dropdown."""
        self.arrow_anim.setDirection(QPropertyAnimation.Backward)  # type: ignore[attr-defined]
        self.arrow_anim.start()
        self.dropdown.close()
        self.is_open = False

    def on_theme_selected(self, theme_name: str) -> None:
        """Apply the selected theme and close the dropdown."""
        self.theme_manager.apply_theme(theme_name, self.window())
        self.close_dropdown()

    def resizeEvent(self, event: QEvent) -> None:  # type: ignore[override]
        """Reposition the button to the top‑right corner of the parent."""
        if self.parent():
            parent_rect = self.parent().rect()  # type: ignore[attr-defined,union-attr]
            self.move(parent_rect.width() - self.width() - 10, 10)
        super().resizeEvent(event)  # type: ignore[arg-type]


# ----------------------------------------------------------------------
# Main Window: Photo to PDF Editor
# ----------------------------------------------------------------------
class PhotoToPDFEditor(QMainWindow):
    """Main application window for editing images and generating PDFs."""

    @staticmethod
    def ensure_rgb(
        img: Image.Image, background_color: tuple[int, int, int] = (255, 255, 255)
    ) -> Image.Image:
        """Convert image to RGB, replacing alpha with a background color.

        Args:
            img: PIL Image to convert.
            background_color: RGB tuple for the background.

        Returns:
            RGB image.
        """
        if img.mode == "RGBA":
            background = Image.new("RGB", img.size, background_color)
            background.paste(img, mask=img.split()[3])
            return background
        elif img.mode == "LA":  # grayscale with alpha
            img = img.convert("RGBA")
            return PhotoToPDFEditor.ensure_rgb(img, background_color)
        else:
            return img.convert("RGB") if img.mode != "RGB" else img

    def __init__(self) -> None:
        """Initialize the main window and all UI components."""
        super().__init__()
        self.setWindowTitle("Photo to PDF Editor — Optimized")
        self.resize(1300, 850)
        self.setMinimumSize(1100, 650)

        # State variables
        self.image_paths: list[str] = []
        self.base_images: dict[str, Image.Image] = {}
        self.edited_images: dict[str, Image.Image] = {}
        self.current_image_index: int = -1
        self.original_image: Image.Image | None = None
        self.points: list[tuple[int, int]] = []
        self.scale_factor: float = 1.0
        self.image_offset: QPointF = QPointF(0, 0)

        # Settings
        self.auto_contrast: bool = True
        self.resize_enabled: bool = False
        self.resize_target: str = "Оригинал"

        # Graphics scene
        self.scene = QGraphicsScene()
        self.pixmap_item: QGraphicsPixmapItem | None = None
        self.point_items: list[QGraphicsItem] = []
        self.line_items: list[QGraphicsLineItem] = []

        self._setup_ui()

        # Theme manager and floating button
        self.theme_manager = ThemeManager()
        self.theme_manager.apply_theme(DEFAULT_THEME, self)
        self.floating_theme_btn = FloatingThemeButton(self.theme_manager, self.centralWidget())
        self.floating_theme_btn.show()

        self.setFocusPolicy(Qt.StrongFocus)  # type: ignore[attr-defined]
        self.graphics_view.setFocusPolicy(Qt.StrongFocus)  # type: ignore[attr-defined]

        # Hotkeys
        QShortcut(Qt.Key_Left, self, self.prev_image)  # type: ignore[attr-defined]
        QShortcut(Qt.Key_Right, self, self.next_image)  # type: ignore[attr-defined]
        QShortcut(Qt.Key_Up, self, self.move_current_up)  # type: ignore[attr-defined]
        QShortcut(Qt.Key_Down, self, self.move_current_down)  # type: ignore[attr-defined]

        self.graphics_view.setFocus()

        # PDF thread placeholder
        self.pdf_thread: PDFSaver | None = None

    def _setup_ui(self) -> None:
        """Create and arrange all UI widgets."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Left panel
        left_panel = QWidget()
        left_panel.setMaximumWidth(340)
        left_panel.setMinimumWidth(300)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(6)

        # Add all functional groups to the left panel
        left_layout.addWidget(self._create_file_group())
        left_layout.addWidget(self._create_processing_group())
        left_layout.addWidget(self._create_flexible_group())
        left_layout.addWidget(self._create_geometry_group())

        self.btn_save_pdf = QPushButton("💾 Сохранить PDF (Ctrl+S)")
        self.btn_save_pdf.clicked.connect(self.save_as_pdf)
        self.btn_save_pdf.setFocusPolicy(Qt.NoFocus)  # type: ignore[attr-defined]
        left_layout.addWidget(self.btn_save_pdf)

        left_layout.addWidget(self._create_image_list_group())

        main_layout.addWidget(left_panel)

        # Right panel (graphics view)
        self.graphics_view = QGraphicsView()
        self.graphics_view.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)  # type: ignore[attr-defined]
        self.graphics_view.setScene(self.scene)
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # type: ignore[attr-defined]
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # type: ignore[attr-defined]
        self.graphics_view.setDragMode(QGraphicsView.NoDrag)  # type: ignore[attr-defined]
        main_layout.addWidget(self.graphics_view)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.hint_label = QLabel(
            "🖱️ ЛКМ - точка | ПКМ / Esc - сброс | ← → - фото | Ctrl+↑/↓ - переместить | "
            "Enter - трансформация | D/F - поворот | G - отражение | "
            "Ctrl+1/2/4/0/9 - размеры | R - сброс выделения"
        )
        self.hint_label.setObjectName("infoLabel")
        self.status_bar.addWidget(self.hint_label, 1)
        self.file_info_label = QLabel("Размер: -\nКачество: оригинальное")
        self.file_info_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)  # type: ignore[attr-defined]
        self.file_info_label.setFixedHeight(30)
        self.status_bar.addPermanentWidget(self.file_info_label)

        # Mouse event handling
        self.scene.setSceneRect(QRectF(0, 0, 100, 100))
        self.graphics_view.setMouseTracking(True)
        self.graphics_view.viewport().installEventFilter(self)

    def _create_file_group(self) -> QGroupBox:
        """Create the file operations group box."""
        group = QGroupBox("📁 Файлы")
        layout = QVBoxLayout(group)
        layout.setSpacing(2)

        self.btn_load = QPushButton("📂 Загрузить изображения")
        self.btn_load.clicked.connect(self.load_images)
        self.btn_load.setFocusPolicy(Qt.NoFocus)  # type: ignore[attr-defined]
        layout.addWidget(self.btn_load)

        self.btn_delete = QPushButton("❌ Удалить текущее")
        self.btn_delete.clicked.connect(self.delete_current_image)
        self.btn_delete.setFocusPolicy(Qt.NoFocus)  # type: ignore[attr-defined]
        layout.addWidget(self.btn_delete)

        self.btn_reset_points = QPushButton("🔄 Очистить выделение")
        self.btn_reset_points.clicked.connect(self.reset_points)
        self.btn_reset_points.setFocusPolicy(Qt.NoFocus)  # type: ignore[attr-defined]
        layout.addWidget(self.btn_reset_points)

        return group

    def _create_processing_group(self) -> QGroupBox:
        """Create the image processing settings group box."""
        group = QGroupBox("⚙️ Обработка")
        layout = QVBoxLayout(group)
        layout.setSpacing(2)

        self.cb_contrast = QCheckBox("✨ Автоконтраст")
        self.cb_contrast.setChecked(True)
        self.cb_contrast.toggled.connect(lambda v: setattr(self, "auto_contrast", v))
        self.cb_contrast.setFocusPolicy(Qt.NoFocus)  # type: ignore[attr-defined]
        layout.addWidget(self.cb_contrast)

        self.cb_resize = QCheckBox("📐 Уменьшить до:")
        self.cb_resize.toggled.connect(lambda v: setattr(self, "resize_enabled", v))
        self.cb_resize.setFocusPolicy(Qt.NoFocus)  # type: ignore[attr-defined]
        layout.addWidget(self.cb_resize)

        self.combo_resize = QComboBox()
        self.combo_resize.addItems(RESIZE_OPTIONS)
        self.combo_resize.currentTextChanged.connect(lambda t: setattr(self, "resize_target", t))
        self.combo_resize.setFocusPolicy(Qt.NoFocus)  # type: ignore[attr-defined]
        layout.addWidget(self.combo_resize)

        self.btn_resize_all = QPushButton("📏 Применить ко всем")
        self.btn_resize_all.clicked.connect(self.apply_resize_to_all)
        self.btn_resize_all.setFocusPolicy(Qt.NoFocus)  # type: ignore[attr-defined]
        layout.addWidget(self.btn_resize_all)

        return group

    def _create_flexible_group(self) -> QGroupBox:
        """Create the flexible resize (target file size) group box."""
        group = QGroupBox("🎯 Гибкое уменьшение (по размеру PDF)")
        layout = QVBoxLayout(group)
        layout.setSpacing(2)

        flex_row = QHBoxLayout()
        flex_row.addWidget(QLabel("Целевой размер (МБ):"))
        self.flex_edit = QLineEdit("10")
        self.flex_edit.setFixedWidth(60)
        self.flex_edit.returnPressed.connect(self.apply_flexible_resize)
        self.flex_edit.setFocusPolicy(Qt.ClickFocus)  # type: ignore[attr-defined]
        flex_row.addWidget(self.flex_edit)
        flex_row.addStretch()
        layout.addLayout(flex_row)

        self.btn_flex = QPushButton("✅ Применить (Enter)")
        self.btn_flex.clicked.connect(self.apply_flexible_resize)
        self.btn_flex.setFocusPolicy(Qt.NoFocus)  # type: ignore[attr-defined]
        layout.addWidget(self.btn_flex)

        return group

    def _create_geometry_group(self) -> QGroupBox:
        """Create the geometric transformation group box."""
        group = QGroupBox("🔄 Геометрия")
        layout = QVBoxLayout(group)
        layout.setSpacing(2)

        self.btn_transform = QPushButton("✂️ Трансформация (Enter)")
        self.btn_transform.clicked.connect(self.apply_perspective_transform)
        self.btn_transform.setFocusPolicy(Qt.NoFocus)  # type: ignore[attr-defined]
        layout.addWidget(self.btn_transform)

        rotate_row = QHBoxLayout()
        self.btn_rotate_left = QPushButton("↺ Влево (D)")
        self.btn_rotate_left.clicked.connect(lambda: self.rotate_image(90))
        self.btn_rotate_left.setFocusPolicy(Qt.NoFocus)  # type: ignore[attr-defined]
        rotate_row.addWidget(self.btn_rotate_left)

        self.btn_rotate_right = QPushButton("↻ Вправо (F)")
        self.btn_rotate_right.clicked.connect(lambda: self.rotate_image(-90))
        self.btn_rotate_right.setFocusPolicy(Qt.NoFocus)  # type: ignore[attr-defined]
        rotate_row.addWidget(self.btn_rotate_right)
        layout.addLayout(rotate_row)

        self.btn_flip = QPushButton("🪞 Отразить (G)")
        self.btn_flip.clicked.connect(self.flip_horizontal)
        self.btn_flip.setFocusPolicy(Qt.NoFocus)  # type: ignore[attr-defined]
        layout.addWidget(self.btn_flip)

        return group

    def _create_image_list_group(self) -> QGroupBox:
        """Create the image list group box."""
        group = QGroupBox("📋 Список изображений")
        layout = QVBoxLayout(group)
        layout.setSpacing(2)

        self.image_list = QListWidget()
        self.image_list.itemClicked.connect(self.on_list_select)
        self.image_list.setFocusPolicy(Qt.NoFocus)  # type: ignore[attr-defined]
        layout.addWidget(self.image_list)

        return group

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Filter mouse events on the graphics view."""
        if obj == self.graphics_view.viewport():
            if event.type() == QEvent.MouseButtonPress:  # type: ignore[attr-defined]
                self._on_view_mouse_press(event)
            elif event.type() == QEvent.MouseMove:  # type: ignore[attr-defined]
                self._on_view_mouse_move(event)
            elif event.type() == QEvent.MouseButtonRelease:  # type: ignore[attr-defined]
                self._on_view_mouse_release(event)
        return super().eventFilter(obj, event)

    def _on_view_mouse_press(self, event: QEvent) -> None:
        """Handle mouse press on the image to add selection points."""
        if self.original_image is None or self.pixmap_item is None:
            return
        pos = self.graphics_view.mapToScene(event.position().toPoint())  # type: ignore[attr-defined]
        img_rect = self.pixmap_item.boundingRect().translated(self.pixmap_item.pos())
        if img_rect.contains(pos):  # type: ignore[call-overload]
            img_x = (pos.x() - self.image_offset.x()) / self.scale_factor
            img_y = (pos.y() - self.image_offset.y()) / self.scale_factor
            if 0 <= img_x < self.original_image.width and 0 <= img_y < self.original_image.height:
                if event.button() == Qt.LeftButton:  # type: ignore[attr-defined]
                    if len(self.points) < 4:
                        self.points.append((int(img_x), int(img_y)))
                        self._draw_points()
                        if len(self.points) == 4:
                            self.hint_label.setText("Выделение готово! Enter - применить")
                elif event.button() == Qt.RightButton:  # type: ignore[attr-defined]
                    self.reset_points()
        self.graphics_view.setFocus()

    def _on_view_mouse_move(self, event: QEvent) -> None:
        """Update status bar with current mouse coordinates."""
        if self.original_image is None or self.pixmap_item is None:
            return
        pos = self.graphics_view.mapToScene(event.position().toPoint())  # type: ignore[attr-defined]
        img_rect = self.pixmap_item.boundingRect().translated(self.pixmap_item.pos())
        if img_rect.contains(pos):  # type: ignore[call-overload]
            img_x = (pos.x() - self.image_offset.x()) / self.scale_factor
            img_y = (pos.y() - self.image_offset.y()) / self.scale_factor
            if 0 <= img_x < self.original_image.width and 0 <= img_y < self.original_image.height:
                self.hint_label.setText(
                    f"({int(img_x)}, {int(img_y)}) | Точки: {len(self.points)}/4"
                )

    def _on_view_mouse_release(self, event: QEvent) -> None:
        """Handle mouse release (no action needed)."""
        pass

    def _draw_points(self) -> None:
        """Render the selection points and connecting lines on the scene."""
        for item in self.point_items + self.line_items:
            self.scene.removeItem(item)
        self.point_items.clear()
        self.line_items.clear()

        if not self.pixmap_item or not self.points:
            return

        for i, (px, py) in enumerate(self.points):
            x = px * self.scale_factor + self.image_offset.x()
            y = py * self.scale_factor + self.image_offset.y()
            ellipse = QGraphicsEllipseItem(x - 5, y - 5, 10, 10)
            ellipse.setBrush(QBrush(QColor(255, 0, 0)))
            ellipse.setPen(QPen(Qt.white, 2))  # type: ignore[attr-defined]
            self.scene.addItem(ellipse)
            self.point_items.append(ellipse)
            text = QGraphicsTextItem(str(i + 1))
            text.setDefaultTextColor(Qt.white)  # type: ignore[attr-defined]
            text.setFont(QFont("Arial", 10, QFont.Bold))  # type: ignore[attr-defined]
            text.setPos(x - 7, y - 25)
            self.scene.addItem(text)
            self.point_items.append(text)

        if len(self.points) > 1:
            pts = []
            for px, py in self.points:
                x = px * self.scale_factor + self.image_offset.x()
                y = py * self.scale_factor + self.image_offset.y()
                pts.append(QPointF(x, y))
            for i in range(len(pts) - 1):
                line = QGraphicsLineItem(pts[i].x(), pts[i].y(), pts[i + 1].x(), pts[i + 1].y())
                line.setPen(QPen(QColor(255, 0, 0), 2))
                self.scene.addItem(line)
                self.line_items.append(line)
            if len(pts) == 4:
                line = QGraphicsLineItem(pts[3].x(), pts[3].y(), pts[0].x(), pts[0].y())
                line.setPen(QPen(QColor(255, 0, 0), 2))
                self.scene.addItem(line)
                self.line_items.append(line)

    def reset_points(self) -> None:
        """Clear all selection points."""
        self.points = []
        self._draw_points()
        self.hint_label.setText(
            "ЛКМ - точка | ПКМ / Esc - сброс | ← → - фото | Enter - трансформация"
        )
        self.graphics_view.setFocus()

    def load_images(self) -> None:
        """Open a file dialog and load selected images."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите изображения",
            "",
            f"Images ({SUPPORTED_IMAGE_EXTENSIONS})",
        )
        for file in files:
            if file not in self.image_paths:
                self.image_paths.append(file)
                self.image_list.addItem(os.path.basename(file))
                img = Image.open(file)
                img = ImageOps.exif_transpose(img)
                img = self.ensure_rgb(img)
                self.base_images[file] = img.copy()
                if file not in self.edited_images:
                    self.edited_images[file] = img.copy()

        if self.image_paths and self.current_image_index == -1:
            self.current_image_index = 0
            self.image_list.setCurrentRow(0)
            self._load_current_image()
        self.graphics_view.setFocus()

    def _load_current_image(self) -> None:
        """Load the currently selected image into the view."""
        if 0 <= self.current_image_index < len(self.image_paths):
            path = self.image_paths[self.current_image_index]
            if path in self.edited_images:
                self.original_image = self.edited_images[path].copy()
            else:
                self.original_image = self.base_images[path].copy()
                self.edited_images[path] = self.original_image.copy()

            QTimer.singleShot(0, self._update_display_image)
            self._update_info_label()
            self.reset_points()
            self.graphics_view.setFocus()

    def _update_info_label(self) -> None:
        """Update the status bar with current image dimensions and filename."""
        if self.original_image:
            path = self.image_paths[self.current_image_index]
            self.file_info_label.setText(
                f"Размер: {self.original_image.width}x{self.original_image.height}\n"
                f"Файл: {os.path.basename(path)}"
            )
        else:
            self.file_info_label.setText("Размер: -\nКачество: оригинальное")

    def _update_display_image(self) -> None:
        """Scale and render the current image in the graphics view."""
        if self.original_image is None:
            return

        view_size = self.graphics_view.viewport().size()
        if view_size.width() <= 1 or view_size.height() <= 1:
            view_size = self.graphics_view.size()
        if view_size.width() <= 1 or view_size.height() <= 1:
            QTimer.singleShot(50, self._update_display_image)
            return

        img_w, img_h = self.original_image.size
        scale = min(view_size.width() / img_w, view_size.height() / img_h, 1.0)
        self.scale_factor = scale
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)

        img_copy = self.original_image.convert("RGB")
        img_copy.thumbnail((new_w, new_h), Image.Resampling.LANCZOS)

        data = img_copy.tobytes("raw", "RGB")
        qimg = QImage(data, img_copy.width, img_copy.height, img_copy.width * 3, QImage.Format_RGB888)  # type: ignore[attr-defined]
        pixmap = QPixmap.fromImage(qimg)

        self.scene.clear()
        self.point_items.clear()
        self.line_items.clear()
        self.pixmap_item = self.scene.addPixmap(pixmap)
        x_offset = (view_size.width() - new_w) // 2
        y_offset = (view_size.height() - new_h) // 2
        self.image_offset = QPointF(x_offset, y_offset)
        self.pixmap_item.setPos(x_offset, y_offset)
        self.scene.setSceneRect(QRectF(0, 0, view_size.width(), view_size.height()))
        self.graphics_view.setSceneRect(QRectF(0, 0, view_size.width(), view_size.height()))
        self._draw_points()
        self.graphics_view.update()

    def on_list_select(self, item: QListWidgetItem) -> None:
        """Handle selection change in the image list."""
        index = self.image_list.row(item)
        if index != self.current_image_index:
            self.current_image_index = index
            self._load_current_image()
        self.graphics_view.setFocus()

    def prev_image(self) -> None:
        """Navigate to the previous image."""
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self.image_list.setCurrentRow(self.current_image_index)
            self._load_current_image()
            self.graphics_view.setFocus()

    def next_image(self) -> None:
        """Navigate to the next image."""
        if self.current_image_index < len(self.image_paths) - 1:
            self.current_image_index += 1
            self.image_list.setCurrentRow(self.current_image_index)
            self._load_current_image()
            self.graphics_view.setFocus()

    def move_current_up(self) -> None:
        """Move the current image one position up in the list."""
        if self.current_image_index > 0:
            idx = self.current_image_index
            self.image_paths[idx], self.image_paths[idx - 1] = (
                self.image_paths[idx - 1],
                self.image_paths[idx],
            )
            self._refresh_image_list()
            self.current_image_index = idx - 1
            self.image_list.setCurrentRow(self.current_image_index)
            self._load_current_image()
            self.graphics_view.setFocus()

    def move_current_down(self) -> None:
        """Move the current image one position down in the list."""
        if self.current_image_index < len(self.image_paths) - 1:
            idx = self.current_image_index
            self.image_paths[idx], self.image_paths[idx + 1] = (
                self.image_paths[idx + 1],
                self.image_paths[idx],
            )
            self._refresh_image_list()
            self.current_image_index = idx + 1
            self.image_list.setCurrentRow(self.current_image_index)
            self._load_current_image()
            self.graphics_view.setFocus()

    def _refresh_image_list(self) -> None:
        """Rebuild the image list widget from the current path list."""
        self.image_list.clear()
        for p in self.image_paths:
            self.image_list.addItem(os.path.basename(p))

    def rotate_image(self, angle: float) -> None:
        """Rotate the current image by the specified angle."""
        if self.original_image is None:
            return
        rotated = self.original_image.rotate(angle, expand=True, resample=Image.Resampling.LANCZOS)
        self._save_geometric_change(rotated)

    def flip_horizontal(self) -> None:
        """Flip the current image horizontally."""
        if self.original_image is None:
            return
        flipped = ImageOps.mirror(self.original_image)
        self._save_geometric_change(flipped)

    def _save_geometric_change(self, new_image: Image.Image) -> None:
        """Persist a geometric transformation to the current image."""
        new_image = self.ensure_rgb(new_image)
        path = self.image_paths[self.current_image_index]
        self.base_images[path] = new_image.copy()
        self.edited_images[path] = new_image.copy()
        self.original_image = new_image
        self._update_display_image()
        self._update_info_label()
        self.reset_points()
        self.graphics_view.setFocus()

    def apply_perspective_transform(self) -> None:
        """Apply a perspective correction using the four selected points."""
        if len(self.points) != 4 or self.original_image is None:
            QMessageBox.warning(self, "Предупреждение", "Нужно выделить 4 точки!")
            return

        try:
            result_image = self._perform_perspective_warp(self.original_image, self.points)
            if self.auto_contrast:
                result_image = ImageOps.autocontrast(result_image, cutoff=1)
            self._save_geometric_change(result_image)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось применить трансформацию: {str(e)}")
        self.graphics_view.setFocus()

    @staticmethod
    def _perform_perspective_warp(
        img: Image.Image, src_points: list[tuple[int, int]]
    ) -> Image.Image:
        """Perform the actual perspective warp using OpenCV.

        Args:
            img: PIL Image to transform.
            src_points: List of four (x, y) points in the original image.

        Returns:
            Warped PIL Image.
        """
        img_array = np.array(img)
        if len(img_array.shape) == 3 and img_array.shape[2] == 3:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

        src = np.array(src_points, dtype=np.float32)
        w_top = np.linalg.norm(src[1] - src[0])
        w_bottom = np.linalg.norm(src[2] - src[3])
        h_left = np.linalg.norm(src[3] - src[0])
        h_right = np.linalg.norm(src[2] - src[1])
        out_w = max(int(w_top), int(w_bottom))
        out_h = max(int(h_left), int(h_right))

        dst = np.array(
            [[0, 0], [out_w - 1, 0], [out_w - 1, out_h - 1], [0, out_h - 1]],
            dtype=np.float32,
        )
        matrix = cv2.getPerspectiveTransform(src, dst)
        result = cv2.warpPerspective(img_array, matrix, (out_w, out_h), flags=cv2.INTER_LANCZOS4)

        if len(result.shape) == 3 and result.shape[2] == 3:
            result_image = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
        else:
            result_image = Image.fromarray(result)

        return result_image

    def apply_resize_to_all(self) -> None:
        """Resize all images according to the selected preset."""
        if not self.image_paths:
            return
        if not self.resize_enabled or self.resize_target == "Оригинал":
            QMessageBox.information(
                self, "Информация", "Уменьшение не включено или выбран 'Оригинал'."
            )
            self.graphics_view.setFocus()
            return

        max_size = self._parse_resize_target(self.resize_target)
        if not max_size:
            self.graphics_view.setFocus()
            return

        target_w, target_h = max_size
        count = 0
        for path in self.image_paths:
            base_img = self.base_images.get(path)
            if base_img is None:
                base_img = Image.open(path)
                base_img = ImageOps.exif_transpose(base_img)
                base_img = self.ensure_rgb(base_img)
                self.base_images[path] = base_img.copy()

            w, h = base_img.size
            if w > target_w or h > target_h:
                if w >= h:
                    new_w = target_w
                    new_h = int(h * (target_w / w))
                else:
                    new_h = target_h
                    new_w = int(w * (target_h / h))
                img_copy = base_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                self.edited_images[path] = img_copy
                count += 1
            else:
                self.edited_images[path] = base_img.copy()

        self._load_current_image()
        QMessageBox.information(
            self, "Готово", f"Уменьшено {count} изображений до {self.resize_target}"
        )
        self.graphics_view.setFocus()

    @staticmethod
    def _parse_resize_target(target: str) -> tuple[int, int] | None:
        """Convert a resize preset name to width/height dimensions."""
        for key, dims in RESIZE_DIMENSIONS.items():
            if key in target:
                return dims
        return None

    def apply_flexible_resize(self) -> None:
        """Resize all images to meet an approximate target PDF file size."""
        if not self.image_paths:
            self.graphics_view.setFocus()
            return

        try:
            target_mb = float(self.flex_edit.text())
            if target_mb <= 0:
                raise ValueError
        except ValueError:
            QMessageBox.critical(self, "Ошибка", "Введите положительное число мегабайт")
            self.graphics_view.setFocus()
            return

        adjusted_target_mb = target_mb * 2.5
        target_bytes = adjusted_target_mb * 1024 * 1024

        total_pixels = 0
        for path in self.image_paths:
            base_img = self.base_images.get(path)
            if base_img is None:
                base_img = Image.open(path)
                base_img = ImageOps.exif_transpose(base_img)
                base_img = self.ensure_rgb(base_img)
                self.base_images[path] = base_img.copy()
            w, h = base_img.size
            total_pixels += w * h

        if total_pixels == 0:
            self.graphics_view.setFocus()
            return

        compression_factor = 2.5
        current_size_bytes = total_pixels * compression_factor

        if target_bytes >= current_size_bytes:
            QMessageBox.information(
                self,
                "Информация",
                "Текущий размер уже меньше целевого. Уменьшение не требуется.",
            )
            self.graphics_view.setFocus()
            return

        scale_factor = math.sqrt(target_bytes / current_size_bytes)

        count = 0
        for path in self.image_paths:
            base_img = self.base_images[path]
            w, h = base_img.size
            new_w = max(1, int(w * scale_factor))
            new_h = max(1, int(h * scale_factor))
            if new_w < w or new_h < h:
                resized = base_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                self.edited_images[path] = resized
                count += 1
            else:
                self.edited_images[path] = base_img.copy()

        self._load_current_image()
        QMessageBox.information(
            self,
            "Готово",
            f"Изображения уменьшены. Ожидаемый размер PDF: ~{target_mb} МБ",
        )
        self.graphics_view.setFocus()

    def quick_resize(self, target_name: str) -> None:
        """Apply a resize preset immediately."""
        self.resize_enabled = True
        self.resize_target = target_name
        self.cb_resize.setChecked(True)
        self.combo_resize.setCurrentText(target_name)
        self.apply_resize_to_all()

    def reset_all_resizes(self) -> None:
        """Restore all images to their pre‑resize state."""
        for path in self.image_paths:
            if path in self.base_images:
                self.edited_images[path] = self.base_images[path].copy()
        self._load_current_image()
        self.resize_enabled = False
        self.resize_target = "Оригинал"
        self.cb_resize.setChecked(False)
        self.combo_resize.setCurrentText("Оригинал")
        QMessageBox.information(
            self,
            "Сброс",
            "Все изображения возвращены к размерам после геометрических правок",
        )
        self.graphics_view.setFocus()

    def activate_flexible_resize(self) -> None:
        """Focus the flexible resize input field."""
        self.cb_resize.setChecked(True)
        self.resize_enabled = True
        self.flex_edit.setFocus()
        self.flex_edit.selectAll()

    def delete_current_image(self) -> None:
        """Remove the current image from the list."""
        if 0 <= self.current_image_index < len(self.image_paths):
            path = self.image_paths[self.current_image_index]
            self.image_list.takeItem(self.current_image_index)
            self.image_paths.pop(self.current_image_index)
            if path in self.base_images:
                del self.base_images[path]
            if path in self.edited_images:
                del self.edited_images[path]

            if self.image_paths:
                self.current_image_index = min(self.current_image_index, len(self.image_paths) - 1)
                self.image_list.setCurrentRow(self.current_image_index)
                self._load_current_image()
            else:
                self.current_image_index = -1
                self.original_image = None
                self.scene.clear()
                self.point_items.clear()
                self.line_items.clear()
                self.pixmap_item = None
                self.file_info_label.setText("Размер: -\nКачество: оригинальное")
        self.graphics_view.setFocus()

    def save_as_pdf(self) -> None:
        """Start background PDF generation."""
        if not self.image_paths:
            QMessageBox.warning(self, "Предупреждение", "Нет изображений для сохранения!")
            return

        pdf_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить PDF как", "", "PDF files (*.pdf)"
        )
        if not pdf_path:
            self.graphics_view.setFocus()
            return

        self.btn_save_pdf.setEnabled(False)
        self.status_bar.showMessage("Генерация PDF... (это может занять некоторое время)")

        self.pdf_thread = PDFSaver(
            self.image_paths, self.base_images, self.edited_images, pdf_path, self
        )
        self.pdf_thread.finished.connect(self._on_pdf_saved)
        self.pdf_thread.error.connect(self._on_pdf_error)
        self.pdf_thread.start()

    def _on_pdf_saved(self, pdf_path: str) -> None:
        """Handle successful PDF generation."""
        self.btn_save_pdf.setEnabled(True)
        self.status_bar.clearMessage()
        QMessageBox.information(self, "Успех", f"PDF сохранён: {pdf_path}")
        self.graphics_view.setFocus()

    def _on_pdf_error(self, error_msg: str) -> None:
        """Handle PDF generation errors."""
        self.btn_save_pdf.setEnabled(True)
        self.status_bar.clearMessage()
        QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить PDF: {error_msg}")
        self.graphics_view.setFocus()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle global keyboard shortcuts."""
        key = event.key()
        modifiers = event.modifiers()

        if modifiers & Qt.ControlModifier:  # type: ignore[attr-defined]
            if key == Qt.Key_S:  # type: ignore[attr-defined]
                self.save_as_pdf()
            elif key == Qt.Key_1:  # type: ignore[attr-defined]
                self.quick_resize("Full HD (1920x1080)")
            elif key == Qt.Key_2:  # type: ignore[attr-defined]
                self.quick_resize("2K (2560x1440)")
            elif key == Qt.Key_4:  # type: ignore[attr-defined]
                self.quick_resize("4K (3840x2160)")
            elif key == Qt.Key_0:  # type: ignore[attr-defined]
                self.reset_all_resizes()
            elif key == Qt.Key_9:  # type: ignore[attr-defined]
                self.activate_flexible_resize()
                event.accept()
                return
            return

        if key == Qt.Key_Escape:  # type: ignore[attr-defined]
            self.reset_points()
        elif key in (Qt.Key_Return, Qt.Key_Enter):  # type: ignore[attr-defined]
            if len(self.points) == 4:
                self.apply_perspective_transform()
            else:
                QMessageBox.warning(self, "Предупреждение", "Нужно выделить 4 точки!")
        elif key == Qt.Key_D:  # type: ignore[attr-defined]
            self.rotate_image(90)
        elif key == Qt.Key_F:  # type: ignore[attr-defined]
            self.rotate_image(-90)
        elif key == Qt.Key_G:  # type: ignore[attr-defined]
            self.flip_horizontal()
        elif key == Qt.Key_R:  # type: ignore[attr-defined]
            self.reset_points()
        else:
            super().keyPressEvent(event)

    def resizeEvent(self, event: QEvent) -> None:  # type: ignore[override]
        """Reposition the floating theme button when the window is resized."""
        super().resizeEvent(event)  # type: ignore[arg-type]
        if hasattr(self, "floating_theme_btn"):
            central = self.centralWidget()
            if central:
                self.floating_theme_btn.move(
                    central.width() - self.floating_theme_btn.width() - 10, 10
                )

    def showEvent(self, event: QEvent) -> None:  # type: ignore[override]
        """Ensure the graphics view has focus and position the theme button."""
        super().showEvent(event)  # type: ignore[arg-type]
        self.graphics_view.setFocus()
        QTimer.singleShot(0, self._position_floating_button)

    def _position_floating_button(self) -> None:
        """Place the theme button at the top‑right of the central widget."""
        if hasattr(self, "floating_theme_btn"):
            central = self.centralWidget()
            if central:
                self.floating_theme_btn.move(
                    central.width() - self.floating_theme_btn.width() - 10, 10
                )


# ----------------------------------------------------------------------
# Main entry point
# ----------------------------------------------------------------------
def main() -> None:
    """Run the Photo to PDF Editor application."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = PhotoToPDFEditor()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
