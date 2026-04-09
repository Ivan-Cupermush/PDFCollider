import sys
import os
import math
import numpy as np
import cv2
from PIL import Image, ImageOps
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QCheckBox, QComboBox, QLabel, QListWidget, QLineEdit,
    QGroupBox, QFileDialog, QMessageBox,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsEllipseItem,
    QGraphicsLineItem, QGraphicsTextItem, QStatusBar
)
from PySide6.QtCore import (
    Qt, QRectF, QPointF, QEvent, QTimer, QPropertyAnimation, QEasingCurve,
    QParallelAnimationGroup, QPoint, Signal
)
from PySide6.QtGui import (
    QFont, QPixmap, QImage, QColor, QPen, QBrush, QPainter, QShortcut,
    QKeySequence, QTransform, QPainterPath, QPolygonF, QAction, QPalette,
    QIcon, QFontDatabase, QMouseEvent, QPaintEvent, QResizeEvent
)


# ----------------------------------------------------------------------
# Theme Manager
# ----------------------------------------------------------------------
class ThemeManager:
    """Manages application themes and applies QSS stylesheets."""
    def __init__(self):
        self.themes = {}
        self.current_theme = None
        self._register_default_themes()

    def _register_default_themes(self):
        """Register all built‑in themes."""
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

        self.current_theme = "Dark"

    def apply_theme(self, theme_name: str, target_widget: QWidget):
        if theme_name not in self.themes:
            raise ValueError(f"Theme '{theme_name}' not found.")
        self.current_theme = theme_name
        colors = self.themes[theme_name]
        qss = self.base_style.format(**colors)
        target_widget.setStyleSheet(qss)

    def get_theme_names(self):
        return list(self.themes.keys())

    def get_current_theme(self):
        return self.current_theme


# ----------------------------------------------------------------------
# Arrow Button
# ----------------------------------------------------------------------
class ArrowButton(QWidget):
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._angle = 0.0
        self.setFixedSize(24, 24)
        self.setCursor(Qt.PointingHandCursor)

    def angle(self):
        return self._angle

    def set_angle(self, angle):
        self._angle = angle
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(self._angle)

        path = QPainterPath()
        size = 10
        path.moveTo(-size / 2, -size / 3)
        path.lineTo(size / 2, -size / 3)
        path.lineTo(0, size / 2)
        path.closeSubpath()

        painter.fillPath(path, QBrush(self.palette().color(QPalette.WindowText)))
        painter.end()


# ----------------------------------------------------------------------
# Theme Dropdown Panel
# ----------------------------------------------------------------------
class ThemeDropdownPanel(QWidget):
    theme_selected = Signal(str)

    def __init__(self, theme_manager: ThemeManager, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.theme_manager = theme_manager
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(4)
        self.setLayout(self.layout)

        self.theme_buttons = {}
        for name in theme_manager.get_theme_names():
            btn = QPushButton(name)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, n=name: self.on_theme_clicked(n))
            self.layout.addWidget(btn)
            self.theme_buttons[name] = btn

        self.adjustSize()

    def on_theme_clicked(self, theme_name):
        self.theme_selected.emit(theme_name)
        self.close()

    def show_at(self, pos: QPoint):
        self.move(pos)
        self.show()


# ----------------------------------------------------------------------
# Floating Theme Button
# ----------------------------------------------------------------------
class FloatingThemeButton(QWidget):
    def __init__(self, theme_manager: ThemeManager, parent=None):
        super().__init__(parent)
        self.theme_manager = theme_manager
        self.dropdown = ThemeDropdownPanel(theme_manager, self.parent())
        self.dropdown.theme_selected.connect(self.on_theme_selected)

        self.arrow = ArrowButton(self)
        self.arrow.clicked.connect(self.toggle_dropdown)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.arrow)
        self.setLayout(layout)

        self.arrow_anim = QPropertyAnimation(self.arrow, b"angle")
        self.arrow_anim.setDuration(200)
        self.arrow_anim.setEasingCurve(QEasingCurve.InOutQuad)
        self.arrow_anim.setStartValue(0.0)
        self.arrow_anim.setEndValue(180.0)

        self.is_open = False
        self.setFixedSize(24, 24)

    def toggle_dropdown(self):
        if self.is_open:
            self.close_dropdown()
        else:
            self.open_dropdown()

    def open_dropdown(self):
        self.arrow_anim.setDirection(QPropertyAnimation.Forward)
        self.arrow_anim.start()
        global_pos = self.mapToGlobal(self.rect().bottomRight())
        dropdown_width = self.dropdown.width()
        x = global_pos.x() - dropdown_width
        y = global_pos.y()
        self.dropdown.show_at(QPoint(x, y))
        self.is_open = True

    def close_dropdown(self):
        self.arrow_anim.setDirection(QPropertyAnimation.Backward)
        self.arrow_anim.start()
        self.dropdown.close()
        self.is_open = False

    def on_theme_selected(self, theme_name):
        self.theme_manager.apply_theme(theme_name, self.window())
        self.close_dropdown()

    def resizeEvent(self, event):
        if self.parent():
            parent_rect = self.parent().rect()
            self.move(parent_rect.width() - self.width() - 10, 10)
        super().resizeEvent(event)


# ----------------------------------------------------------------------
# PhotoToPDFEditor
# ----------------------------------------------------------------------
class PhotoToPDFEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Photo to PDF Editor — Pro Edition")
        self.resize(1300, 850)
        self.setMinimumSize(1100, 650)

        # State variables
        self.image_paths = []
        self.base_images = {}
        self.edited_images = {}
        self.current_image_index = -1
        self.original_image = None
        self.points = []
        self.scale_factor = 1.0
        self.image_offset = QPointF(0, 0)

        # Settings
        self.auto_contrast = True
        self.resize_enabled = False
        self.resize_target = "Оригинал"

        # Graphics scene
        self.scene = QGraphicsScene()
        self.pixmap_item = None
        self.point_items = []
        self.line_items = []

        self.setup_ui()

        # Theme manager and floating button
        self.theme_manager = ThemeManager()
        self.theme_manager.apply_theme("Dark", self)
        self.floating_theme_btn = FloatingThemeButton(self.theme_manager, self.centralWidget())
        self.floating_theme_btn.show()

        self.setFocusPolicy(Qt.StrongFocus)
        self.graphics_view.setFocusPolicy(Qt.StrongFocus)

        # Hotkeys
        QShortcut(QKeySequence(Qt.Key_Left), self, activated=self.prev_image)
        QShortcut(QKeySequence(Qt.Key_Right), self, activated=self.next_image)
        QShortcut(QKeySequence(Qt.Key_Up), self, activated=self.move_current_up)
        QShortcut(QKeySequence(Qt.Key_Down), self, activated=self.move_current_down)

        self.graphics_view.setFocus()

    def setup_ui(self):
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

        # File group
        file_group = QGroupBox("📁 Файлы")
        file_layout = QVBoxLayout(file_group)
        file_layout.setSpacing(2)
        self.btn_load = QPushButton("📂 Загрузить изображения")
        self.btn_load.clicked.connect(self.load_images)
        self.btn_load.setFocusPolicy(Qt.NoFocus)
        file_layout.addWidget(self.btn_load)

        self.btn_delete = QPushButton("❌ Удалить текущее")
        self.btn_delete.clicked.connect(self.delete_current_image)
        self.btn_delete.setFocusPolicy(Qt.NoFocus)
        file_layout.addWidget(self.btn_delete)

        self.btn_reset_points = QPushButton("🔄 Очистить выделение")
        self.btn_reset_points.clicked.connect(self.reset_points)
        self.btn_reset_points.setFocusPolicy(Qt.NoFocus)
        file_layout.addWidget(self.btn_reset_points)
        left_layout.addWidget(file_group)

        # Processing group
        settings_group = QGroupBox("⚙️ Обработка")
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.setSpacing(2)
        self.cb_contrast = QCheckBox("✨ Автоконтраст")
        self.cb_contrast.setChecked(True)
        self.cb_contrast.toggled.connect(lambda v: setattr(self, 'auto_contrast', v))
        self.cb_contrast.setFocusPolicy(Qt.NoFocus)
        settings_layout.addWidget(self.cb_contrast)

        self.cb_resize = QCheckBox("📐 Уменьшить до:")
        self.cb_resize.toggled.connect(lambda v: setattr(self, 'resize_enabled', v))
        self.cb_resize.setFocusPolicy(Qt.NoFocus)
        settings_layout.addWidget(self.cb_resize)

        self.combo_resize = QComboBox()
        self.combo_resize.addItems(["Оригинал", "4K (3840x2160)", "2K (2560x1440)", "Full HD (1920x1080)"])
        self.combo_resize.currentTextChanged.connect(lambda t: setattr(self, 'resize_target', t))
        self.combo_resize.setFocusPolicy(Qt.NoFocus)
        settings_layout.addWidget(self.combo_resize)

        self.btn_resize_all = QPushButton("📏 Применить ко всем")
        self.btn_resize_all.clicked.connect(self.apply_resize_to_all)
        self.btn_resize_all.setFocusPolicy(Qt.NoFocus)
        settings_layout.addWidget(self.btn_resize_all)
        left_layout.addWidget(settings_group)

        # Flexible resize group
        flex_group = QGroupBox("🎯 Гибкое уменьшение (по размеру PDF)")
        flex_layout = QVBoxLayout(flex_group)
        flex_layout.setSpacing(2)
        flex_row = QHBoxLayout()
        flex_row.addWidget(QLabel("Целевой размер (МБ):"))
        self.flex_edit = QLineEdit("10")
        self.flex_edit.setFixedWidth(60)
        self.flex_edit.returnPressed.connect(self.apply_flexible_resize)
        self.flex_edit.setFocusPolicy(Qt.ClickFocus)
        flex_row.addWidget(self.flex_edit)
        flex_row.addStretch()
        flex_layout.addLayout(flex_row)
        self.btn_flex = QPushButton("✅ Применить (Enter)")
        self.btn_flex.clicked.connect(self.apply_flexible_resize)
        self.btn_flex.setFocusPolicy(Qt.NoFocus)
        flex_layout.addWidget(self.btn_flex)
        left_layout.addWidget(flex_group)

        # Geometry group
        geo_group = QGroupBox("🔄 Геометрия")
        geo_layout = QVBoxLayout(geo_group)
        geo_layout.setSpacing(2)
        self.btn_transform = QPushButton("✂️ Трансформация (Enter)")
        self.btn_transform.clicked.connect(self.apply_perspective_transform)
        self.btn_transform.setFocusPolicy(Qt.NoFocus)
        geo_layout.addWidget(self.btn_transform)

        rotate_row = QHBoxLayout()
        self.btn_rotate_left = QPushButton("↺ Влево (D)")
        self.btn_rotate_left.clicked.connect(lambda: self.rotate_image(90))
        self.btn_rotate_left.setFocusPolicy(Qt.NoFocus)
        rotate_row.addWidget(self.btn_rotate_left)

        self.btn_rotate_right = QPushButton("↻ Вправо (F)")
        self.btn_rotate_right.clicked.connect(lambda: self.rotate_image(-90))
        self.btn_rotate_right.setFocusPolicy(Qt.NoFocus)
        rotate_row.addWidget(self.btn_rotate_right)
        geo_layout.addLayout(rotate_row)

        self.btn_flip = QPushButton("🪞 Отразить (G)")
        self.btn_flip.clicked.connect(self.flip_horizontal)
        self.btn_flip.setFocusPolicy(Qt.NoFocus)
        geo_layout.addWidget(self.btn_flip)
        left_layout.addWidget(geo_group)

        # Save PDF
        self.btn_save_pdf = QPushButton("💾 Сохранить PDF (Ctrl+S)")
        self.btn_save_pdf.clicked.connect(self.save_as_pdf)
        self.btn_save_pdf.setFocusPolicy(Qt.NoFocus)
        left_layout.addWidget(self.btn_save_pdf)

        # Image list
        list_group = QGroupBox("📋 Список изображений")
        list_layout = QVBoxLayout(list_group)
        list_layout.setSpacing(2)
        self.image_list = QListWidget()
        self.image_list.itemClicked.connect(self.on_list_select)
        self.image_list.setFocusPolicy(Qt.NoFocus)
        list_layout.addWidget(self.image_list)
        left_layout.addWidget(list_group)

        main_layout.addWidget(left_panel)

        # Right panel (graphics view)
        self.graphics_view = QGraphicsView()
        self.graphics_view.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.graphics_view.setScene(self.scene)
        self.graphics_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.graphics_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.graphics_view.setDragMode(QGraphicsView.NoDrag)
        main_layout.addWidget(self.graphics_view)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.hint_label = QLabel("🖱️ ЛКМ - точка | ПКМ / Esc - сброс | ← → - фото | Ctrl+↑/↓ - переместить | Enter - трансформация | D/F - поворот | G - отражение | Ctrl+1/2/4/0/9 - размеры | R - сброс выделения")
        self.hint_label.setObjectName("infoLabel")
        self.status_bar.addWidget(self.hint_label, 1)
        self.file_info_label = QLabel("Размер: -\nКачество: оригинальное")
        self.file_info_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.file_info_label.setFixedHeight(30)
        self.status_bar.addPermanentWidget(self.file_info_label)

        # Mouse event handling
        self.scene.setSceneRect(QRectF(0, 0, 100, 100))
        self.graphics_view.setMouseTracking(True)
        self.graphics_view.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.graphics_view.viewport():
            if event.type() == QEvent.MouseButtonPress:
                self.on_view_mouse_press(event)
            elif event.type() == QEvent.MouseMove:
                self.on_view_mouse_move(event)
            elif event.type() == QEvent.MouseButtonRelease:
                self.on_view_mouse_release(event)
        return super().eventFilter(obj, event)

    def on_view_mouse_press(self, event):
        if self.original_image is None or self.pixmap_item is None:
            return
        pos = self.graphics_view.mapToScene(event.position().toPoint())
        img_rect = self.pixmap_item.boundingRect().translated(self.pixmap_item.pos())
        if img_rect.contains(pos):
            img_x = (pos.x() - self.image_offset.x()) / self.scale_factor
            img_y = (pos.y() - self.image_offset.y()) / self.scale_factor
            if 0 <= img_x < self.original_image.width and 0 <= img_y < self.original_image.height:
                if event.button() == Qt.LeftButton:
                    if len(self.points) < 4:
                        self.points.append((int(img_x), int(img_y)))
                        self.draw_points()
                        if len(self.points) == 4:
                            self.hint_label.setText("Выделение готово! Enter - применить")
                elif event.button() == Qt.RightButton:
                    self.reset_points()
        self.graphics_view.setFocus()

    def on_view_mouse_move(self, event):
        if self.original_image is None or self.pixmap_item is None:
            return
        pos = self.graphics_view.mapToScene(event.position().toPoint())
        img_rect = self.pixmap_item.boundingRect().translated(self.pixmap_item.pos())
        if img_rect.contains(pos):
            img_x = (pos.x() - self.image_offset.x()) / self.scale_factor
            img_y = (pos.y() - self.image_offset.y()) / self.scale_factor
            if 0 <= img_x < self.original_image.width and 0 <= img_y < self.original_image.height:
                self.hint_label.setText(f"({int(img_x)}, {int(img_y)}) | Точки: {len(self.points)}/4")

    def on_view_mouse_release(self, event):
        pass

    def draw_points(self):
        for item in self.point_items + self.line_items:
            self.scene.removeItem(item)
        self.point_items.clear()
        self.line_items.clear()

        if not self.pixmap_item or not self.points:
            return

        for i, (px, py) in enumerate(self.points):
            x = px * self.scale_factor + self.image_offset.x()
            y = py * self.scale_factor + self.image_offset.y()
            ellipse = QGraphicsEllipseItem(x-5, y-5, 10, 10)
            ellipse.setBrush(QBrush(QColor(255, 0, 0)))
            ellipse.setPen(QPen(Qt.white, 2))
            self.scene.addItem(ellipse)
            self.point_items.append(ellipse)
            text = QGraphicsTextItem(str(i+1))
            text.setDefaultTextColor(Qt.white)
            text.setFont(QFont("Arial", 10, QFont.Bold))
            text.setPos(x-7, y-25)
            self.scene.addItem(text)
            self.point_items.append(text)

        if len(self.points) > 1:
            pts = []
            for px, py in self.points:
                x = px * self.scale_factor + self.image_offset.x()
                y = py * self.scale_factor + self.image_offset.y()
                pts.append(QPointF(x, y))
            for i in range(len(pts)-1):
                line = QGraphicsLineItem(pts[i].x(), pts[i].y(), pts[i+1].x(), pts[i+1].y())
                line.setPen(QPen(QColor(255, 0, 0), 2))
                self.scene.addItem(line)
                self.line_items.append(line)
            if len(pts) == 4:
                line = QGraphicsLineItem(pts[3].x(), pts[3].y(), pts[0].x(), pts[0].y())
                line.setPen(QPen(QColor(255, 0, 0), 2))
                self.scene.addItem(line)
                self.line_items.append(line)

    def reset_points(self):
        self.points = []
        self.draw_points()
        self.hint_label.setText("ЛКМ - точка | ПКМ / Esc - сброс | ← → - фото | Enter - трансформация")
        self.graphics_view.setFocus()

    def load_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Выберите изображения",
            "", "Images (*.jpg *.jpeg *.png *.bmp *.tiff)"
        )
        for file in files:
            if file not in self.image_paths:
                self.image_paths.append(file)
                self.image_list.addItem(os.path.basename(file))
                img = Image.open(file)
                img = ImageOps.exif_transpose(img)
                self.base_images[file] = img.copy()
                if file not in self.edited_images:
                    self.edited_images[file] = img.copy()

        if self.image_paths and self.current_image_index == -1:
            self.current_image_index = 0
            self.image_list.setCurrentRow(0)
            self.load_current_image()
        self.graphics_view.setFocus()

    def load_current_image(self):
        if 0 <= self.current_image_index < len(self.image_paths):
            path = self.image_paths[self.current_image_index]
            if path in self.edited_images:
                self.original_image = self.edited_images[path].copy()
            else:
                self.original_image = self.base_images[path].copy()
                self.edited_images[path] = self.original_image.copy()

            QTimer.singleShot(0, self.update_display_image)
            self.update_info_label()
            self.reset_points()
            self.graphics_view.setFocus()

    def update_info_label(self):
        if self.original_image:
            path = self.image_paths[self.current_image_index]
            self.file_info_label.setText(f"Размер: {self.original_image.width}x{self.original_image.height}\nФайл: {os.path.basename(path)}")
        else:
            self.file_info_label.setText("Размер: -\nКачество: оригинальное")

    def update_display_image(self):
        if self.original_image is None:
            return

        view_size = self.graphics_view.viewport().size()
        if view_size.width() <= 1 or view_size.height() <= 1:
            view_size = self.graphics_view.size()
        if view_size.width() <= 1 or view_size.height() <= 1:
            QTimer.singleShot(50, self.update_display_image)
            return

        img_w, img_h = self.original_image.size
        scale = min(view_size.width() / img_w, view_size.height() / img_h, 1.0)
        self.scale_factor = scale
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)

        img_copy = self.original_image.convert("RGB")
        img_copy.thumbnail((new_w, new_h), Image.Resampling.LANCZOS)

        data = img_copy.tobytes("raw", "RGB")
        qimg = QImage(data, img_copy.width, img_copy.height, img_copy.width * 3, QImage.Format_RGB888)
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
        self.draw_points()
        self.graphics_view.update()

    def on_list_select(self, item):
        index = self.image_list.row(item)
        if index != self.current_image_index:
            self.current_image_index = index
            self.load_current_image()
        self.graphics_view.setFocus()

    def prev_image(self):
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self.image_list.setCurrentRow(self.current_image_index)
            self.load_current_image()
            self.graphics_view.setFocus()

    def next_image(self):
        if self.current_image_index < len(self.image_paths) - 1:
            self.current_image_index += 1
            self.image_list.setCurrentRow(self.current_image_index)
            self.load_current_image()
            self.graphics_view.setFocus()

    # Исправленные функции перемещения (без обмена в словарях)
    def move_current_up(self):
        if self.current_image_index > 0:
            idx = self.current_image_index
            # Меняем местами пути в списке
            self.image_paths[idx], self.image_paths[idx-1] = self.image_paths[idx-1], self.image_paths[idx]
            # Словари base_images и edited_images не трогаем – ключи остались теми же,
            # просто порядок в списке изменился
            self.image_list.clear()
            for p in self.image_paths:
                self.image_list.addItem(os.path.basename(p))
            self.current_image_index = idx - 1
            self.image_list.setCurrentRow(self.current_image_index)
            self.load_current_image()
            self.graphics_view.setFocus()

    def move_current_down(self):
        if self.current_image_index < len(self.image_paths) - 1:
            idx = self.current_image_index
            self.image_paths[idx], self.image_paths[idx+1] = self.image_paths[idx+1], self.image_paths[idx]
            self.image_list.clear()
            for p in self.image_paths:
                self.image_list.addItem(os.path.basename(p))
            self.current_image_index = idx + 1
            self.image_list.setCurrentRow(self.current_image_index)
            self.load_current_image()
            self.graphics_view.setFocus()

    def rotate_image(self, angle):
        if self.original_image is None:
            return
        rotated = self.original_image.rotate(angle, expand=True, resample=Image.Resampling.LANCZOS)
        self._save_geometric_change(rotated)

    def flip_horizontal(self):
        if self.original_image is None:
            return
        flipped = ImageOps.mirror(self.original_image)
        self._save_geometric_change(flipped)

    def _save_geometric_change(self, new_image):
        path = self.image_paths[self.current_image_index]
        self.base_images[path] = new_image.copy()
        self.edited_images[path] = new_image.copy()
        self.original_image = new_image
        self.update_display_image()
        self.update_info_label()
        self.reset_points()
        self.graphics_view.setFocus()

    def apply_perspective_transform(self):
        if len(self.points) != 4 or self.original_image is None:
            QMessageBox.warning(self, "Предупреждение", "Нужно выделить 4 точки!")
            return

        try:
            img_array = np.array(self.original_image)
            if len(img_array.shape) == 3 and img_array.shape[2] == 3:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

            src = np.array(self.points, dtype=np.float32)
            w_top = np.linalg.norm(src[1] - src[0])
            w_bottom = np.linalg.norm(src[2] - src[3])
            h_left = np.linalg.norm(src[3] - src[0])
            h_right = np.linalg.norm(src[2] - src[1])
            out_w = max(int(w_top), int(w_bottom))
            out_h = max(int(h_left), int(h_right))

            dst = np.array([[0, 0], [out_w-1, 0], [out_w-1, out_h-1], [0, out_h-1]], dtype=np.float32)
            matrix = cv2.getPerspectiveTransform(src, dst)
            result = cv2.warpPerspective(img_array, matrix, (out_w, out_h), flags=cv2.INTER_LANCZOS4)

            if len(result.shape) == 3 and result.shape[2] == 3:
                result_image = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
            else:
                result_image = Image.fromarray(result)

            if self.auto_contrast:
                result_image = ImageOps.autocontrast(result_image, cutoff=1)

            self._save_geometric_change(result_image)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось применить трансформацию: {str(e)}")
        self.graphics_view.setFocus()

    def apply_resize_to_all(self):
        if not self.image_paths:
            return
        if not self.resize_enabled or self.resize_target == "Оригинал":
            QMessageBox.information(self, "Информация", "Уменьшение не включено или выбран 'Оригинал'.")
            self.graphics_view.setFocus()
            return

        target = self.resize_target
        max_size = self._parse_resize_target(target)
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

        self.load_current_image()
        QMessageBox.information(self, "Готово", f"Уменьшено {count} изображений до {target} (остальные оставлены без изменений)")
        self.graphics_view.setFocus()

    def _parse_resize_target(self, target):
        if "4K" in target:
            return (3840, 2160)
        elif "2K" in target:
            return (2560, 1440)
        elif "Full HD" in target:
            return (1920, 1080)
        return None

    def apply_flexible_resize(self):
        if not self.image_paths:
            self.graphics_view.setFocus()
            return

        try:
            target_mb = float(self.flex_edit.text())
            if target_mb <= 0:
                raise ValueError
        except:
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
                self.base_images[path] = base_img.copy()
            w, h = base_img.size
            total_pixels += w * h

        if total_pixels == 0:
            self.graphics_view.setFocus()
            return

        compression_factor = 2.5
        current_size_bytes = total_pixels * compression_factor

        if target_bytes >= current_size_bytes:
            QMessageBox.information(self, "Информация", "Текущий размер уже меньше целевого. Уменьшение не требуется.")
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

        self.load_current_image()
        QMessageBox.information(self, "Готово", f"Изображения уменьшены. Ожидаемый размер PDF: ~{target_mb} МБ")
        self.graphics_view.setFocus()

    def quick_resize(self, target_name):
        self.resize_enabled = True
        self.resize_target = target_name
        self.cb_resize.setChecked(True)
        self.combo_resize.setCurrentText(target_name)
        self.apply_resize_to_all()

    def reset_all_resizes(self):
        for path in self.image_paths:
            if path in self.base_images:
                self.edited_images[path] = self.base_images[path].copy()
        self.load_current_image()
        self.resize_enabled = False
        self.resize_target = "Оригинал"
        self.cb_resize.setChecked(False)
        self.combo_resize.setCurrentText("Оригинал")
        QMessageBox.information(self, "Сброс", "Все изображения возвращены к размерам после геометрических правок")
        self.graphics_view.setFocus()

    def activate_flexible_resize(self):
        self.cb_resize.setChecked(True)
        self.resize_enabled = True
        self.flex_edit.setFocus()
        self.flex_edit.selectAll()

    def delete_current_image(self):
        if 0 <= self.current_image_index < len(self.image_paths):
            path = self.image_paths[self.current_image_index]
            self.image_list.takeItem(self.current_image_index)
            self.image_paths.pop(self.current_image_index)
            if path in self.base_images:
                del self.base_images[path]
            if path in self.edited_images:
                del self.edited_images[path]

            if self.image_paths:
                self.current_image_index = min(self.current_image_index, len(self.image_paths)-1)
                self.image_list.setCurrentRow(self.current_image_index)
                self.load_current_image()
            else:
                self.current_image_index = -1
                self.original_image = None
                self.scene.clear()
                self.point_items.clear()
                self.line_items.clear()
                self.pixmap_item = None
                self.file_info_label.setText("Размер: -\nКачество: оригинальное")
        self.graphics_view.setFocus()

    def save_as_pdf(self):
        if not self.image_paths:
            QMessageBox.warning(self, "Предупреждение", "Нет изображений для сохранения!")
            return

        pdf_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить PDF как",
            "", "PDF files (*.pdf)"
        )
        if not pdf_path:
            self.graphics_view.setFocus()
            return

        try:
            c = canvas.Canvas(pdf_path)

            for path in self.image_paths:
                if path in self.edited_images:
                    img = self.edited_images[path]
                else:
                    img = self.base_images.get(path, Image.open(path))
                    img = ImageOps.exif_transpose(img)

                if img.mode != 'RGB':
                    img = img.convert('RGB')

                w, h = img.size
                c.setPageSize((w, h))
                temp = "temp_image.jpg"
                img.save(temp, format='JPEG', quality=100, subsampling=0)
                c.drawImage(ImageReader(temp), 0, 0, width=w, height=h)
                c.showPage()
                os.remove(temp)

            c.save()
            QMessageBox.information(self, "Успех", f"PDF сохранён: {pdf_path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить PDF: {str(e)}")

        self.graphics_view.setFocus()

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()

        if modifiers & Qt.ControlModifier:
            if key == Qt.Key_S:
                self.save_as_pdf()
            elif key == Qt.Key_1:
                self.quick_resize("Full HD (1920x1080)")
            elif key == Qt.Key_2:
                self.quick_resize("2K (2560x1440)")
            elif key == Qt.Key_4:
                self.quick_resize("4K (3840x2160)")
            elif key == Qt.Key_0:
                self.reset_all_resizes()
            elif key == Qt.Key_9:
                self.activate_flexible_resize()
                event.accept()
                return
            return

        if key == Qt.Key_Escape:
            self.reset_points()
        elif key == Qt.Key_Return or key == Qt.Key_Enter:
            if len(self.points) == 4:
                self.apply_perspective_transform()
            else:
                QMessageBox.warning(self, "Предупреждение", "Нужно выделить 4 точки!")
        elif key == Qt.Key_D:
            self.rotate_image(90)
        elif key == Qt.Key_F:
            self.rotate_image(-90)
        elif key == Qt.Key_G:
            self.flip_horizontal()
        elif key == Qt.Key_R:
            self.reset_points()
        else:
            super().keyPressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'floating_theme_btn'):
            central = self.centralWidget()
            if central:
                self.floating_theme_btn.move(central.width() - self.floating_theme_btn.width() - 10, 10)

    def showEvent(self, event):
        super().showEvent(event)
        self.graphics_view.setFocus()
        QTimer.singleShot(0, self._position_floating_button)

    def _position_floating_button(self):
        if hasattr(self, 'floating_theme_btn'):
            central = self.centralWidget()
            if central:
                self.floating_theme_btn.move(central.width() - self.floating_theme_btn.width() - 10, 10)


# ----------------------------------------------------------------------
# Main entry point
# ----------------------------------------------------------------------
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = PhotoToPDFEditor()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()