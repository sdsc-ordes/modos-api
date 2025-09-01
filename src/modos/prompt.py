from collections.abc import Mapping
from datetime import date
import importlib.util
import re
from typing import Any

import click
from loguru import logger
from prompt_toolkit import prompt
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document
import typer

from modos.codes import CodeMatcher, get_slot_matchers
from modos.helpers.schema import (
    get_enum_values,
    get_slots,
    get_slot_range,
    load_schema,
)

from modos.remote import EndpointManager


def is_fuzon_available(endpoint: EndpointManager | None) -> bool:
    """Check if fuzon is available on server or client side."""

    if endpoint and endpoint.fuzon:
        return True
    if importlib.util.find_spec("pyfuzon"):
        return True
    return False


class SlotCodeCompleter(Completer):
    """Auto-suggestions for terminology codes."""

    def __init__(self, matcher: CodeMatcher):
        self.matcher: CodeMatcher = matcher

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ):
        for rec in self.matcher.find_codes(document.text):
            yield Completion(
                f"{rec.label} {rec.uri}",
                start_position=-document.cursor_position,
            )


def fuzzy_complete(prompt_txt: str, matcher: CodeMatcher):
    """Given a pre-configured matcher, prompt the user with live auto-suggestions."""
    result = prompt(
        f"{prompt_txt}: ",
        completer=SlotCodeCompleter(matcher),
        complete_while_typing=True,
    )

    # If the user selected a suggestion with a URI, return that URI.
    if match := re.match(r".* <(http[^>]*)>$", result):
        uri = match.groups()[0]
        return uri
    return result


class SlotPrompter:
    """Introspects the schema to prompt the user for values based on input class/slot.

    Parameters
    ---------
    endpoint:
        Endpoint running a fuzon server for code matching.
    suggest:
        Whether to generate auto-suggestion dynamically.
    prompt:
        Override the default prompt messages.
    """

    def __init__(
        self,
        endpoint: EndpointManager | None = None,
        suggest: bool = True,
        prompt: str | None = None,
    ):
        self.prompt = prompt
        if not suggest:
            self.slot_matchers = {}
            return

        if is_fuzon_available(endpoint):
            self.slot_matchers = get_slot_matchers(endpoint.fuzon)
        else:
            logger.warning("fuzon not available, disabling code suggestions.")
            self.slot_matchers = {}

    def prompt_for_slot(self, slot_name: str, optional: bool = False):
        slot_range = get_slot_range(slot_name)
        choices, default = None, None
        if slot_range == "datetime":
            default = date.today()
        elif load_schema().get_enum(slot_range):
            choices = click.Choice(get_enum_values(slot_range))
        elif optional:
            default = ""

        # generate slot-specific prompt unless overridden
        if self.prompt is None:
            prefix = "(optional) " if optional else "(required) "
            prompt = f"{prefix}Enter a value for {slot_name}"
        else:
            prompt = self.prompt

        if slot_name in self.slot_matchers:
            output = fuzzy_complete(prompt, self.slot_matchers[slot_name])
        else:
            output = typer.prompt(
                prompt,
                default=default,
                type=choices,
            )

        if output == "":
            output = None

        return output

    def prompt_for_slots(
        self,
        target_class: type,
        exclude: Mapping[str, list[str]] | None = None,
    ) -> dict[str, Any]:
        """Prompt the user to provide values for the slots of input class.
        values of required fields can be excluded to repeat the prompt.

        Parameters
            ----------
            target_class
                Class to build
            exclude
                Mapping with the name of a slot as key  and list of invalid entries as values.
        """

        entries = {}
        required_slots = set(get_slots(target_class, required_only=True))
        optional_slots = (
            set(get_slots(target_class, required_only=False)) - required_slots
        )

        # Always require identifiers
        if "id" in optional_slots:
            optional_slots.remove("id")
            required_slots.add("id")

        for slot_name in required_slots:
            entries[slot_name] = self.prompt_for_slot(slot_name)
            if entries[slot_name] is None:
                raise ValueError(f"Missing required slot: {slot_name}")
            if exclude and entries.get(slot_name) in exclude.get(
                slot_name, []
            ):
                print(
                    f"Invalid value: {slot_name} must differ from {exclude[slot_name]}."
                )
                entries[slot_name] = self.prompt_for_slot(slot_name)

        if optional_slots:
            for slot_name in optional_slots:
                entries[slot_name] = self.prompt_for_slot(
                    slot_name, optional=True
                )
        return entries
