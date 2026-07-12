"""loom-datagen — synthetic source data generator for the Loom warehouse."""

import importlib.metadata

try:
    __version__ = importlib.metadata.version("loom-datagen")
except importlib.metadata.PackageNotFoundError:  # not installed (e.g. raw source tree)
    __version__ = "0.0.0"
