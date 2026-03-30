try:
    from importlib.metadata import version
    __version__ = version("ezmig")
except Exception:
    __version__ = "0.0.0-dev"
