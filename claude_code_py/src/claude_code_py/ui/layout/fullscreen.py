from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Static

from claude_code_py.ui.textual.widgets import (
    PromptComposer,
    PromptOverlayWidget,
    TranscriptWidget,
)


class ReplFullscreenLayout(Static):
    DEFAULT_CSS = """
    ReplFullscreenLayout {
        layout: vertical;
        height: 1fr;
        background: rgb(0,0,0);
        color: rgb(255,255,255);
        padding: 0;
    }

    #scroll-region {
        height: 1fr;
        background: rgb(0,0,0);
    }

    #transcript {
        height: 1fr;
        border: none;
        background: rgb(0,0,0);
        padding: 0;
    }

    #overlay-slot {
        display: none;
        height: auto;
        margin: 0 1;
    }

    #modal-slot {
        display: none;
        height: auto;
        margin: 0 1;
    }

    #prompt-slot {
        border-top: solid rgb(136,136,136);
        background: rgb(0,0,0);
        padding: 0 1 1 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="scroll-region"):
            yield TranscriptWidget(id="transcript")
            yield Container(id="overlay-slot")
            yield Container(id="modal-slot")
        yield PromptOverlayWidget(id="prompt-overlay-slot")
        yield PromptComposer(id="prompt-slot")

    def transcript_widget(self) -> TranscriptWidget:
        return self.query_one("#transcript", TranscriptWidget)

    def prompt_composer(self) -> PromptComposer:
        return self.query_one("#prompt-slot", PromptComposer)

    def prompt_overlay_widget(self) -> PromptOverlayWidget:
        return self.query_one("#prompt-overlay-slot", PromptOverlayWidget)

    def set_overlay(self, widget) -> None:
        container = self.query_one("#overlay-slot", Container)
        container.remove_children()
        if widget is not None:
            container.display = True
            container.mount(widget)

    def clear_overlay(self) -> None:
        container = self.query_one("#overlay-slot", Container)
        container.remove_children()
        container.display = False

    def set_modal(self, widget) -> None:
        container = self.query_one("#modal-slot", Container)
        container.remove_children()
        if widget is not None:
            container.display = True
            container.mount(widget)

    def clear_modal(self) -> None:
        container = self.query_one("#modal-slot", Container)
        container.remove_children()
        container.display = False
