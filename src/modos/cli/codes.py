from typing import Optional
from typing_extensions import Annotated

import typer

from modos.codes import SLOT_TERMINOLOGIES

codes = typer.Typer(add_completion=False)


@codes.command()
def search(
    ctx: typer.Context,
    slot: Annotated[
        str,
        typer.Argument(
            ...,
            help=f"The slot to search for codes. Possible values are {', '.join(SLOT_TERMINOLOGIES.keys())}",
        ),
    ],
    query: Annotated[
        Optional[str],
        typer.Option(
            "--query", "-q", help="Predefined text to use when search codes."
        ),
    ] = None,
    top: Annotated[
        int,
        typer.Option(
            "--top",
            "-t",
            help="Show at most N codes when using a prefedined query.",
        ),
    ] = 50,
):
    """Search for terminology codes using free text."""
    from modos.codes import get_slot_matcher
    from modos.prompt import fuzzy_complete
    from modos.remote import EndpointManager

    matcher = get_slot_matcher(
        slot,
        EndpointManager(ctx.obj["endpoint"]).fuzon,
    )
    matcher.top = top
    if query:
        matches = matcher.find_codes(query)
        out = "\n".join([f"{m.uri} | {m.label}" for m in matches])
    else:
        out = fuzzy_complete(
            prompt_txt=f'Browsing terms for slot "{slot}". Use tab to cycle suggestions.\n> ',
            matcher=matcher,
        )
    print(out)
