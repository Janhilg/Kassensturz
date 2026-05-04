_EXPORTS = {
    "AppPaths": ("web.app_paths", "AppPaths"),
    "KassensturzWebApp": ("web.kassensturz_web_app", "KassensturzWebApp"),
}


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(name)

    module_name, object_name = _EXPORTS[name]
    module = __import__(module_name, fromlist=[object_name])
    return getattr(module, object_name)


__all__ = [
    "AppPaths",
    "KassensturzWebApp",
]
