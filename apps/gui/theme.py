"""Dark theme for the GUI with Razer-authentic styling."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect


class RazerColors:
    """Centralized color palette for Razer-inspired theme."""

    # Primary accent - Razer signature green
    GREEN_PRIMARY = "#2da05a"
    GREEN_LIGHT = "#3db76a"
    GREEN_DARK = "#1a8040"
    GREEN_GLOW = "#44ff88"

    # Backgrounds - dark gradient
    BG_DARKEST = "#0a0a0a"
    BG_DARKER = "#141414"
    BG_DARK = "#1e1e1e"
    BG_MEDIUM = "#2d2d2d"
    BG_LIGHT = "#3d3d3d"
    BG_LIGHTER = "#4d4d4d"

    # Text hierarchy
    TEXT_PRIMARY = "#dcdcdc"
    TEXT_SECONDARY = "#888888"
    TEXT_DISABLED = "#555555"
    TEXT_INVERSE = "#000000"

    # Status colors
    STATUS_SUCCESS = "#2ecc71"
    STATUS_WARNING = "#f39c12"
    STATUS_ERROR = "#e74c3c"
    STATUS_INFO = "#3498db"

    # Interactive states
    HOVER_BORDER = "#2da05a"
    FOCUS_BORDER = "#44ff88"
    PRESSED_BG = "#2da05a"

    @classmethod
    def as_qcolor(cls, hex_color: str) -> QColor:
        """Convert hex string to QColor."""
        return QColor(hex_color)


class RazerTypography:
    """Font sizes and weights for consistent typography."""

    # Size scale
    SIZE_TITLE = 16
    SIZE_HEADING = 14
    SIZE_BODY = 12
    SIZE_SMALL = 11
    SIZE_TINY = 9

    # Weights (for stylesheet strings)
    WEIGHT_BOLD = "bold"
    WEIGHT_NORMAL = "normal"

    # Font family preference
    FONT_FAMILY = "Segoe UI, Ubuntu, Helvetica, Arial, sans-serif"
    FONT_MONO = "JetBrains Mono, Consolas, Monaco, monospace"


class RazerSpacing:
    """Consistent spacing values for layouts."""

    XS = 4  # Tight spacing
    SM = 8  # Standard spacing
    MD = 12  # Medium spacing
    LG = 16  # Large spacing
    XL = 24  # Extra large spacing

    # Specific use cases
    BUTTON_PADDING_H = 16
    BUTTON_PADDING_V = 6
    CARD_PADDING = 12
    CARD_MARGIN = 8


class RazerEffects:
    """Factory for visual effects like shadows and glows."""

    @staticmethod
    def shadow_small() -> QGraphicsDropShadowEffect:
        """Subtle shadow for buttons and small elements."""
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(6)
        effect.setOffset(0, 2)
        effect.setColor(QColor(0, 0, 0, 80))
        return effect

    @staticmethod
    def shadow_medium() -> QGraphicsDropShadowEffect:
        """Medium shadow for cards and panels."""
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(12)
        effect.setOffset(0, 4)
        effect.setColor(QColor(0, 0, 0, 100))
        return effect

    @staticmethod
    def shadow_large() -> QGraphicsDropShadowEffect:
        """Large shadow for dialogs and overlays."""
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(24)
        effect.setOffset(0, 8)
        effect.setColor(QColor(0, 0, 0, 120))
        return effect

    @staticmethod
    def glow(color: str = RazerColors.GREEN_GLOW) -> QGraphicsDropShadowEffect:
        """Glow effect for selected/active elements."""
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(20)
        effect.setOffset(0, 0)
        effect.setColor(QColor(color))
        return effect

    @staticmethod
    def glow_subtle(color: str = RazerColors.GREEN_PRIMARY) -> QGraphicsDropShadowEffect:
        """Subtle glow for hover states."""
        effect = QGraphicsDropShadowEffect()
        effect.setBlurRadius(10)
        effect.setOffset(0, 0)
        c = QColor(color)
        c.setAlpha(100)
        effect.setColor(c)
        return effect


def apply_dark_theme(app: QApplication) -> None:
    """Apply a Razer-inspired dark theme."""
    palette = QPalette()

    # Base colors - dark with Razer green accents
    dark_bg = QColor(30, 30, 30)
    darker_bg = QColor(20, 20, 20)
    light_bg = QColor(45, 45, 45)
    text_color = QColor(220, 220, 220)
    disabled_text = QColor(120, 120, 120)
    razer_green = QColor(45, 160, 90)  # Softer green, easier on eyes
    highlight = razer_green
    link_color = QColor(70, 150, 90)

    # Window
    palette.setColor(QPalette.ColorRole.Window, dark_bg)
    palette.setColor(QPalette.ColorRole.WindowText, text_color)

    # Base (for text inputs, etc.)
    palette.setColor(QPalette.ColorRole.Base, darker_bg)
    palette.setColor(QPalette.ColorRole.AlternateBase, light_bg)

    # Text
    palette.setColor(QPalette.ColorRole.Text, text_color)
    palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, disabled_text)

    # Buttons
    palette.setColor(QPalette.ColorRole.Button, light_bg)
    palette.setColor(QPalette.ColorRole.ButtonText, text_color)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, disabled_text)

    # Highlights
    palette.setColor(QPalette.ColorRole.Highlight, highlight)
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)

    # Links
    palette.setColor(QPalette.ColorRole.Link, link_color)
    palette.setColor(QPalette.ColorRole.LinkVisited, QColor(80, 160, 80))

    # Tooltips
    palette.setColor(QPalette.ColorRole.ToolTipBase, dark_bg)
    palette.setColor(QPalette.ColorRole.ToolTipText, text_color)

    app.setPalette(palette)

    # Additional stylesheet for finer control
    app.setStyleSheet("""
        QMainWindow {
            background-color: #1e1e1e;
        }
        QGroupBox {
            border: 1px solid #3d3d3d;
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 8px;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
            color: #2da05a;
        }
        QPushButton {
            background-color: #2d2d2d;
            border: 1px solid #3d3d3d;
            border-radius: 4px;
            padding: 6px 16px;
            min-width: 80px;
        }
        QPushButton:hover {
            background-color: #3d3d3d;
            border-color: #2da05a;
        }
        QPushButton:pressed {
            background-color: #2da05a;
            color: black;
        }
        QPushButton:disabled {
            background-color: #1a1a1a;
            color: #666666;
        }
        QLineEdit, QSpinBox, QComboBox {
            background-color: #141414;
            border: 1px solid #3d3d3d;
            border-radius: 4px;
            padding: 4px;
        }
        QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
            border-color: #2da05a;
        }
        QListWidget, QTreeWidget, QTableWidget {
            background-color: #141414;
            border: 1px solid #3d3d3d;
            border-radius: 4px;
        }
        QListWidget::item:selected, QTreeWidget::item:selected {
            background-color: #2da05a;
            color: black;
        }
        QListWidget::item:hover, QTreeWidget::item:hover {
            background-color: #2d2d2d;
        }
        QTabWidget::pane {
            border: 1px solid #3d3d3d;
            border-radius: 4px;
        }
        QTabBar::tab {
            background-color: #2d2d2d;
            border: 1px solid #3d3d3d;
            padding: 8px 16px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: #2da05a;
            color: black;
        }
        QTabBar::tab:hover:!selected {
            background-color: #3d3d3d;
        }
        QSlider::groove:horizontal {
            background-color: #2d2d2d;
            height: 6px;
            border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background-color: #2da05a;
            width: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }
        QSlider::sub-page:horizontal {
            background-color: #2da05a;
            border-radius: 3px;
        }
        QScrollBar:vertical {
            background-color: #1a1a1a;
            width: 12px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical {
            background-color: #3d3d3d;
            min-height: 20px;
            border-radius: 6px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #2da05a;
        }
        QStatusBar {
            background-color: #141414;
            color: #888888;
        }
    """)
