"""Read native selection or browse-mode selection without touching the clipboard."""
import api
import textInfos


def get_selected_word():
    obj = api.getFocusObject()
    if obj is None:
        return ''
    # Same browse-mode choice used by NVDA's selection reporting commands.
    interceptor = getattr(obj, 'treeInterceptor', None)
    if interceptor is not None and getattr(interceptor, 'isReady', False) and not getattr(interceptor, 'passThrough', True):
        obj = interceptor
    try:
        info = obj.makeTextInfo(textInfos.POSITION_SELECTION)
        if info.isCollapsed:
            return ''
        value = info.text.strip()
        # Do not silently truncate a paragraph into a different word.
        return value if len(value) <= 200 else ''
    except (RuntimeError, NotImplementedError, LookupError, AttributeError):
        return ''
