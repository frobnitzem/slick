.. These are examples of badges you might want to add to your README:
   please update the URLs accordingly

    .. image:: https://api.cirrus-ci.com/github/<USER>/slick.svg?branch=main
        :alt: Built Status
        :target: https://cirrus-ci.com/github/<USER>/slick
    .. image:: https://readthedocs.org/projects/slick/badge/?version=latest
        :alt: ReadTheDocs
        :target: https://slick.readthedocs.io/en/stable/
    .. image:: https://img.shields.io/coveralls/github/<USER>/slick/main.svg
        :alt: Coveralls
        :target: https://coveralls.io/r/<USER>/slick
    .. image:: https://img.shields.io/pypi/v/slick.svg
        :alt: PyPI-Server
        :target: https://pypi.org/project/slick/
    .. image:: https://img.shields.io/conda/vn/conda-forge/slick.svg
        :alt: Conda-Forge
        :target: https://anaconda.org/conda-forge/slick
    .. image:: https://pepy.tech/badge/slick/month
        :alt: Monthly Downloads
        :target: https://pepy.tech/project/slick
    .. image:: https://img.shields.io/twitter/url/http/shields.io.svg?style=social&label=Twitter
        :alt: Twitter
        :target: https://twitter.com/slick

.. image:: https://img.shields.io/badge/-PyScaffold-005CA0?logo=pyscaffold
    :alt: Project generated with PyScaffold
    :target: https://pyscaffold.org/

|

=====
slick
=====


  Slick package manager.

A package manager built for a single purpose -- transform a spec into a
build description.  Build descriptions are often complicated by many
things that could be solved with conventions:

  * What build commands do I run?

  * What build options are available, and which work together?

  * Where are my dependencies?

    - What build options did they use?

Slick accomplishes the build description translation by defining
and adhering to conventions:

  - Describe what it is instead of how to use it.

    Slick's implementation is based entirely on structured data.
    We do not try to monopolize the interfaces to that data by
    building unnecessary abstraction layers -- like commands on top
    of commands or configuration on top of configuration.

    Each piece of data that slick works with is user-accessible,
    and has a canonical path where it can be found.

  - Don't do more than necessary.

    Command-line utilities run the same way tests do:
    set up classes, call functions, then exit.

  - Be modular.

    Import paths should form a tree or a DAG, not a rats nest.
    If a sub-tree gets too big, it can and will be split into
    a separate python package.

