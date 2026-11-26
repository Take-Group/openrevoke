"""``manager_email`` of the people CSV import: resolve each row's manager and refuse loops.

A manager is a stored person (primary e-mail or alias) or another row of the file (its e-mail or a
new alias). A row whose manager is a row with errors fails too, because that person will not be
stored; the check runs again until no row changes.
"""

from typing import TYPE_CHECKING

from app.services.people_managers import creates_cycle

if TYPE_CHECKING:
    from app.services.people_import import Directory, RowPlan


def resolve_managers(plans: list[RowPlan], directory: Directory) -> None:
    """Sets ``plan.manager`` (the manager's primary e-mail) or adds a row error."""
    by_line = {plan.line: plan for plan in plans}
    base = {
        person.primary_email: directory.by_id[person.manager_id].primary_email
        for person in directory.by_email.values()
        if person.manager_id is not None and person.manager_id in directory.by_id
    }
    changed = True
    while changed:
        changed = False
        graph = dict(base)
        for plan in plans:
            if plan.errors or plan.manager_email is None or plan.email is None:
                plan.manager = None
                continue
            target, error = _target(plan.manager_email, directory, by_line)
            if error is None and target == plan.email:
                error = "A person cannot be their own manager"
            elif error is None and target is not None and creates_cycle(graph, plan.email, target):
                error = f"Manager {target} already reports to {plan.email}, directly or through others (a loop)"
            if error is not None:
                plan.errors.append(error)
                plan.manager = None
                changed = True
                break
            plan.manager = target
            graph[plan.email] = target


def _target(email: str, directory: Directory, by_line: dict[int, RowPlan]) -> tuple[str | None, str | None]:
    """(manager's primary e-mail, None) or (None, error)."""
    if email in directory.by_email:
        return email, None
    owner = directory.alias_owner.get(email)
    if owner is not None and owner in directory.by_id:
        return directory.by_id[owner].primary_email, None
    line = directory.file_emails.get(email)
    row = by_line.get(line) if line is not None else None
    if row is None:
        return None, f"Manager {email} is not a person in Open Revoke or a row of this file"
    if row.errors or row.email is None:
        return None, f"Manager {email} is on line {row.line}, which has errors"
    return row.email, None
