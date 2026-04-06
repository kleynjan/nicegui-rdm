"""
Multi-step dialog pattern for complex forms.

Usage:
    wizard = StepWizard(
        steps=[
            WizardStep(name="guest", title="Select Guest", render=render_step1),
            WizardStep(name="details", title="Details", render=render_step2),
        ],
        on_complete=handle_complete,
    )
    await wizard.show()

Pattern preserves the original manual_invite_dialog logic:
- State machine with step tracking
- Refreshable content per step
- Back/Next navigation
- Validation per step before proceeding
"""
from dataclasses import dataclass, field
from typing import Callable, Awaitable, Any

from nicegui import ui

from .button import Button
from .dialog import Dialog
from .layout import Row
from ..i18n import _


@dataclass
class WizardStep:
    """A single step in a wizard dialog."""
    name: str
    title: str
    render: Callable[[dict], Awaitable[None]]  # async render function, receives state
    validate: Callable[[dict], bool] | None = None  # optional validation, return True if valid
    next_label: str = ""
    back_label: str = ""

    def __post_init__(self):
        if not self.next_label:
            self.next_label = _("Next →")
        if not self.back_label:
            self.back_label = _("← Back")


@dataclass
class StepWizard:
    """Multi-step wizard dialog.

    Args:
        steps: List of WizardStep definitions
        on_complete: Async callback when wizard completes (receives state dict)
        cancel_label: Label for cancel button
        complete_label: Label for final step's complete button
    """
    steps: list[WizardStep]
    on_complete: Callable[[dict], Awaitable[None]]
    cancel_label: str = ""
    complete_label: str = ""

    def __post_init__(self):
        if not self.cancel_label:
            self.cancel_label = _("Cancel")
        if not self.complete_label:
            self.complete_label = _("Create")

    _state: dict = field(default_factory=dict, init=False)
    _dialog_state: dict = field(default_factory=dict, init=False)
    _current_step: int = field(default=0, init=False)
    _dlg: Dialog | None = field(default=None, init=False)
    _content: Any = field(default=None, init=False)

    @property
    def state(self) -> dict:
        """Access wizard state dict."""
        return self._state

    @property
    def current_step(self) -> WizardStep:
        """Get current step."""
        return self.steps[self._current_step]

    @property
    def is_first_step(self) -> bool:
        return self._current_step == 0

    @property
    def is_last_step(self) -> bool:
        return self._current_step == len(self.steps) - 1

    def _validate_current(self) -> bool:
        """Validate current step. Returns True if valid or no validator."""
        step = self.current_step
        if step.validate is None:
            return True
        return step.validate(self._state)

    async def _handle_next(self):
        """Handle next button click."""
        if not self._validate_current():
            return
        if self.is_last_step:
            await self._handle_complete()
        else:
            self._current_step += 1
            self._content.refresh()

    def _handle_back(self):
        """Handle back button click."""
        if not self.is_first_step:
            self._current_step -= 1
            self._content.refresh()

    async def _handle_complete(self):
        """Handle wizard completion."""
        if self._dlg:
            self._dlg.close()
        await self.on_complete(self._state)

    def _handle_cancel(self):
        """Handle cancel button click."""
        if self._dlg:
            self._dlg.close()

    async def show(self):
        """Show the wizard dialog."""
        self._current_step = 0

        with Dialog(state=self._dialog_state) as self._dlg:
            @ui.refreshable
            async def _content():
                step = self.current_step
                ui.label(step.title).classes('dialog-header')

                await step.render(self._state)

                with Row(classes='rdm-edit-actions'):
                    # Next/Complete button
                    if self.is_last_step:
                        Button(self.complete_label, on_click=self._handle_next)
                    else:
                        Button(step.next_label, on_click=self._handle_next)

                    # Back button (not on first step)
                    if not self.is_first_step:
                        Button(step.back_label, on_click=self._handle_back)

                    # Cancel button
                    Button(self.cancel_label, on_click=self._handle_cancel, color="secondary")

            self._content = _content
            await _content()

        self._dlg.open()
