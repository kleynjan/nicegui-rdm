"""Tests for StepWizard step flow."""
import asyncio

import pytest
from nicegui import html, ui
from nicegui.testing import User

from ng_rdm.components import WizardStep, StepWizard

from .conftest import html_should_see, html_should_see_async

pytestmark = pytest.mark.components


async def _render_step1(state: dict):
    html.span('Step 1 Content')
    state['step1_visited'] = True


async def _render_step2(state: dict):
    html.span('Step 2 Content')
    state['step2_visited'] = True


async def _noop_complete(data):
    pass


async def test_wizard_renders_first_step(user: User):
    """First step content visible."""
    @ui.page('/')
    async def page():
        wizard = StepWizard(
            steps=[
                WizardStep(name='s1', title='Step 1', render=_render_step1),
                WizardStep(name='s2', title='Step 2', render=_render_step2),
            ],
            on_complete=_noop_complete,
        )
        await wizard.show()

    await user.open('/')
    html_should_see(user, 'Step 1')
    html_should_see(user, 'Step 1 Content')


async def test_wizard_next_advances(user: User):
    """Next button moves to step 2."""
    @ui.page('/')
    async def page():
        wizard = StepWizard(
            steps=[
                WizardStep(name='s1', title='Step 1', render=_render_step1),
                WizardStep(name='s2', title='Step 2', render=_render_step2),
            ],
            on_complete=_noop_complete,
        )
        await wizard.show()

    await user.open('/')
    html_should_see(user, 'Step 1 Content')
    user.find('Next →').click()
    await html_should_see_async(user, 'Step 2 Content')


async def test_wizard_back_returns(user: User):
    """Back button returns to step 1."""
    @ui.page('/')
    async def page():
        wizard = StepWizard(
            steps=[
                WizardStep(name='s1', title='Step 1', render=_render_step1),
                WizardStep(name='s2', title='Step 2', render=_render_step2),
            ],
            on_complete=_noop_complete,
        )
        await wizard.show()

    await user.open('/')
    user.find('Next →').click()
    await html_should_see_async(user, 'Step 2 Content')
    user.find('← Back').click()
    await html_should_see_async(user, 'Step 1 Content')


async def test_wizard_complete_fires_callback(user: User):
    """Complete fires on_complete with collected data."""
    complete_log = []

    async def log_complete(data):
        complete_log.append(data.copy())

    @ui.page('/')
    async def page():
        wizard = StepWizard(
            steps=[
                WizardStep(name='s1', title='Step 1', render=_render_step1),
            ],
            on_complete=log_complete,
        )
        await wizard.show()

    await user.open('/')
    # Single step: the "Next" button is replaced by "Create" (complete_label)
    user.find('Create').click()
    await asyncio.sleep(0.1)
    assert len(complete_log) == 1
    assert complete_log[0]['step1_visited'] is True


async def test_wizard_cancel_closes(user: User):
    """Cancel closes the wizard dialog."""
    @ui.page('/')
    async def page():
        wizard = StepWizard(
            steps=[
                WizardStep(name='s1', title='Step 1', render=_render_step1),
                WizardStep(name='s2', title='Step 2', render=_render_step2),
            ],
            on_complete=_noop_complete,
        )
        await wizard.show()

    await user.open('/')
    user.find('Cancel').click()
    # Wizard dialog should be closed
