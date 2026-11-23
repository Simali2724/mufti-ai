from contextvars import ContextVar
progress_sink=ContextVar('progress_sink',default=None)
async def report(task,provider,model,status):
    sink=progress_sink.get()
    if sink is not None:
        await sink({'task':task,'provider':provider,'model':model,'state':status,'message':f'{task.title()} · {provider} / {model} · {status}'})
async def draft_token(text):
    """Live draft text for the reader while a long explanation is being written.

    The final answer replaces the draft once it has been checked, so these tokens are a
    preview only. Streaming matters most on the local 2 GB GPU, where an explanation takes
    minutes: the reader watches it being written instead of staring at a spinner.
    """
    sink=progress_sink.get()
    if sink is not None and text:
        await sink({'kind':'draft','text':text})
async def draft_reset():
    """The provider failed mid-answer and another one is starting: discard the preview."""
    sink=progress_sink.get()
    if sink is not None:
        await sink({'kind':'draft_reset'})
