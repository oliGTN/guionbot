# -*- coding: utf-8 -*-
from datetime import datetime
from contextlib import contextmanager
from contextvars import ContextVar
import inspect
import uuid

import config


# Context is local to the current async task and is inherited by asyncio tasks
# created inside that context. Keep defaults empty so legacy log calls are
# unchanged until an operation context is explicitly established.
_log_operation = ContextVar("guionbot_log_operation", default=None)
_log_run_id = ContextVar("guionbot_log_run_id", default=None)
_log_parent_run_id = ContextVar("guionbot_log_parent_run_id", default=None)


def new_run_id():
    """Return a short identifier for one command execution or loop iteration."""
    return uuid.uuid4().hex[:8]


def get_log_context():
    """Return the current logging context as a dictionary."""
    return {
        "operation": _log_operation.get(),
        "run_id": _log_run_id.get(),
        "parent_run_id": _log_parent_run_id.get(),
    }


def set_log_context(operation, run_id=None, parent_run_id=None):
    """
    Set context for a new operation and return tokens for restoring the old
    context. If nested, the current run_id becomes the default parent_run_id.
    Always pair this with reset_log_context(), preferably in a finally block.
    """
    current_run_id = _log_run_id.get()
    if run_id is None:
        run_id = new_run_id()
    if parent_run_id is None:
        parent_run_id = current_run_id

    tokens = (
        _log_operation.set(str(operation) if operation is not None else None),
        _log_run_id.set(str(run_id) if run_id is not None else None),
        _log_parent_run_id.set(
            str(parent_run_id) if parent_run_id is not None else None
        ),
    )
    return tokens


def reset_log_context(tokens):
    """Restore the context returned by set_log_context()."""
    operation_token, run_id_token, parent_run_id_token = tokens
    _log_parent_run_id.reset(parent_run_id_token)
    _log_run_id.reset(run_id_token)
    _log_operation.reset(operation_token)


@contextmanager
def operation_context(operation, run_id=None, parent_run_id=None):
    """
    Context manager for one command execution or background-loop iteration.

    Works across await calls:
        with golog.operation_context("update_rpc_60secs"):
            await do_work()
    """
    tokens = set_log_context(operation, run_id, parent_run_id)
    try:
        yield _log_run_id.get()
    finally:
        reset_log_context(tokens)


################################################
# function: log
################################################
def log(level, txt, identifier=None):
    now = datetime.now()
    dt_string = now.strftime("%Y/%m/%d %H:%M:%S")
    stack = inspect.stack()
    caller = stack[1]
    module_name = caller.filename.split("/")[-1][:-3]
    fct = module_name + "." + caller.function
    code_line = caller.lineno

    context = get_log_context()
    context_parts = []
    if context["operation"] is not None:
        context_parts.append("op=" + context["operation"])
    if context["run_id"] is not None:
        context_parts.append("run=" + context["run_id"])
    if context["parent_run_id"] is not None:
        context_parts.append("parent=" + context["parent_run_id"])
    context_txt = "[" + " ".join(context_parts) + "]" if context_parts else ""

    if identifier is not None:
        id_txt = "[" + str(identifier) + "]"
    else:
        id_txt = ""

    log_string = (
        dt_string + ":" + level + ":" + fct + "[" + str(code_line) + "]:"
        + context_txt + id_txt + str(txt)
    )

    if level == "DBG":
        if config.LOG_LEVEL == "DBG":
            print(log_string, flush=True)
    else:
        print(log_string, flush=True)
