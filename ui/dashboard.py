"""
dashboard.py — Main Application Window & Layout

Premium CustomTkinter dark-mode dashboard with:
- Header with app title and status
- Sidebar navigation (Scanner, Batch, History, Settings)
- Upload area (browse image/video/batch)
- Image preview with zoom
- Processing area with progress bar
- Results panel with copy/save/export
- History panel with search
- Settings panel with theme switcher
"""

import json
import csv
import logging
import threading
from pathlib import Path
from datetime import datetime
from tkinter import filedialog, messagebox
from typing import Optional

import customtkinter as ctk

from ui.themes import AppTheme
from ui.widgets import (
    StatusCard, ResultCard, ImagePreview,
    ProgressPanel, HistoryItem, FileDropZone
)
from core.image_decoder import ImageDecoder
from core.video_decoder import VideoDecoder

logger = logging.getLogger(__name__)


class Dashboard(ctk.CTk):
    """
    Main application window — QR Code Scanner Dashboard.

    Sections:
    1. Header — App title, logo, system status
    2. Sidebar — Navigation (Scanner, History, Settings)
    3. Main Area — Upload, Preview, Processing, Results
    4. History Panel — Recent scans list
    5. Settings Panel — Configuration options
    """

    APP_TITLE = "QR Code Detector & Decoder"
    APP_VERSION = "1.0.0"
    WINDOW_SIZE = "1280x780"
    MIN_SIZE = (960, 600)

    def __init__(self):
        super().__init__()

        # ── App Configuration ──
        self._mode = "dark"
        self._colors = AppTheme.get_colors(self._mode)
        ctk.set_appearance_mode("dark")

        self.title(self.APP_TITLE)
        self.geometry(self.WINDOW_SIZE)
        self.minsize(*self.MIN_SIZE)

        # ── State ──
        self.image_decoder = ImageDecoder()
        self.video_decoder = VideoDecoder()
        self.scan_history = []
        self._current_view = "scanner"
        self._current_result = None
        self._stats = {
            'total_scans': 0,
            'successful': 0,
            'failed': 0,
        }

        # ── Build UI ──
        self._build_layout()

        logger.info("Dashboard initialized")

    # ═══════════════════════════════════════════════════
    # LAYOUT BUILDING
    # ═══════════════════════════════════════════════════

    def _build_layout(self):
        """Build the complete dashboard layout."""
        self.configure(fg_color=self._colors['bg'])

        # Main grid: sidebar (col 0) | content (col 1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header (row 0, full width)
        self._build_header()

        # Sidebar (row 1, col 0)
        self._build_sidebar()

        # Content area (row 1, col 1)
        self._content_frame = ctk.CTkFrame(
            self, fg_color=self._colors['bg'],
            corner_radius=0
        )
        self._content_frame.grid(row=1, column=1, sticky="nsew", padx=0, pady=0)
        self._content_frame.grid_columnconfigure(0, weight=1)
        self._content_frame.grid_rowconfigure(0, weight=1)

        # Build all views (only one shown at a time)
        self._build_scanner_view()
        self._build_history_view()
        self._build_settings_view()

        # Show default view
        self._show_view("scanner")

    def _build_header(self):
        """Build the header bar."""
        header = ctk.CTkFrame(
            self, fg_color=self._colors['bg_header'],
            corner_radius=0, height=56
        )
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.grid_columnconfigure(1, weight=1)
        header.grid_propagate(False)

        # Logo & Title
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        ctk.CTkLabel(
            title_frame, text="◈",
            font=AppTheme.font("2xl", bold=True),
            text_color=AppTheme.PRIMARY
        ).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(
            title_frame, text=self.APP_TITLE,
            font=AppTheme.font("lg", bold=True),
            text_color=self._colors['fg']
        ).pack(side="left")

        ctk.CTkLabel(
            title_frame, text=f"v{self.APP_VERSION}",
            font=AppTheme.font("xs"),
            text_color=self._colors['fg_muted']
        ).pack(side="left", padx=(8, 0), pady=(4, 0))

        # Status indicator
        self._header_status = ctk.CTkLabel(
            header, text="● Ready",
            font=AppTheme.font("sm"),
            text_color=AppTheme.ACCENT
        )
        self._header_status.grid(row=0, column=2, padx=20, pady=10, sticky="e")

    def _build_sidebar(self):
        """Build the sidebar navigation."""
        sidebar = ctk.CTkFrame(
            self, fg_color=self._colors['bg_sidebar'],
            corner_radius=0, width=200
        )
        sidebar.grid(row=1, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(10, weight=1)

        self._nav_buttons = {}
        nav_items = [
            ("scanner", "🔍", "Scanner"),
            ("history", "📜", "History"),
            ("settings", "⚙️", "Settings"),
        ]

        for i, (key, icon, label) in enumerate(nav_items):
            btn = ctk.CTkButton(
                sidebar,
                text=f"  {icon}  {label}",
                font=AppTheme.font("base"),
                fg_color="transparent",
                hover_color=self._colors['bg_card_hover'],
                text_color=self._colors['fg'],
                anchor="w",
                height=42,
                corner_radius=AppTheme.CORNER_RADIUS_SM,
                command=lambda k=key: self._show_view(k)
            )
            btn.grid(row=i, column=0, padx=10, pady=(10 if i == 0 else 3, 3), sticky="ew")
            self._nav_buttons[key] = btn

        # Stats cards in sidebar
        stats_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        stats_frame.grid(row=10, column=0, padx=10, pady=10, sticky="sew")

        self._total_card = StatusCard(
            stats_frame, "📊", "0", "Total Scans",
            color=AppTheme.PRIMARY
        )
        self._total_card.pack(fill="x", pady=(0, 6))

        self._success_card = StatusCard(
            stats_frame, "✅", "0", "Successful",
            color=AppTheme.SUCCESS
        )
        self._success_card.pack(fill="x", pady=(0, 6))

        self._fail_card = StatusCard(
            stats_frame, "❌", "0", "Failed",
            color=AppTheme.ERROR
        )
        self._fail_card.pack(fill="x")

    # ═══════════════════════════════════════════════════
    # SCANNER VIEW
    # ═══════════════════════════════════════════════════

    def _build_scanner_view(self):
        """Build the main scanner view."""
        self._scanner_frame = ctk.CTkFrame(
            self._content_frame,
            fg_color=self._colors['bg'],
            corner_radius=0
        )

        self._scanner_frame.grid_columnconfigure(0, weight=3)
        self._scanner_frame.grid_columnconfigure(1, weight=2)
        self._scanner_frame.grid_rowconfigure(1, weight=1)

        # ── Left Column ──
        left = ctk.CTkFrame(self._scanner_frame, fg_color="transparent")
        left.grid(row=0, column=0, rowspan=3, padx=(16, 8), pady=12, sticky="nsew")
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)

        # Upload zone
        self._file_drop = FileDropZone(
            left,
            on_image_select=self._on_image_selected,
            on_video_select=self._on_video_selected,
            on_batch_select=self._on_batch_selected
        )
        self._file_drop.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        # Image preview
        self._preview = ImagePreview(left)
        self._preview.grid(row=1, column=0, sticky="nsew")

        # ── Right Column ──
        right = ctk.CTkFrame(self._scanner_frame, fg_color="transparent")
        right.grid(row=0, column=1, rowspan=3, padx=(8, 16), pady=12, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        # Processing panel
        self._progress_panel = ProgressPanel(right)
        self._progress_panel.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        # Result card
        self._result_card = ResultCard(
            right,
            on_copy=self._copy_result,
            on_save=self._save_result
        )
        self._result_card.grid(row=1, column=0, sticky="nsew", pady=(0, 8))

        # Export buttons
        export_frame = ctk.CTkFrame(
            right, fg_color=self._colors['bg_card'],
            corner_radius=AppTheme.CORNER_RADIUS
        )
        export_frame.grid(row=2, column=0, sticky="ew")
        export_frame.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(
            export_frame, text="📄 Export JSON",
            font=AppTheme.font("xs", bold=True),
            fg_color=AppTheme.PRIMARY,
            hover_color=AppTheme.PRIMARY_HOVER,
            height=30, corner_radius=4,
            command=self._export_json
        ).grid(row=0, column=0, padx=8, pady=10, sticky="ew")

        ctk.CTkButton(
            export_frame, text="📊 Export CSV",
            font=AppTheme.font("xs", bold=True),
            fg_color=AppTheme.SECONDARY,
            hover_color=AppTheme.SECONDARY_HOVER,
            height=30, corner_radius=4,
            command=self._export_csv
        ).grid(row=0, column=1, padx=4, pady=10, sticky="ew")

        ctk.CTkButton(
            export_frame, text="📸 Save Screenshot",
            font=AppTheme.font("xs", bold=True),
            fg_color=AppTheme.ACCENT,
            hover_color=AppTheme.ACCENT_HOVER,
            height=30, corner_radius=4,
            command=self._save_screenshot
        ).grid(row=0, column=2, padx=8, pady=10, sticky="ew")

    # ═══════════════════════════════════════════════════
    # HISTORY VIEW
    # ═══════════════════════════════════════════════════

    def _build_history_view(self):
        """Build the history panel view."""
        self._history_frame = ctk.CTkFrame(
            self._content_frame,
            fg_color=self._colors['bg'],
            corner_radius=0
        )
        self._history_frame.grid_columnconfigure(0, weight=1)
        self._history_frame.grid_rowconfigure(1, weight=1)

        # Header with search
        header = ctk.CTkFrame(self._history_frame, fg_color="transparent")
        header.grid(row=0, column=0, padx=20, pady=(16, 8), sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header, text="📜  Scan History",
            font=AppTheme.font("xl", bold=True),
            text_color=self._colors['fg']
        ).grid(row=0, column=0, sticky="w")

        self._history_search = ctk.CTkEntry(
            header, placeholder_text="🔍 Search history...",
            font=AppTheme.font("sm"),
            fg_color=self._colors['bg_input'],
            text_color=self._colors['fg'],
            border_color=self._colors['border'],
            height=34, corner_radius=6, width=250
        )
        self._history_search.grid(row=0, column=1, padx=(16, 0), sticky="e")
        self._history_search.bind("<KeyRelease>", self._filter_history)

        ctk.CTkButton(
            header, text="🗑️ Clear All", width=100, height=34,
            font=AppTheme.font("sm", bold=True),
            fg_color=AppTheme.ERROR,
            hover_color=AppTheme.ERROR_HOVER,
            corner_radius=6,
            command=self._clear_history
        ).grid(row=0, column=2, padx=(8, 0), sticky="e")

        # Scrollable history list
        self._history_list = ctk.CTkScrollableFrame(
            self._history_frame,
            fg_color=self._colors['bg'],
            corner_radius=0,
        )
        self._history_list.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="nsew")
        self._history_list.grid_columnconfigure(0, weight=1)

        # Empty state
        self._history_empty = ctk.CTkLabel(
            self._history_list,
            text="No scan history yet.\nUpload an image or video to get started.",
            font=AppTheme.font("base"),
            text_color=self._colors['fg_muted'],
            justify="center"
        )
        self._history_empty.grid(row=0, column=0, pady=60)

    # ═══════════════════════════════════════════════════
    # SETTINGS VIEW
    # ═══════════════════════════════════════════════════

    def _build_settings_view(self):
        """Build the settings panel."""
        self._settings_frame = ctk.CTkFrame(
            self._content_frame,
            fg_color=self._colors['bg'],
            corner_radius=0
        )
        self._settings_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self._settings_frame, text="⚙️  Settings",
            font=AppTheme.font("xl", bold=True),
            text_color=self._colors['fg']
        ).grid(row=0, column=0, padx=24, pady=(20, 16), sticky="w")

        # Settings card
        card = ctk.CTkFrame(
            self._settings_frame,
            fg_color=self._colors['bg_card'],
            corner_radius=AppTheme.CORNER_RADIUS
        )
        card.grid(row=1, column=0, padx=24, pady=(0, 12), sticky="ew")
        card.grid_columnconfigure(1, weight=1)

        row = 0

        # Theme
        ctk.CTkLabel(
            card, text="Appearance Theme",
            font=AppTheme.font("base", bold=True),
            text_color=self._colors['fg']
        ).grid(row=row, column=0, padx=20, pady=(16, 6), sticky="w")

        self._theme_var = ctk.StringVar(value="Dark")
        theme_menu = ctk.CTkOptionMenu(
            card, values=["Dark", "Light"],
            variable=self._theme_var,
            font=AppTheme.font("sm"),
            fg_color=self._colors['bg_input'],
            button_color=AppTheme.PRIMARY,
            button_hover_color=AppTheme.PRIMARY_HOVER,
            dropdown_fg_color=self._colors['bg_card'],
            dropdown_text_color=self._colors['fg'],
            dropdown_hover_color=self._colors['bg_card_hover'],
            width=160, height=34,
            command=self._change_theme
        )
        theme_menu.grid(row=row, column=1, padx=20, pady=(16, 6), sticky="e")

        row += 1

        # Frame interval
        ctk.CTkLabel(
            card, text="Video Frame Interval (sec)",
            font=AppTheme.font("base", bold=True),
            text_color=self._colors['fg']
        ).grid(row=row, column=0, padx=20, pady=6, sticky="w")

        self._interval_var = ctk.StringVar(value="0.5")
        interval_entry = ctk.CTkEntry(
            card, textvariable=self._interval_var,
            font=AppTheme.font("sm"),
            fg_color=self._colors['bg_input'],
            text_color=self._colors['fg'],
            border_color=self._colors['border'],
            width=160, height=34, corner_radius=6
        )
        interval_entry.grid(row=row, column=1, padx=20, pady=6, sticky="e")

        row += 1

        # Top N frames
        ctk.CTkLabel(
            card, text="Top N Video Frames",
            font=AppTheme.font("base", bold=True),
            text_color=self._colors['fg']
        ).grid(row=row, column=0, padx=20, pady=6, sticky="w")

        self._topn_var = ctk.StringVar(value="10")
        topn_entry = ctk.CTkEntry(
            card, textvariable=self._topn_var,
            font=AppTheme.font("sm"),
            fg_color=self._colors['bg_input'],
            text_color=self._colors['fg'],
            border_color=self._colors['border'],
            width=160, height=34, corner_radius=6
        )
        topn_entry.grid(row=row, column=1, padx=20, pady=(6, 16), sticky="e")

        # About section
        about_card = ctk.CTkFrame(
            self._settings_frame,
            fg_color=self._colors['bg_card'],
            corner_radius=AppTheme.CORNER_RADIUS
        )
        about_card.grid(row=2, column=0, padx=24, pady=0, sticky="ew")

        ctk.CTkLabel(
            about_card, text="About",
            font=AppTheme.font("base", bold=True),
            text_color=self._colors['fg']
        ).grid(row=0, column=0, padx=20, pady=(16, 4), sticky="w")

        ctk.CTkLabel(
            about_card,
            text=(
                f"{self.APP_TITLE} v{self.APP_VERSION}\n"
                "Advanced QR Code Detection & Decoding\n"
                "Powered by ZXing-CPP + OpenCV\n"
                "30-step enhancement pipeline for damaged/blurry QR codes"
            ),
            font=AppTheme.font("sm"),
            text_color=self._colors['fg_muted'],
            justify="left"
        ).grid(row=1, column=0, padx=20, pady=(0, 16), sticky="w")

    # ═══════════════════════════════════════════════════
    # VIEW SWITCHING
    # ═══════════════════════════════════════════════════

    def _show_view(self, view_name: str):
        """Switch to the specified view."""
        # Hide all views
        for frame in [self._scanner_frame, self._history_frame, self._settings_frame]:
            frame.grid_forget()

        # Show selected view
        if view_name == "scanner":
            self._scanner_frame.grid(row=0, column=0, sticky="nsew")
        elif view_name == "history":
            self._history_frame.grid(row=0, column=0, sticky="nsew")
        elif view_name == "settings":
            self._settings_frame.grid(row=0, column=0, sticky="nsew")

        # Update nav button appearance
        for key, btn in self._nav_buttons.items():
            if key == view_name:
                btn.configure(
                    fg_color=self._colors['bg_card_hover'],
                    text_color=AppTheme.PRIMARY
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=self._colors['fg']
                )

        self._current_view = view_name

    # ═══════════════════════════════════════════════════
    # EVENT HANDLERS
    # ═══════════════════════════════════════════════════

    def _on_image_selected(self, file_path: str):
        """Handle image file selection."""
        logger.info(f"Image selected: {file_path}")
        self._header_status.configure(text="● Processing...", text_color=AppTheme.WARNING)
        self._progress_panel.reset()
        self._result_card.clear()

        # Load preview
        try:
            from PIL import Image
            img = Image.open(file_path)
            self._preview.set_image(img)
        except Exception as e:
            logger.error(f"Preview load failed: {e}")

        # Process in background thread
        thread = threading.Thread(
            target=self._process_image,
            args=(file_path,),
            daemon=True
        )
        thread.start()

    def _on_video_selected(self, file_path: str):
        """Handle video file selection."""
        logger.info(f"Video selected: {file_path}")
        self._header_status.configure(text="● Processing video...", text_color=AppTheme.WARNING)
        self._progress_panel.reset()
        self._result_card.clear()

        # Show first frame as preview
        try:
            import cv2
            cap = cv2.VideoCapture(file_path)
            ret, frame = cap.read()
            cap.release()
            if ret:
                self._preview.set_cv_image(frame)
        except Exception:
            pass

        # Process in background thread
        thread = threading.Thread(
            target=self._process_video,
            args=(file_path,),
            daemon=True
        )
        thread.start()

    def _on_batch_selected(self, file_paths: list):
        """Handle batch file selection."""
        logger.info(f"Batch selected: {len(file_paths)} files")
        self._header_status.configure(text="● Batch processing...", text_color=AppTheme.WARNING)
        self._progress_panel.reset()
        self._result_card.clear()

        thread = threading.Thread(
            target=self._process_batch,
            args=(file_paths,),
            daemon=True
        )
        thread.start()

    # ═══════════════════════════════════════════════════
    # PROCESSING (Background threads)
    # ═══════════════════════════════════════════════════

    def _process_image(self, file_path: str):
        """Process image in background thread."""
        def progress_cb(pct):
            self.after(0, self._progress_panel.set_progress, pct)

        def status_cb(msg):
            self.after(0, self._progress_panel.set_status, msg)
            self.after(0, self._progress_panel.set_stage, msg)

        result = self.image_decoder.decode_file(
            file_path,
            progress_callback=progress_cb,
            status_callback=status_cb
        )

        self.after(0, self._handle_result, result)

    def _process_video(self, file_path: str):
        """Process video in background thread."""
        try:
            interval = float(self._interval_var.get())
        except ValueError:
            interval = 0.5

        try:
            top_n = int(self._topn_var.get())
        except ValueError:
            top_n = 10

        def progress_cb(pct):
            self.after(0, self._progress_panel.set_progress, pct)

        def status_cb(msg):
            self.after(0, self._progress_panel.set_status, msg)
            self.after(0, self._progress_panel.set_stage, msg)

        result = self.video_decoder.decode_file(
            file_path,
            frame_interval=interval,
            top_n=top_n,
            progress_callback=progress_cb,
            status_callback=status_cb
        )

        # If video decode got a best frame, show it in preview
        if result.get('success') and result.get('results'):
            best_frame_result = result['results'][0]
            if hasattr(best_frame_result, 'frame_number'):
                result['_frame_info'] = f"Frame #{best_frame_result.frame_number}"

        self.after(0, self._handle_result, result)

    def _process_batch(self, file_paths: list):
        """Process batch in background thread."""
        def progress_cb(pct):
            self.after(0, self._progress_panel.set_progress, pct)

        def status_cb(msg):
            self.after(0, self._progress_panel.set_status, msg)

        results = self.image_decoder.decode_batch(
            file_paths,
            progress_callback=progress_cb,
            status_callback=status_cb
        )

        # Combine results
        for result in results:
            self.after(0, self._handle_result, result)

    # ═══════════════════════════════════════════════════
    # RESULT HANDLING
    # ═══════════════════════════════════════════════════

    def _handle_result(self, result: dict):
        """Handle decode result (runs on main thread)."""
        self._stats['total_scans'] += 1

        if result.get('success') and result.get('results'):
            self._stats['successful'] += 1
            self._header_status.configure(
                text="● Decoded", text_color=AppTheme.SUCCESS
            )

            # Build result text (all QR codes found)
            texts = [r.text for r in result['results']]
            combined_text = "\n---\n".join(texts)

            # Build metadata
            first = result['results'][0]
            metadata = {
                'Type': first.format,
                'Confidence': f"{first.confidence:.0%}",
                'Time': f"{result.get('processing_time', 0):.2f}s",
                'Enhancement': result.get('enhancement_used', 'None'),
                'Resolution': first.image_resolution or result.get('image_resolution', '—'),
                'Frame': first.frame_number if first.frame_number >= 0 else '—',
            }

            self._result_card.set_result(combined_text, metadata)
            self._current_result = result

        else:
            self._stats['failed'] += 1
            self._header_status.configure(
                text="● Failed", text_color=AppTheme.ERROR
            )
            self._result_card.set_result(
                "No QR code could be decoded.",
                {
                    'Type': '—',
                    'Confidence': '0%',
                    'Time': f"{result.get('processing_time', 0):.2f}s",
                    'Enhancement': result.get('enhancement_used', '—'),
                    'Resolution': result.get('image_resolution', '—'),
                    'Frame': '—',
                }
            )
            self._result_card.set_failed()

        # Update stats
        self._total_card.update_value(str(self._stats['total_scans']))
        self._success_card.update_value(str(self._stats['successful']))
        self._fail_card.update_value(str(self._stats['failed']))

        # Add to history
        self._add_to_history(result)

    def _add_to_history(self, result: dict):
        """Add scan result to history."""
        entry = {
            'file': Path(result.get('file_path', 'Unknown')).name,
            'text': result['results'][0].text if result.get('results') else 'No decode',
            'success': result.get('success', False),
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'result': result,
        }
        self.scan_history.insert(0, entry)
        self._refresh_history_list()

    def _refresh_history_list(self):
        """Refresh the history list display."""
        # Clear existing items
        for widget in self._history_list.winfo_children():
            widget.destroy()

        if not self.scan_history:
            self._history_empty = ctk.CTkLabel(
                self._history_list,
                text="No scan history yet.\nUpload an image or video to get started.",
                font=AppTheme.font("base"),
                text_color=self._colors['fg_muted'],
                justify="center"
            )
            self._history_empty.grid(row=0, column=0, pady=60)
            return

        search_term = self._history_search.get().lower().strip()

        for i, entry in enumerate(self.scan_history):
            if search_term and search_term not in entry['file'].lower() and \
               search_term not in entry['text'].lower():
                continue

            item = HistoryItem(
                self._history_list,
                filename=entry['file'],
                result_text=entry['text'],
                timestamp=entry['timestamp'],
                success=entry['success']
            )
            item.grid(row=i, column=0, pady=(0, 4), sticky="ew")

    def _filter_history(self, event=None):
        """Filter history by search term."""
        self._refresh_history_list()

    def _clear_history(self):
        """Clear all scan history."""
        if messagebox.askyesno("Clear History", "Are you sure you want to clear all scan history?"):
            self.scan_history.clear()
            self._refresh_history_list()

    # ═══════════════════════════════════════════════════
    # ACTIONS
    # ═══════════════════════════════════════════════════

    def _copy_result(self, text: str):
        """Copy text to clipboard."""
        if text and text != "No QR code decoded yet...":
            self.clipboard_clear()
            self.clipboard_append(text)
            self._progress_panel.set_status("📋 Copied to clipboard!")

    def _save_result(self, text: str):
        """Save result to text file."""
        if not text or text == "No QR code decoded yet...":
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if path:
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(text)
                self._progress_panel.set_status(f"💾 Saved to {Path(path).name}")
            except Exception as e:
                messagebox.showerror("Save Error", str(e))

    def _export_json(self):
        """Export all history to JSON."""
        if not self.scan_history:
            messagebox.showinfo("Export", "No scan history to export.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )
        if path:
            try:
                export_data = []
                for entry in self.scan_history:
                    item = {
                        'file': entry['file'],
                        'text': entry['text'],
                        'success': entry['success'],
                        'timestamp': entry['timestamp'],
                        'processing_time': entry['result'].get('processing_time', 0),
                        'enhancement': entry['result'].get('enhancement_used', ''),
                    }
                    export_data.append(item)

                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)

                self._progress_panel.set_status(f"📄 Exported JSON: {Path(path).name}")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))

    def _export_csv(self):
        """Export all history to CSV."""
        if not self.scan_history:
            messagebox.showinfo("Export", "No scan history to export.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")]
        )
        if path:
            try:
                with open(path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        'File', 'Decoded Text', 'Success',
                        'Timestamp', 'Processing Time', 'Enhancement'
                    ])
                    for entry in self.scan_history:
                        writer.writerow([
                            entry['file'],
                            entry['text'],
                            entry['success'],
                            entry['timestamp'],
                            entry['result'].get('processing_time', 0),
                            entry['result'].get('enhancement_used', ''),
                        ])

                self._progress_panel.set_status(f"📊 Exported CSV: {Path(path).name}")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))

    def _save_screenshot(self):
        """Save current preview as screenshot."""
        if self._preview._current_image is None:
            messagebox.showinfo("Screenshot", "No image to save.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg")]
        )
        if path:
            try:
                self._preview._current_image.save(path)
                self._progress_panel.set_status(f"📸 Screenshot saved: {Path(path).name}")
            except Exception as e:
                messagebox.showerror("Save Error", str(e))

    # ═══════════════════════════════════════════════════
    # THEME
    # ═══════════════════════════════════════════════════

    def _change_theme(self, choice: str):
        """Switch between dark and light themes."""
        mode = choice.lower()
        ctk.set_appearance_mode(mode)
        self._mode = mode
        self._colors = AppTheme.get_colors(mode)
        self._progress_panel.set_status(f"Theme changed to {choice}")
