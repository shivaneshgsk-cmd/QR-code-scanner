"""
themes.py — Color Palette, Font Definitions, and Theme Configuration

Provides dark and light mode themes for the application UI.
"""


class AppTheme:
    """Application theme configuration."""

    # ── Brand Colors ──
    PRIMARY = "#2563EB"        # Blue
    PRIMARY_HOVER = "#1D4ED8"
    PRIMARY_LIGHT = "#3B82F6"

    SECONDARY = "#06B6D4"      # Cyan
    SECONDARY_HOVER = "#0891B2"

    ACCENT = "#10B981"         # Green
    ACCENT_HOVER = "#059669"

    WARNING = "#F59E0B"
    ERROR = "#EF4444"
    ERROR_HOVER = "#DC2626"

    SUCCESS = "#10B981"
    INFO = "#3B82F6"

    # ── Dark Mode ──
    DARK = {
        'bg': "#0F172A",
        'bg_secondary': "#1E293B",
        'bg_card': "#1E293B",
        'bg_card_hover': "#334155",
        'bg_input': "#0F172A",
        'bg_sidebar': "#0F172A",
        'bg_header': "#1E293B",
        'fg': "#F8FAFC",
        'fg_secondary': "#94A3B8",
        'fg_muted': "#64748B",
        'border': "#334155",
        'border_light': "#1E293B",
        'scrollbar': "#334155",
        'selection': "#2563EB",
    }

    # ── Light Mode ──
    LIGHT = {
        'bg': "#F8FAFC",
        'bg_secondary': "#F1F5F9",
        'bg_card': "#FFFFFF",
        'bg_card_hover': "#F1F5F9",
        'bg_input': "#FFFFFF",
        'bg_sidebar': "#F1F5F9",
        'bg_header': "#FFFFFF",
        'fg': "#0F172A",
        'fg_secondary': "#475569",
        'fg_muted': "#94A3B8",
        'border': "#E2E8F0",
        'border_light': "#F1F5F9",
        'scrollbar': "#CBD5E1",
        'selection': "#2563EB",
    }

    # ── Fonts ──
    FONT_FAMILY = "Segoe UI"
    FONT_FAMILY_MONO = "Consolas"
    FONT_SIZES = {
        'xs': 10,
        'sm': 11,
        'base': 13,
        'lg': 15,
        'xl': 18,
        '2xl': 22,
        '3xl': 28,
        'hero': 36,
    }

    # ── Spacing ──
    PADDING = {
        'xs': 4,
        'sm': 8,
        'md': 12,
        'lg': 16,
        'xl': 20,
        '2xl': 28,
    }

    CORNER_RADIUS = 10
    CORNER_RADIUS_SM = 6
    CORNER_RADIUS_LG = 14

    @classmethod
    def get_colors(cls, mode: str = "dark") -> dict:
        """Get color palette for the specified mode."""
        return cls.DARK if mode == "dark" else cls.LIGHT

    @classmethod
    def font(cls, size: str = "base", bold: bool = False) -> tuple:
        """Get font tuple for CustomTkinter."""
        weight = "bold" if bold else "normal"
        return (cls.FONT_FAMILY, cls.FONT_SIZES.get(size, 13), weight)

    @classmethod
    def mono_font(cls, size: str = "base") -> tuple:
        """Get monospace font tuple."""
        return (cls.FONT_FAMILY_MONO, cls.FONT_SIZES.get(size, 13))
