# Copyright 2013-2023 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from typing import Union

import importlib
import importlib.machinery
import importlib.util
from pathlib import Path

# short name of the package
def short_name(package_name : str) -> str:
    return Path(package_name).stem

def load_package(package_name : str):
    # FIXME: just using file paths for now
    path = Path(package_name) / "package.py"
    clsname = short_name(package_name)

    fullname = package_name.replace('/', '.')
    loader = importlib.machinery.SourceFileLoader(fullname, str(path))
    spec   = importlib.util.spec_from_loader(fullname, loader)
    mod    = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)

    names = []
    for name in dir(mod):
        if name.lower() == clsname.lower():
            names.append(name)
    if len(names) > 1:
        raise ImportError("Multiple classes in module match {}".format(clsname))
    if len(names) == 0:
        raise ImportError("No class in module matching {}".format(clsname))
    return getattr(mod, names[0])
