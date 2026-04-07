"""Photo to PDF Editor - Lossless Quality."""

import math
import os
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image, ImageOps, ImageTk
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


class PhotoToPDFEditor:
    """Photo to PDF editor with perspective correction and flexible resizing."""

    def __init__(self, root: tk.Tk) -> None:
        """Initialize the application.

        Args:
            root: The root Tkinter window.
        """
        self.root = root
        self.root.title("Photo to PDF Editor - Lossless Quality")
        self.root.geometry("1250x800")
        self.root.focus_set()

        # Variables
        self.image_paths: List[str] = []
        self.base_images: Dict[str, Image.Image] = {}
        self.edited_images: Dict[str, Image.Image] = {}
        self.current_image_index: int = -1
        self.original_image: Optional[Image.Image] = None
        self.display_image: Optional[Image.Image] = None
        self.points: List[Tuple[int, int]] = []
        self.scale_factor: float = 1.0
        self.image_offset: Tuple[int, int] = (0, 0)

        # Processing options
        self.auto_contrast = tk.BooleanVar(value=True)
        self.resize_enabled = tk.BooleanVar(value=False)
        self.resize_target = tk.StringVar(value="Оригинал")

        # Interface
        self.setup_ui()
        self.bind_hotkeys()

    def bind_hotkeys(self) -> None:
        """Bind keyboard shortcuts."""
        # Canvas gets keyboard focus
        self.canvas.bind("<Left>", self.prev_image)
        self.canvas.bind("<Right>", self.next_image)
        self.canvas.bind("<Escape>", self.reset_points)
        self.canvas.bind("<Return>", self.apply_transform_on_enter)
        self.canvas.bind("<Key>", self.on_global_key)

        # Global Ctrl combinations
        self.root.bind("<Control-s>", lambda e: self.save_as_pdf())
        self.root.bind("<Control-S>", lambda e: self.save_as_pdf())
        self.root.bind(
            "<Control-Key-1>", lambda e: self.quick_resize("Full HD (1920x1080)")
        )
        self.root.bind("<Control-Key-2>", lambda e: self.quick_resize("2K (2560x1440)"))
        self.root.bind("<Control-Key-4>", lambda e: self.quick_resize("4K (3840x2160)"))
        self.root.bind("<Control-Key-0>", lambda e: self.reset_all_resizes())
        self.root.bind("<Control-Key-9>", lambda e: self.activate_flexible_resize())

    def on_global_key(self, event: tk.Event) -> None:
        """Handle global key presses on the canvas.

        Args:
            event: The key event.
        """
        if event.widget == self.flex_entry:  # Ignore if focus is in entry
            return
        keysym = event.keysym.lower()
        if keysym == "d":
            self.rotate_image(90)
        elif keysym == "f":
            self.rotate_image(-90)
        elif keysym == "g":
            self.flip_horizontal()
        elif keysym == "r":
            self.reset_points()

    def setup_ui(self) -> None:
        """Create the user interface."""
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Left panel
        left_panel = ttk.Frame(main_frame, width=320)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_panel.pack_propagate(False)

        # File buttons
        ttk.Button(
            left_panel, text="Загрузить изображения", command=self.load_images
        ).pack(fill=tk.X, pady=2)
        ttk.Button(
            left_panel, text="Удалить текущее", command=self.delete_current_image
        ).pack(fill=tk.X, pady=2)
        ttk.Button(
            left_panel, text="Очистить выделение", command=self.reset_points
        ).pack(fill=tk.X, pady=2)

        ttk.Separator(left_panel, orient="horizontal").pack(fill=tk.X, pady=5)

        # Processing settings
        settings_frame = ttk.LabelFrame(left_panel, text="Настройки обработки")
        settings_frame.pack(fill=tk.X, pady=5)

        ttk.Checkbutton(
            settings_frame,
            text="Автоконтраст (рекомендуется)",
            variable=self.auto_contrast,
        ).pack(anchor=tk.W, padx=5, pady=2)

        ttk.Checkbutton(
            settings_frame, text="Уменьшить до:", variable=self.resize_enabled
        ).pack(anchor=tk.W, padx=5, pady=2)

        resize_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.resize_target,
            values=[
                "Оригинал",
                "4K (3840x2160)",
                "2K (2560x1440)",
                "Full HD (1920x1080)",
            ],
            state="readonly",
        )
        resize_combo.pack(fill=tk.X, padx=5, pady=2)
        resize_combo.current(0)

        ttk.Button(
            settings_frame,
            text="Уменьшить все до выбранного",
            command=self.apply_resize_to_all,
        ).pack(fill=tk.X, padx=5, pady=2)

        # Flexible resizing
        flex_frame = ttk.LabelFrame(
            left_panel, text="Гибкое уменьшение (по размеру PDF)"
        )
        flex_frame.pack(fill=tk.X, pady=5)

        mb_frame = ttk.Frame(flex_frame)
        mb_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(mb_frame, text="Целевой размер (МБ):").pack(side=tk.LEFT)
        self.flex_mb_var = tk.StringVar(value="10")
        self.flex_entry = ttk.Entry(mb_frame, textvariable=self.flex_mb_var, width=10)
        self.flex_entry.pack(side=tk.LEFT, padx=5)
        self.flex_entry.bind("<Return>", self.apply_flexible_resize)

        ttk.Button(
            flex_frame, text="Применить (Enter)", command=self.apply_flexible_resize
        ).pack(pady=2)

        ttk.Separator(left_panel, orient="horizontal").pack(fill=tk.X, pady=5)

        # Geometric operations
        geo_frame = ttk.LabelFrame(left_panel, text="Геометрические операции")
        geo_frame.pack(fill=tk.X, pady=5)

        ttk.Button(
            geo_frame,
            text="Применить трансформацию (Enter)",
            command=self.apply_perspective_transform,
        ).pack(fill=tk.X, pady=2)

        rotate_frame = ttk.Frame(geo_frame)
        rotate_frame.pack(fill=tk.X, pady=2)
        ttk.Button(
            rotate_frame, text="↺ Влево (D)", command=lambda: self.rotate_image(90)
        ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))
        ttk.Button(
            rotate_frame, text="↻ Вправо (F)", command=lambda: self.rotate_image(-90)
        ).pack(side=tk.LEFT, expand=True, fill=tk.X)

        ttk.Button(geo_frame, text="↕ Отразить (G)", command=self.flip_horizontal).pack(
            fill=tk.X, pady=2
        )

        ttk.Separator(left_panel, orient="horizontal").pack(fill=tk.X, pady=5)

        # Save PDF
        ttk.Button(
            left_panel, text="Сохранить PDF (Ctrl+S)", command=self.save_as_pdf
        ).pack(fill=tk.X, pady=2)

        # Information
        quality_frame = ttk.LabelFrame(left_panel, text="Информация")
        quality_frame.pack(fill=tk.X, pady=10)

        self.quality_label = ttk.Label(
            quality_frame, text="Размер: -\nКачество: оригинальное", justify=tk.LEFT
        )
        self.quality_label.pack(padx=5, pady=5)

        # Image list
        list_frame = ttk.LabelFrame(left_panel, text="Изображения")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.image_listbox = tk.Listbox(list_frame)
        self.image_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.image_listbox.yview
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.image_listbox.config(yscrollcommand=scrollbar.set)

        self.image_listbox.bind("<<ListboxSelect>>", self.on_image_select)

        # Canvas area
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(canvas_frame, bg="gray20", takefocus=1)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        h_scrollbar = ttk.Scrollbar(
            canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview
        )
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        v_scrollbar = ttk.Scrollbar(
            canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview
        )
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas.configure(
            xscrollcommand=h_scrollbar.set, yscrollcommand=v_scrollbar.set
        )

        # Mouse bindings
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<Button-3>", self.reset_points)
        self.canvas.bind("<Motion>", self.on_mouse_move)

        # Info bar
        self.info_label = ttk.Label(
            self.root,
            text=(
                "ЛКМ - точка | ПКМ / Esc - сброс | ← → - фото | Enter - трансформация | "
                "D/F - поворот | G - отражение | Ctrl+1/2/4/0/9 - размеры | R - сброс выделения"
            ),
            font=("Arial", 9),
        )
        self.info_label.pack(side=tk.BOTTOM, pady=5)

        # Focus canvas
        self.canvas.focus_set()

    # ---------- Image loading and management ----------
    def load_images(self) -> None:
        """Load images from file dialog."""
        files = filedialog.askopenfilenames(
            title="Выберите изображения",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff")],
        )
        for file in files:
            if file not in self.image_paths:
                self.image_paths.append(file)
                self.image_listbox.insert(tk.END, os.path.basename(file))
                img = Image.open(file)
                img = ImageOps.exif_transpose(img)
                self.base_images[file] = img.copy()
                if file not in self.edited_images:
                    self.edited_images[file] = img.copy()

        if self.image_paths and self.current_image_index == -1:
            self.current_image_index = 0
            self.image_listbox.selection_set(0)
            self.load_current_image()
        self.canvas.focus_set()

    def load_current_image(self) -> None:
        """Load the currently selected image."""
        if 0 <= self.current_image_index < len(self.image_paths):
            path = self.image_paths[self.current_image_index]
            if path in self.edited_images:
                self.original_image = self.edited_images[path].copy()
            else:
                self.original_image = self.base_images[path].copy()
                self.edited_images[path] = self.original_image.copy()

            original_size = self.original_image.size
            self.quality_label.config(
                text=f"Размер: {original_size[0]}x{original_size[1]}\nФайл: {os.path.basename(path)}"
            )
            self.display_image, self.scale_factor = self.resize_for_display(
                self.original_image
            )
            self.reset_points()
            self.show_image()
            self.canvas.focus_set()

    def resize_for_display(self, image: Image.Image) -> Tuple[Image.Image, float]:
        """Resize image to fit canvas for display.

        Args:
            image: The original image.

        Returns:
            A tuple of (resized image, scale factor).
        """
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        if canvas_width <= 1:
            canvas_width, canvas_height = 800, 600

        img_w, img_h = image.size
        scale = min(canvas_width / img_w, canvas_height / img_h, 1.0)
        new_size = (int(img_w * scale), int(img_h * scale))
        resized = image.copy()
        resized.thumbnail(new_size, Image.Resampling.LANCZOS)
        return resized, scale

    def show_image(self) -> None:
        """Display the current image on the canvas."""
        if self.display_image:
            self.canvas.delete("all")
            self.tk_image = ImageTk.PhotoImage(self.display_image)  # type: ignore[attr-defined]

            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            img_w, img_h = self.display_image.size
            x_offset = max(0, (cw - img_w) // 2)
            y_offset = max(0, (ch - img_h) // 2)
            self.image_offset = (x_offset, y_offset)

            self.canvas.create_image(
                x_offset, y_offset, anchor=tk.NW, image=self.tk_image, tags="image"
            )
            self.canvas.config(scrollregion=self.canvas.bbox("all"))
            self.draw_points()

    # ---------- Point selection ----------
    def on_canvas_click(self, event: tk.Event) -> None:
        """Handle canvas click to add a point.

        Args:
            event: The mouse click event.
        """
        if self.display_image is None:
            return
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        img_x = x - self.image_offset[0]
        img_y = y - self.image_offset[1]
        if (
            0 <= img_x < self.display_image.width
            and 0 <= img_y < self.display_image.height
        ):
            if len(self.points) < 4:
                orig_x = int(img_x / self.scale_factor)
                orig_y = int(img_y / self.scale_factor)
                self.points.append((orig_x, orig_y))
                self.draw_points()
                if len(self.points) == 4:
                    self.info_label.config(text="Выделение готово! Enter - применить")
            else:
                messagebox.showinfo(
                    "Информация", "Уже 4 точки. Нажмите ПКМ / Esc для сброса"
                )

    def draw_points(self) -> None:
        """Draw the selected points and connecting lines."""
        self.canvas.delete("points")
        for i, (px, py) in enumerate(self.points):
            x = px * self.scale_factor + self.image_offset[0]
            y = py * self.scale_factor + self.image_offset[1]
            self.canvas.create_oval(
                x - 5,
                y - 5,
                x + 5,
                y + 5,
                fill="red",
                outline="white",
                width=2,
                tags="points",
            )
            self.canvas.create_text(
                x,
                y - 15,
                text=str(i + 1),
                fill="white",
                font=("Arial", 12, "bold"),
                tags="points",
            )

        if len(self.points) > 1:
            coords = []
            for px, py in self.points:
                x = px * self.scale_factor + self.image_offset[0]
                y = py * self.scale_factor + self.image_offset[1]
                coords.extend([x, y])
            self.canvas.create_line(coords, fill="red", width=2, tags="points")
            if len(self.points) == 4:
                x1 = self.points[0][0] * self.scale_factor + self.image_offset[0]
                y1 = self.points[0][1] * self.scale_factor + self.image_offset[1]
                x4 = self.points[3][0] * self.scale_factor + self.image_offset[0]
                y4 = self.points[3][1] * self.scale_factor + self.image_offset[1]
                self.canvas.create_line(
                    x4, y4, x1, y1, fill="red", width=2, tags="points"
                )

    def reset_points(self, event: Optional[tk.Event] = None) -> None:
        """Clear all selected points.

        Args:
            event: Optional event (used for bindings).
        """
        self.points = []
        self.draw_points()
        self.info_label.config(
            text="ЛКМ - точка | ПКМ / Esc - сброс | ← → - фото | Enter - трансформация"
        )

    def on_mouse_move(self, event: tk.Event) -> None:
        """Update info label with coordinates when mouse moves.

        Args:
            event: The mouse motion event.
        """
        if self.display_image:
            x = self.canvas.canvasx(event.x) - self.image_offset[0]
            y = self.canvas.canvasy(event.y) - self.image_offset[1]
            if 0 <= x < self.display_image.width and 0 <= y < self.display_image.height:
                orig_x = int(x / self.scale_factor)
                orig_y = int(y / self.scale_factor)
                self.info_label.config(
                    text=f"({orig_x}, {orig_y}) | Точки: {len(self.points)}/4"
                )

    # ---------- Navigation ----------
    def on_image_select(self, event: tk.Event) -> None:
        """Handle selection change in the image list.

        Args:
            event: The listbox selection event.
        """
        sel = self.image_listbox.curselection()
        if sel:
            self.current_image_index = sel[0]
            self.load_current_image()
            self.canvas.focus_set()

    def prev_image(self, event: Optional[tk.Event] = None) -> None:
        """Switch to previous image.

        Args:
            event: Optional event (used for bindings).
        """
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self.sync_listbox_and_load()
            self.canvas.focus_set()

    def next_image(self, event: Optional[tk.Event] = None) -> None:
        """Switch to next image.

        Args:
            event: Optional event (used for bindings).
        """
        if self.current_image_index < len(self.image_paths) - 1:
            self.current_image_index += 1
            self.sync_listbox_and_load()
            self.canvas.focus_set()

    def sync_listbox_and_load(self) -> None:
        """Synchronize listbox selection and load current image."""
        self.image_listbox.selection_clear(0, tk.END)
        self.image_listbox.selection_set(self.current_image_index)
        self.load_current_image()

    # ---------- Geometric operations ----------
    def rotate_image(self, angle: int) -> None:
        """Rotate the current image.

        Args:
            angle: Rotation angle in degrees (positive = counter-clockwise).
        """
        if self.original_image is None:
            return
        rotated = self.original_image.rotate(
            angle, expand=True, resample=Image.Resampling.LANCZOS
        )
        self._save_geometric_change(rotated)

    def flip_horizontal(self) -> None:
        """Mirror the current image horizontally."""
        if self.original_image is None:
            return
        flipped = ImageOps.mirror(self.original_image)
        self._save_geometric_change(flipped)

    def _save_geometric_change(self, new_image: Image.Image) -> None:
        """Save geometric changes and update displayed image.

        Args:
            new_image: The transformed image.
        """
        path = self.image_paths[self.current_image_index]
        self.base_images[path] = new_image.copy()
        self.edited_images[path] = new_image.copy()
        self.original_image = new_image
        original_size = new_image.size
        self.quality_label.config(
            text=f"Размер: {original_size[0]}x{original_size[1]}\nФайл: {os.path.basename(path)}"
        )
        self.display_image, self.scale_factor = self.resize_for_display(new_image)
        self.reset_points()
        self.show_image()
        self.canvas.focus_set()

    # ---------- Perspective transform ----------
    def apply_transform_on_enter(self, event: Optional[tk.Event] = None) -> None:
        """Apply perspective transform when Enter is pressed.

        Args:
            event: Optional event (used for bindings).
        """
        if len(self.points) == 4:
            self.apply_perspective_transform()
        else:
            messagebox.showwarning("Предупреждение", "Нужно выделить 4 точки!")
        self.canvas.focus_set()

    def apply_perspective_transform(self) -> None:
        """Apply perspective correction using selected points."""
        if len(self.points) != 4 or self.original_image is None:
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

            dst = np.array(
                [[0, 0], [out_w - 1, 0], [out_w - 1, out_h - 1], [0, out_h - 1]],
                dtype=np.float32,
            )
            matrix = cv2.getPerspectiveTransform(src, dst)
            result = cv2.warpPerspective(
                img_array, matrix, (out_w, out_h), flags=cv2.INTER_LANCZOS4
            )

            if len(result.shape) == 3 and result.shape[2] == 3:
                result_image = Image.fromarray(cv2.cvtColor(result, cv2.COLOR_BGR2RGB))
            else:
                result_image = Image.fromarray(result)

            if self.auto_contrast.get():
                result_image = ImageOps.autocontrast(result_image, cutoff=1)

            self._save_geometric_change(result_image)

        except Exception as e:
            messagebox.showerror(
                "Ошибка", f"Не удалось применить трансформацию: {str(e)}"
            )
        self.canvas.focus_set()

    # ---------- Resizing operations ----------
    def apply_resize_to_all(self) -> None:
        """Resize all images to the selected fixed resolution."""
        if not self.image_paths:
            return
        if not self.resize_enabled.get() or self.resize_target.get() == "Оригинал":
            messagebox.showinfo(
                "Информация", "Уменьшение не включено или выбран 'Оригинал'."
            )
            self.canvas.focus_set()
            return

        target = self.resize_target.get()
        max_size = self._parse_resize_target(target)
        if not max_size:
            self.canvas.focus_set()
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
            if w >= h:
                new_w = target_w
                new_h = int(h * (target_w / w))
            else:
                new_h = target_h
                new_w = int(w * (target_h / h))

            img_copy = base_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            self.edited_images[path] = img_copy
            count += 1

        self.load_current_image()
        messagebox.showinfo(
            "Готово",
            f"Уменьшено {count} изображений до {target} (длинная сторона подогнана под целевой размер)",
        )
        self.canvas.focus_set()

    @staticmethod
    def _parse_resize_target(target: str) -> Optional[Tuple[int, int]]:
        """Parse target resolution string to (width, height).

        Args:
            target: Target string like "4K (3840x2160)".

        Returns:
            Tuple (width, height) or None if unknown.
        """
        if "4K" in target:
            return (3840, 2160)
        if "2K" in target:
            return (2560, 1440)
        if "Full HD" in target:
            return (1920, 1080)
        return None

    def apply_flexible_resize(self, event: Optional[tk.Event] = None) -> None:
        """Resize all images to meet a target PDF size.

        Args:
            event: Optional event (used for bindings).
        """
        if not self.image_paths:
            self.canvas.focus_set()
            return

        try:
            target_mb = float(self.flex_mb_var.get())
            if target_mb <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Ошибка", "Введите положительное число мегабайт")
            self.canvas.focus_set()
            return

        # Empirical adjustment factor
        adjusted_target_mb = target_mb * 2.5
        target_bytes = adjusted_target_mb * 1024 * 1024

        # Estimate total pixels from base images
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
            self.canvas.focus_set()
            return

        # Approximate bytes per pixel for JPEG quality 100
        compression_factor = 2.5
        current_size_bytes = total_pixels * compression_factor

        if target_bytes >= current_size_bytes:
            messagebox.showinfo(
                "Информация",
                "Текущий размер уже меньше целевого. Уменьшение не требуется.",
            )
            self.canvas.focus_set()
            return

        scale_factor = math.sqrt(target_bytes / current_size_bytes)

        count = 0
        for path in self.image_paths:
            base_img = self.base_images[path]
            w, h = base_img.size
            new_w = max(1, int(w * scale_factor))
            new_h = max(1, int(h * scale_factor))
            resized = base_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            self.edited_images[path] = resized
            count += 1

        self.load_current_image()
        messagebox.showinfo(
            "Готово",
            f"Изображения уменьшены. Ожидаемый размер PDF: ~{target_mb} МБ (с учётом поправки)",
        )
        self.canvas.focus_set()

    # ---------- Quick commands ----------
    def quick_resize(self, target_name: str) -> None:
        """Quick resize to a predefined resolution.

        Args:
            target_name: Resolution name (e.g., "Full HD (1920x1080)").
        """
        self.resize_enabled.set(True)
        self.resize_target.set(target_name)
        self.apply_resize_to_all()
        self.canvas.focus_set()

    def reset_all_resizes(self) -> None:
        """Reset all images to their base sizes (after geometric edits)."""
        for path in self.image_paths:
            if path in self.base_images:
                self.edited_images[path] = self.base_images[path].copy()
        self.load_current_image()
        self.resize_enabled.set(False)
        self.resize_target.set("Оригинал")
        messagebox.showinfo(
            "Сброс", "Все изображения возвращены к размерам после геометрических правок"
        )
        self.canvas.focus_set()

    def activate_flexible_resize(self) -> None:
        """Activate flexible resize mode and focus the entry field."""
        self.resize_enabled.set(True)
        self.flex_entry.focus_set()
        self.flex_entry.select_range(0, tk.END)
        self.info_label.config(text="Введите размер в МБ и нажмите Enter")

    # ---------- Image deletion ----------
    def delete_current_image(self) -> None:
        """Delete the currently selected image."""
        if 0 <= self.current_image_index < len(self.image_paths):
            path = self.image_paths[self.current_image_index]
            del self.image_paths[self.current_image_index]
            self.image_listbox.delete(self.current_image_index)
            if path in self.base_images:
                del self.base_images[path]
            if path in self.edited_images:
                del self.edited_images[path]

            if self.image_paths:
                self.current_image_index = min(
                    self.current_image_index, len(self.image_paths) - 1
                )
                self.image_listbox.selection_set(self.current_image_index)
                self.load_current_image()
            else:
                self.current_image_index = -1
                self.original_image = None
                self.display_image = None
                self.canvas.delete("all")
                self.quality_label.config(text="Размер: -\nКачество: оригинальное")
        self.canvas.focus_set()

    # ---------- PDF saving ----------
    def save_as_pdf(self, event: Optional[tk.Event] = None) -> None:
        """Save all images as a single PDF.

        Args:
            event: Optional event (used for bindings).
        """
        if not self.image_paths:
            messagebox.showwarning("Предупреждение", "Нет изображений для сохранения!")
            self.canvas.focus_set()
            return

        pdf_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            title="Сохранить PDF как...",
        )
        if not pdf_path:
            self.canvas.focus_set()
            return

        try:
            c = canvas.Canvas(pdf_path)

            for path in self.image_paths:
                if path in self.edited_images:
                    img = self.edited_images[path]
                else:
                    img = self.base_images.get(path, Image.open(path))
                    img = ImageOps.exif_transpose(img)

                if img.mode != "RGB":
                    img = img.convert("RGB")

                w, h = img.size
                c.setPageSize((w, h))

                # Use a temporary file with automatic cleanup
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                    temp_path = tmp.name
                img.save(temp_path, format="JPEG", quality=100, subsampling=0)
                c.drawImage(ImageReader(temp_path), 0, 0, width=w, height=h)
                c.showPage()
                os.unlink(temp_path)

            c.save()
            messagebox.showinfo("Успех", f"PDF сохранён: {pdf_path}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить PDF: {str(e)}")

        self.canvas.focus_set()


def main() -> None:
    """Application entry point."""
    root = tk.Tk()
    PhotoToPDFEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()
