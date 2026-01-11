"""Animation utilities for smooth UI transitions and effects."""

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QSequentialAnimationGroup,
    QVariantAnimation,
)
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsOpacityEffect, QWidget


class RazerAnimations:
    """Factory for creating smooth animations with Razer aesthetic."""

    # Duration constants (milliseconds)
    DURATION_INSTANT = 50
    DURATION_FAST = 150
    DURATION_NORMAL = 250
    DURATION_SLOW = 400
    DURATION_EXTRA_SLOW = 600

    # Easing curves for different contexts
    EASE_OUT = QEasingCurve.Type.OutCubic
    EASE_IN_OUT = QEasingCurve.Type.InOutCubic
    EASE_BOUNCE = QEasingCurve.Type.OutBack
    EASE_ELASTIC = QEasingCurve.Type.OutElastic

    @staticmethod
    def fade_in(
        widget: QWidget,
        duration: int = 250,
        start_opacity: float = 0.0,
        end_opacity: float = 1.0,
    ) -> QPropertyAnimation:
        """
        Create a fade-in animation for a widget.

        Args:
            widget: Target widget
            duration: Animation duration in ms
            start_opacity: Starting opacity (0.0 to 1.0)
            end_opacity: Ending opacity (0.0 to 1.0)

        Returns:
            Configured QPropertyAnimation (call .start() to run)
        """
        effect = widget.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)

        effect.setOpacity(start_opacity)

        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(duration)
        anim.setStartValue(start_opacity)
        anim.setEndValue(end_opacity)
        anim.setEasingCurve(RazerAnimations.EASE_OUT)
        return anim

    @staticmethod
    def fade_out(
        widget: QWidget,
        duration: int = 250,
        start_opacity: float = 1.0,
        end_opacity: float = 0.0,
    ) -> QPropertyAnimation:
        """Create a fade-out animation for a widget."""
        return RazerAnimations.fade_in(widget, duration, start_opacity, end_opacity)

    @staticmethod
    def shadow_lift(
        shadow_effect,
        duration: int = 150,
        start_blur: int = 12,
        end_blur: int = 20,
    ) -> QPropertyAnimation:
        """
        Animate shadow blur radius to create a "lift" effect on hover.

        Args:
            shadow_effect: QGraphicsDropShadowEffect to animate
            duration: Animation duration in ms
            start_blur: Starting blur radius
            end_blur: Ending blur radius

        Returns:
            Configured QPropertyAnimation
        """
        anim = QPropertyAnimation(shadow_effect, b"blurRadius")
        anim.setDuration(duration)
        anim.setStartValue(start_blur)
        anim.setEndValue(end_blur)
        anim.setEasingCurve(RazerAnimations.EASE_OUT)
        return anim

    @staticmethod
    def shadow_drop(
        shadow_effect,
        duration: int = 150,
        start_blur: int = 20,
        end_blur: int = 12,
    ) -> QPropertyAnimation:
        """Animate shadow blur radius back down after hover ends."""
        return RazerAnimations.shadow_lift(shadow_effect, duration, start_blur, end_blur)

    @staticmethod
    def color_transition(
        start_color: QColor,
        end_color: QColor,
        duration: int = 250,
        callback=None,
    ) -> QVariantAnimation:
        """
        Create a smooth color transition animation.

        Args:
            start_color: Starting QColor
            end_color: Ending QColor
            duration: Animation duration in ms
            callback: Function to call with interpolated color on each frame

        Returns:
            Configured QVariantAnimation
        """
        anim = QVariantAnimation()
        anim.setDuration(duration)
        anim.setStartValue(start_color)
        anim.setEndValue(end_color)
        anim.setEasingCurve(RazerAnimations.EASE_IN_OUT)

        if callback:
            anim.valueChanged.connect(callback)

        return anim

    @staticmethod
    def pulse(
        widget: QWidget,
        duration: int = 600,
        min_opacity: float = 0.6,
        max_opacity: float = 1.0,
        loop: bool = True,
    ) -> QSequentialAnimationGroup:
        """
        Create a pulsing opacity animation for attention.

        Args:
            widget: Target widget
            duration: Full cycle duration in ms
            min_opacity: Minimum opacity during pulse
            max_opacity: Maximum opacity during pulse
            loop: Whether to loop indefinitely

        Returns:
            Configured QSequentialAnimationGroup
        """
        effect = widget.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)

        group = QSequentialAnimationGroup()

        # Fade out
        fade_out = QPropertyAnimation(effect, b"opacity")
        fade_out.setDuration(duration // 2)
        fade_out.setStartValue(max_opacity)
        fade_out.setEndValue(min_opacity)
        fade_out.setEasingCurve(QEasingCurve.Type.InOutSine)
        group.addAnimation(fade_out)

        # Fade in
        fade_in = QPropertyAnimation(effect, b"opacity")
        fade_in.setDuration(duration // 2)
        fade_in.setStartValue(min_opacity)
        fade_in.setEndValue(max_opacity)
        fade_in.setEasingCurve(QEasingCurve.Type.InOutSine)
        group.addAnimation(fade_in)

        if loop:
            group.setLoopCount(-1)  # Infinite loop

        return group

    @staticmethod
    def scale_bounce(
        widget: QWidget,
        duration: int = 300,
        scale_factor: float = 1.1,
    ) -> QSequentialAnimationGroup:
        """
        Create a scale bounce effect (grow then return).

        Note: Requires widget to have a custom scale property or use transform.
        This is a placeholder for future implementation.
        """
        # Qt doesn't have native scale animation for widgets
        # Would need to implement using QTransform or custom painting
        group = QSequentialAnimationGroup()
        return group


class AnimatedWidget(QWidget):
    """
    Base class for widgets with built-in animation support.

    Provides convenient methods for common animations.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._animations: list[QPropertyAnimation] = []
        self._opacity_effect: QGraphicsOpacityEffect | None = None

    def fade_in(self, duration: int = 250) -> None:
        """Fade the widget in."""
        anim = RazerAnimations.fade_in(self, duration)
        anim.start()
        self._animations.append(anim)

    def fade_out(self, duration: int = 250) -> None:
        """Fade the widget out."""
        anim = RazerAnimations.fade_out(self, duration)
        anim.start()
        self._animations.append(anim)

    def stop_all_animations(self) -> None:
        """Stop all running animations on this widget."""
        for anim in self._animations:
            anim.stop()
        self._animations.clear()


class HoverAnimationMixin:
    """
    Mixin class to add hover shadow animations to any QWidget with a shadow effect.

    Usage:
        class MyCard(QFrame, HoverAnimationMixin):
            def __init__(self):
                super().__init__()
                self._setup_hover_animation()
    """

    _hover_anim: QPropertyAnimation | None = None
    _shadow_blur_normal: int = 12
    _shadow_blur_hover: int = 20

    def _setup_hover_animation(self, normal_blur: int = 12, hover_blur: int = 20) -> None:
        """Initialize hover animation settings."""
        self._shadow_blur_normal = normal_blur
        self._shadow_blur_hover = hover_blur

    def enterEvent(self, event) -> None:
        """Handle mouse enter - lift shadow."""
        effect = self.graphicsEffect()
        if effect and hasattr(effect, "blurRadius"):
            if self._hover_anim:
                self._hover_anim.stop()
            self._hover_anim = RazerAnimations.shadow_lift(
                effect,
                duration=150,
                start_blur=self._shadow_blur_normal,
                end_blur=self._shadow_blur_hover,
            )
            self._hover_anim.start()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        """Handle mouse leave - drop shadow."""
        effect = self.graphicsEffect()
        if effect and hasattr(effect, "blurRadius"):
            if self._hover_anim:
                self._hover_anim.stop()
            self._hover_anim = RazerAnimations.shadow_drop(
                effect,
                duration=150,
                start_blur=self._shadow_blur_hover,
                end_blur=self._shadow_blur_normal,
            )
            self._hover_anim.start()
        super().leaveEvent(event)
