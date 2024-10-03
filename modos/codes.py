"""Utilities to automatically find / recommend terminology codes from text."""
from dataclasses import dataclass
import requests
from typing import Optional, Protocol


SLOT_TERMINOLOGIES = {
    "cell_type": "https://purl.obolibrary.org/obo/cl.owl",
    "source_material": "https://purl.obolibrary.org/obo/uberon.owl",
    "taxon_id": "https://purl.obolibrary.org/obo/ncbitaxon/subsets/taxslim.owl",
}


@dataclass
class Code:
    label: str
    uri: str


class CodeMatcher(Protocol):
    def find_codes(self, query: str) -> list[Code]:
        ...


class LocalCodeMatcher(CodeMatcher):
    """Find ontology codes for a given text by running a local term matcher."""

    def __init__(self, slot: str):
        self.slot = slot
        try:
            from pyfuzon import TermMatcher

            self.matcher = TermMatcher.from_files([SLOT_TERMINOLOGIES[slot]])
        except ImportError:
            raise ValueError(
                """No endpoint provided and pyfuzon not installed,
                cannot do code matching."""
            )

    def find_codes(self, query: str) -> list[Code]:
        return self.matcher.top(query, 50)


class RemoteCodeMatcher(CodeMatcher):
    """Find ontology codes for a given text relying on a remote term matcher."""

    def __init__(self, slot: str, endpoint: str):
        self.endpoint = endpoint
        self.slot = slot

    def find_codes(self, query: str) -> list[Code]:
        codes = requests.get(
            f"{self.endpoint}/top?collection={self.slot}&query={query}&top=50"
        ).json()["codes"]
        return [Code(label=code["label"], uri=code["uri"]) for code in codes]


def get_slot_matchers(
    endpoint: Optional[str] = None,
) -> dict[str, CodeMatcher]:
    """Instantiates a code matcher for each slot. If the endpoint is provided, remote matchers are used."""
    matchers = {}
    for slot in SLOT_TERMINOLOGIES.keys():
        if endpoint:
            matchers[slot] = RemoteCodeMatcher(slot, endpoint)
        else:
            matchers[slot] = LocalCodeMatcher(slot)
    return matchers
