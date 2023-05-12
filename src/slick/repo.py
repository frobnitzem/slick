# Copyright 2013-2023 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import importlib
import importlib.machinery
import importlib.util
from pathlib import Path

#: Package modules are imported as spack.pkg.<repo-namespace>.<pkg-name>
ROOT_PYTHON_NAMESPACE = "spack.pkg"

def filename_for_package_name(root, package_name) -> Path:
    """Return the python file defining this package.

    For instance:

        filename_for_package_name('.', 'hdf5') == './hdf5/package.py'

    Args:
        package_name (str): name of the package
    """
    return Path(root) / package_name / 'package.py'

def load_package(repo, package_name):
    root = Path('.') # FIXME: compute from repo name
    path = filename_for_package_name(root, package_name)

    fullname = f"{ROOT_PYTHON_NAMESPACE}.{repo}.{package_name}"
    loader = importlib.machinery.SourceFileLoader(fullname, str(path))
    spec = importlib.util.spec_from_loader(fullname, loader)
    mod = importlib.util.module_from_spec(spec)
    return loader.exec_module(mod)
