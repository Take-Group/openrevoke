"""Slack agent: a Slack app that takes access requests from people in direct messages.

Setup (panel, ``app.services.slack_agent_setup``): an app configuration token
creates the app from a manifest (``manifest.py``) and sets its icon
(``avatar.py``); OAuth or a pasted bot token installs it; an app-level token
opens Socket Mode, so no public URL is needed.

Runtime (Temporal worker process, ``runner.py``): one Socket Mode connection
(``socket_mode.py``) gets direct messages and button clicks (``events.py``).
A message goes to the language model with three tools (``tools.py``); the
answer replaces a placeholder in the chat (``conversation.py``). A poll tells
admins about requests waiting for approval (``approvals.py``) and tells
people when their account is ready (``notifier.py``).
"""
