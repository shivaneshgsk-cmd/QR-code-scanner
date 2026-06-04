"""
widgets.py — Custom Reusable Widget Components

Provides premium-look widgets for the QR Scanner dashboard:
- StatusCard: Metric display card with icon
- ResultCard: Decoded QR data display with actions
- ImagePreview: Zoomable image display
- ProgressPanel: Live enhancement status
- HistoryItem: Scan history list row
- FileDropZone: File upload area
"""

import tkinter as tk
from datetime import datetime
from typing import Optional, Callable

import customtkinter as ctk
from PIL import Image, ImageTk

from ui.themes import AppTheme


class StatusCard(ctk.CTkFrame):
    """
    Rounded metric card showing an icon, value, and label.
    Used for stats display in the dashboard header.
    """

    def __init__(self, master, icon: str, value: str, label: str,
                 color: str = AppTheme.PRIMARY, **kwargs):
        colors = AppTheme.get_colors()
        super().__init__(
            master,
            fg_color=colors['bg_card'],
            corner_radius=AppTheme.CORNER_RADIUS,
            **kwargs
        )

        self.grid_columnconfigure(0, weight=1)

        # Icon & Value row
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.grid(row=0, column=0, padx=16, pady=(14, 2), sticky="w")

        icon_label = ctk.CTkLabel(
            top_frame, text=icon, font=AppTheme.font("xl"),
            text_color=color
        )
        icon_label.pack(side="left", padx=(0, 8))

        self.value_label = ctk.CTkLabel(
            top_frame, text=value,
            font=AppTheme.font("2xl", bold=True),
            text_color=colors['fg']
        )
        self.value_label.pack(side="left")

        # Label row
        self.label_widget = ctk.CTkLabel(
            self, text=label,
            font=AppTheme.font("sm"),
            text_color=colors['fg_muted']
        )
        self.label_widget.grid(row=1, column=0, padx=16, pady=(0, 14), sticky="w")

    def update_value(self, value: str):
        """Update the displayed value."""
        self.value_label.configure(text=value)


class ResultCard(ctk.CTkFrame):
    """
    Displays decoded QR code result with copy and save actions.
    """

    def __init__(self, master, on_copy: Optional[Callable] = None,
                 on_save: Optional[Callable] = None, **kwargs):
        colors = AppTheme.get_colors()
        super().__init__(
            master,
            fg_color=colors['bg_card'],
            corner_radius=AppTheme.CORNER_RADIUS,
            **kwargs
        )

        self.on_copy = on_copy
        self.on_save = on_save
        self._colors = colors

        self.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=16, pady=(14, 6), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text="📋  Decoded Result",
            font=AppTheme.font("lg", bold=True),
            text_color=colors['fg']
        ).grid(row=0, column=0, sticky="w")

        # Status badge
        self.status_badge = ctk.CTkLabel(
            header, text="  WAITING  ",
            font=AppTheme.font("xs", bold=True),
            text_color="#FFF",
            fg_color=colors['fg_muted'],
            corner_radius=4,
        )
        self.status_badge.grid(row=0, column=1, sticky="e")

        # Result text area
        self.result_text = ctk.CTkTextbox(
            self, height=100,
            font=AppTheme.mono_font("base"),
            fg_color=colors['bg_input'],
            text_color=colors['fg'],
            border_color=colors['border'],
            border_width=1,
            corner_radius=AppTheme.CORNER_RADIUS_SM,
        )
        self.result_text.grid(row=1, column=0, padx=16, pady=6, sticky="ew")
        self.result_text.insert("1.0", "No QR code decoded yet...")
        self.result_text.configure(state="disabled")

        # Metadata area
        self.meta_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.meta_frame.grid(row=2, column=0, padx=16, pady=(2, 6), sticky="ew")
        self.meta_frame.grid_columnconfigure(0, weight=1)

        self.meta_labels = {}
        meta_items = [
            ("Type", "—"), ("Confidence", "—"), ("Time", "—"),
            ("Enhancement", "—"), ("Resolution", "—"), ("Frame", "—")
        ]
        for i, (key, val) in enumerate(meta_items):
            row = i // 3
            col = i % 3
            frame = ctk.CTkFrame(self.meta_frame, fg_color="transparent")
            frame.grid(row=row, column=col, padx=4, pady=2, sticky="w")

            ctk.CTkLabel(
                frame, text=f"{key}:", font=AppTheme.font("xs"),
                text_color=colors['fg_muted']
            ).pack(side="left", padx=(0, 4))

            lbl = ctk.CTkLabel(
                frame, text=val, font=AppTheme.font("xs", bold=True),
                text_color=colors['fg_secondary']
            )
            lbl.pack(side="left")
            self.meta_labels[key] = lbl

        self.meta_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # Action buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=3, column=0, padx=16, pady=(6, 14), sticky="ew")

        self.copy_btn = ctk.CTkButton(
            btn_frame, text="📋 Copy", width=90, height=32,
            font=AppTheme.font("sm", bold=True),
            fg_color=AppTheme.PRIMARY,
            hover_color=AppTheme.PRIMARY_HOVER,
            corner_radius=AppTheme.CORNER_RADIUS_SM,
            command=self._handle_copy
        )
        self.copy_btn.pack(side="left", padx=(0, 8))

        self.save_btn = ctk.CTkButton(
            btn_frame, text="💾 Save", width=90, height=32,
            font=AppTheme.font("sm", bold=True),
            fg_color=AppTheme.SECONDARY,
            hover_color=AppTheme.SECONDARY_HOVER,
            corner_radius=AppTheme.CORNER_RADIUS_SM,
            command=self._handle_save
        )
        self.save_btn.pack(side="left", padx=(0, 8))

    def set_result(self, text: str, metadata: dict = None):
        """Update the result display."""
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", text)
        self.result_text.configure(state="disabled")

        if text and text != "No QR code decoded yet...":
            self.status_badge.configure(
                text="  DECODED  ",
                fg_color=AppTheme.SUCCESS
            )
        else:
            self.status_badge.configure(
                text="  WAITING  ",
                fg_color=self._colors['fg_muted']
            )

        if metadata:
            for key, lbl in self.meta_labels.items():
                if key in metadata:
                    lbl.configure(text=str(metadata[key]))

    def set_failed(self):
        """Show decode failure status."""
        self.status_badge.configure(
            text="  FAILED  ",
            fg_color=AppTheme.ERROR
        )

    def clear(self):
        """Clear the result display."""
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", "No QR code decoded yet...")
        self.result_text.configure(state="disabled")
        self.status_badge.configure(
            text="  WAITING  ",
            fg_color=self._colors['fg_muted']
        )
        for lbl in self.meta_labels.values():
            lbl.configure(text="—")

    def _handle_copy(self):
        """Copy result text to clipboard."""
        self.result_text.configure(state="normal")
        text = self.result_text.get("1.0", "end").strip()
        self.result_text.configure(state="disabled")
        if self.on_copy:
            self.on_copy(text)

    def _handle_save(self):
        """Trigger save callback."""
        self.result_text.configure(state="normal")
        text = self.result_text.get("1.0", "end").strip()
        self.result_text.configure(state="disabled")
        if self.on_save:
            self.on_save(text)


class ImagePreview(ctk.CTkFrame):
    """
    Zoomable image preview panel with fit-to-screen support.
    """

    def __init__(self, master, **kwargs):
        colors = AppTheme.get_colors()
        super().__init__(
            master,
            fg_color=colors['bg_card'],
            corner_radius=AppTheme.CORNER_RADIUS,
            **kwargs
        )

        self._colors = colors
        self._current_image = None
        self._photo = None
        self._zoom = 1.0

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=12, pady=(10, 4), sticky="ew")

        ctk.CTkLabel(
            header, text="🖼️  Preview",
            font=AppTheme.font("base", bold=True),
            text_color=colors['fg']
        ).pack(side="left")

        # Zoom controls
        zoom_frame = ctk.CTkFrame(header, fg_color="transparent")
        zoom_frame.pack(side="right")

        ctk.CTkButton(
            zoom_frame, text="−", width=28, height=28,
            font=AppTheme.font("base", bold=True),
            fg_color=colors['bg_input'],
            hover_color=colors['bg_card_hover'],
            text_color=colors['fg'],
            corner_radius=4,
            command=self._zoom_out
        ).pack(side="left", padx=2)

        self.zoom_label = ctk.CTkLabel(
            zoom_frame, text="100%",
            font=AppTheme.font("xs"),
            text_color=colors['fg_muted']
        )
        self.zoom_label.pack(side="left", padx=4)

        ctk.CTkButton(
            zoom_frame, text="+", width=28, height=28,
            font=AppTheme.font("base", bold=True),
            fg_color=colors['bg_input'],
            hover_color=colors['bg_card_hover'],
            text_color=colors['fg'],
            corner_radius=4,
            command=self._zoom_in
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            zoom_frame, text="⊡", width=28, height=28,
            font=AppTheme.font("base"),
            fg_color=colors['bg_input'],
            hover_color=colors['bg_card_hover'],
            text_color=colors['fg'],
            corner_radius=4,
            command=self._fit_to_screen
        ).pack(side="left", padx=(6, 0))

        # Canvas for image display
        self.canvas = tk.Canvas(
            self, bg=colors['bg'],
            highlightthickness=0, bd=0
        )
        self.canvas.grid(row=1, column=0, padx=8, pady=(4, 10), sticky="nsew")

        # Placeholder text
        self._placeholder_id = self.canvas.create_text(
            0, 0, text="Upload an image or video to preview",
            fill=colors['fg_muted'], font=AppTheme.font("base"),
            anchor="center"
        )
        self.canvas.bind("<Configure>", self._on_resize)

    def set_image(self, pil_image: Image.Image):
        """Display a PIL image."""
        self._current_image = pil_image
        self._zoom = 1.0
        self._fit_to_screen()

    def set_cv_image(self, cv_image):
        """Display an OpenCV image (BGR NumPy array)."""
        import cv2
        if len(cv_image.shape) == 2:
            rgb = cv2.cvtColor(cv_image, cv2.COLOR_GRAY2RGB)
        else:
            rgb = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        self.set_image(pil_img)

    def clear(self):
        """Clear the preview."""
        self._current_image = None
        self._photo = None
        self.canvas.delete("all")
        colors = AppTheme.get_colors()
        self._placeholder_id = self.canvas.create_text(
            self.canvas.winfo_width() // 2,
            self.canvas.winfo_height() // 2,
            text="Upload an image or video to preview",
            fill=colors['fg_muted'], font=AppTheme.font("base"),
            anchor="center"
        )

    def _render(self):
        """Render current image at current zoom level."""
        if self._current_image is None:
            return

        self.canvas.delete("all")
        self._placeholder_id = None

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()

        img = self._current_image.copy()
        new_w = int(img.width * self._zoom)
        new_h = int(img.height * self._zoom)

        if new_w < 1 or new_h < 1:
            return

        img = img.resize((new_w, new_h), Image.LANCZOS)
        self._photo = ImageTk.PhotoImage(img)

        self.canvas.create_image(cw // 2, ch // 2, image=self._photo, anchor="center")
        self.zoom_label.configure(text=f"{int(self._zoom * 100)}%")

    def _zoom_in(self):
        self._zoom = min(self._zoom * 1.25, 5.0)
        self._render()

    def _zoom_out(self):
        self._zoom = max(self._zoom / 1.25, 0.1)
        self._render()

    def _fit_to_screen(self):
        """Fit image to canvas size."""
        if self._current_image is None:
            return

        cw = max(self.canvas.winfo_width(), 100)
        ch = max(self.canvas.winfo_height(), 100)
        iw, ih = self._current_image.size

        scale_w = cw / iw
        scale_h = ch / ih
        self._zoom = min(scale_w, scale_h) * 0.95

        self._render()

    def _on_resize(self, event):
        if self._current_image:
            self._fit_to_screen()
        elif self._placeholder_id:
            self.canvas.coords(
                self._placeholder_id,
                event.width // 2, event.height // 2
            )


class ProgressPanel(ctk.CTkFrame):
    """
    Live processing status display with progress bar
    and enhancement stage indicator.
    """

    def __init__(self, master, **kwargs):
        colors = AppTheme.get_colors()
        super().__init__(
            master,
            fg_color=colors['bg_card'],
            corner_radius=AppTheme.CORNER_RADIUS,
            **kwargs
        )

        self._colors = colors
        self.grid_columnconfigure(0, weight=1)

        # Header
        ctk.CTkLabel(
            self, text="⚙️  Processing",
            font=AppTheme.font("base", bold=True),
            text_color=colors['fg']
        ).grid(row=0, column=0, padx=16, pady=(12, 6), sticky="w")

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            self, height=8,
            progress_color=AppTheme.PRIMARY,
            fg_color=colors['bg_input'],
            corner_radius=4,
        )
        self.progress_bar.grid(row=1, column=0, padx=16, pady=(0, 6), sticky="ew")
        self.progress_bar.set(0)

        # Percentage label
        self.pct_label = ctk.CTkLabel(
            self, text="0%",
            font=AppTheme.font("xs", bold=True),
            text_color=AppTheme.PRIMARY
        )
        self.pct_label.grid(row=2, column=0, padx=16, pady=(0, 2), sticky="e")

        # Status text
        self.status_label = ctk.CTkLabel(
            self, text="Ready",
            font=AppTheme.font("sm"),
            text_color=colors['fg_secondary']
        )
        self.status_label.grid(row=3, column=0, padx=16, pady=(0, 6), sticky="w")

        # Enhancement stage
        self.stage_label = ctk.CTkLabel(
            self, text="",
            font=AppTheme.font("xs"),
            text_color=colors['fg_muted']
        )
        self.stage_label.grid(row=4, column=0, padx=16, pady=(0, 12), sticky="w")

    def set_progress(self, percent: float):
        """Set progress bar value (0-100)."""
        self.progress_bar.set(percent / 100.0)
        self.pct_label.configure(text=f"{int(percent)}%")

        if percent >= 100:
            self.progress_bar.configure(progress_color=AppTheme.SUCCESS)
        else:
            self.progress_bar.configure(progress_color=AppTheme.PRIMARY)

    def set_status(self, text: str):
        """Update status message."""
        self.status_label.configure(text=text)

    def set_stage(self, text: str):
        """Update enhancement stage text."""
        self.stage_label.configure(text=text)

    def reset(self):
        """Reset to initial state."""
        self.set_progress(0)
        self.set_status("Ready")
        self.set_stage("")
        self.progress_bar.configure(progress_color=AppTheme.PRIMARY)


class HistoryItem(ctk.CTkFrame):
    """Single row in the scan history panel."""

    def __init__(self, master, filename: str, result_text: str,
                 timestamp: str, success: bool = True,
                 on_click: Optional[Callable] = None, **kwargs):
        colors = AppTheme.get_colors()
        super().__init__(
            master,
            fg_color=colors['bg_card'],
            corner_radius=AppTheme.CORNER_RADIUS_SM,
            height=50,
            **kwargs
        )

        self._on_click = on_click
        self.grid_columnconfigure(1, weight=1)

        # Status dot
        status_color = AppTheme.SUCCESS if success else AppTheme.ERROR
        ctk.CTkLabel(
            self, text="●", font=AppTheme.font("sm"),
            text_color=status_color
        ).grid(row=0, column=0, padx=(10, 6), pady=8, rowspan=2)

        # Filename
        ctk.CTkLabel(
            self, text=filename,
            font=AppTheme.font("sm", bold=True),
            text_color=colors['fg'],
            anchor="w"
        ).grid(row=0, column=1, padx=0, pady=(8, 0), sticky="w")

        # Result preview (truncated)
        preview = result_text[:60] + "..." if len(result_text) > 60 else result_text
        ctk.CTkLabel(
            self, text=preview,
            font=AppTheme.font("xs"),
            text_color=colors['fg_muted'],
            anchor="w"
        ).grid(row=1, column=1, padx=0, pady=(0, 8), sticky="w")

        # Timestamp
        ctk.CTkLabel(
            self, text=timestamp,
            font=AppTheme.font("xs"),
            text_color=colors['fg_muted']
        ).grid(row=0, column=2, padx=(8, 12), pady=8, rowspan=2)

        # Click binding
        if on_click:
            self.bind("<Button-1>", lambda e: on_click())
            for child in self.winfo_children():
                child.bind("<Button-1>", lambda e: on_click())


class FileDropZone(ctk.CTkFrame):
    """
    File upload area with browse buttons.
    Provides visual feedback for the upload zone.
    """

    def __init__(self, master,
                 on_image_select: Optional[Callable] = None,
                 on_video_select: Optional[Callable] = None,
                 on_batch_select: Optional[Callable] = None,
                 **kwargs):
        colors = AppTheme.get_colors()
        super().__init__(
            master,
            fg_color=colors['bg_card'],
            corner_radius=AppTheme.CORNER_RADIUS,
            **kwargs
        )

        self.on_image_select = on_image_select
        self.on_video_select = on_video_select
        self.on_batch_select = on_batch_select

        self.grid_columnconfigure(0, weight=1)

        # Drop zone visual
        drop_frame = ctk.CTkFrame(
            self,
            fg_color=colors['bg'],
            corner_radius=AppTheme.CORNER_RADIUS,
            border_color=colors['border'],
            border_width=2,
        )
        drop_frame.grid(row=0, column=0, padx=16, pady=(16, 8), sticky="ew")
        drop_frame.grid_columnconfigure(0, weight=1)

        # Icon and text
        ctk.CTkLabel(
            drop_frame, text="📁",
            font=AppTheme.font("hero"),
            text_color=colors['fg_muted']
        ).grid(row=0, column=0, pady=(20, 4))

        ctk.CTkLabel(
            drop_frame, text="Upload Image or Video",
            font=AppTheme.font("lg", bold=True),
            text_color=colors['fg']
        ).grid(row=1, column=0, pady=(0, 2))

        ctk.CTkLabel(
            drop_frame,
            text="Supports: PNG, JPG, BMP, TIFF, WEBP | MP4, AVI, MOV, MKV",
            font=AppTheme.font("xs"),
            text_color=colors['fg_muted']
        ).grid(row=2, column=0, pady=(0, 16))

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=1, column=0, padx=16, pady=(4, 16), sticky="ew")
        btn_frame.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(
            btn_frame, text="🖼️  Browse Image",
            font=AppTheme.font("sm", bold=True),
            fg_color=AppTheme.PRIMARY,
            hover_color=AppTheme.PRIMARY_HOVER,
            corner_radius=AppTheme.CORNER_RADIUS_SM,
            height=36,
            command=self._browse_image
        ).grid(row=0, column=0, padx=4, sticky="ew")

        ctk.CTkButton(
            btn_frame, text="🎬  Browse Video",
            font=AppTheme.font("sm", bold=True),
            fg_color=AppTheme.SECONDARY,
            hover_color=AppTheme.SECONDARY_HOVER,
            corner_radius=AppTheme.CORNER_RADIUS_SM,
            height=36,
            command=self._browse_video
        ).grid(row=0, column=1, padx=4, sticky="ew")

        ctk.CTkButton(
            btn_frame, text="📦  Batch Process",
            font=AppTheme.font("sm", bold=True),
            fg_color=AppTheme.ACCENT,
            hover_color=AppTheme.ACCENT_HOVER,
            corner_radius=AppTheme.CORNER_RADIUS_SM,
            height=36,
            command=self._browse_batch
        ).grid(row=0, column=2, padx=4, sticky="ew")

    def _browse_image(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.webp"),
                ("All files", "*.*")
            ]
        )
        if path and self.on_image_select:
            self.on_image_select(path)

    def _browse_video(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Select Video",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm"),
                ("All files", "*.*")
            ]
        )
        if path and self.on_video_select:
            self.on_video_select(path)

    def _browse_batch(self):
        from tkinter import filedialog
        paths = filedialog.askopenfilenames(
            title="Select Multiple Files",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.webp"),
                ("All files", "*.*")
            ]
        )
        if paths and self.on_batch_select:
            self.on_batch_select(list(paths))
