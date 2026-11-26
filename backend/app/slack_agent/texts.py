"""Messages the agent sends without the language model."""

from typing import Any

from app.models.enums import AccessRequestStatus, ActionKind

WORKING = "_Working on it…_"
UNKNOWN_PERSON = (
    "I can't find you among the people in Open Revoke{email}. Ask an admin to add you, then write to me again."
)
LEFT = "Your profile in Open Revoke is marked as someone who left the company, so I can't request access for you."
NO_MODEL = "I'm not fully set up yet: an admin has to choose the AI model in Open Revoke settings."
AI_FAILED = "Sorry, I couldn't answer right now ({error}). Try again in a minute."
FAILED = "Sorry, something went wrong on my side. Try again in a minute."
UNKNOWN_DECIDER = "I can't tell who you are: your Slack profile has no e-mail. Decide in Open Revoke instead."


def unknown_person(email: str | None) -> str:
    return UNKNOWN_PERSON.format(email=f" (your Slack e-mail is {email})" if email else "")


def finished(app_name: str, status: AccessRequestStatus, action: Any | None, comment: str | None = None) -> str:
    if status == AccessRequestStatus.DONE:
        email = (action.payload or {}).get("email") if action is not None else None
        text = f":white_check_mark: Your *{app_name}* account is ready" + (f" ({email})." if email else ".")
        if action is not None and action.secret_result_encrypted is not None:
            text += " An admin will send you the sign-in details."
        elif action is not None and action.kind == ActionKind.MANUAL_TASK:
            text += " An admin set it up; ask them if you did not get the sign-in details."
        else:
            text += " Check your inbox for an invitation from the app."
        return text
    if status == AccessRequestStatus.FAILED:
        return (
            f":x: I couldn't create your *{app_name}* account. An admin can see what went wrong in Open Revoke "
            "and fix it."
        )
    if status == AccessRequestStatus.REJECTED:
        text = f":no_entry_sign: Your request for *{app_name}* was rejected."
        return text + (f"\n> {_quote(comment)}" if comment else "")
    return f"Your request for *{app_name}* was cancelled. Ask an admin if you think it should not be."


def approval_request(
    *,
    person_name: str,
    person_email: str,
    app_name: str,
    justification: str | None,
    role: str | None,
    for_manager: bool,
    requested_by: str | None = None,
) -> str:
    who = f"*{person_name}* ({person_email})"
    text = f"{who} asks for an account in *{app_name}*" + (f" with the role _{role}_." if role else ".")
    if requested_by and requested_by != person_email:
        text += f"\nAsked by {requested_by}."
    if justification:
        text += f"\n> {_quote(justification)}"
    text += "\nYou decide as their manager." if for_manager else "\nAn admin decides this step."
    return text


def _quote(text: str) -> str:
    return text.replace("\n", " ")[:300]
