.. scaldys-project documentation master file

Welcome to scaldys-project's documentation!
============================================

``scaldys-project`` automates the complete Windows distribution pipeline for
Python projects — from Sphinx documentation through Cython compilation,
PyInstaller bundling, and Inno Setup installer creation — all driven by a
single command.

If you are starting a new project, `scaldys-template
<https://github.com/scaldys/scaldys-template>`_ gives you a ready-to-use
project scaffold with ``scaldys-project`` already integrated: packaging
scripts, Sphinx documentation, CI/CD workflows, and a working
``builder.toml`` — nothing to wire up manually.

Start with the :ref:`overview` for a high-level picture, or jump straight to
:ref:`installation` and :ref:`quickstart` to get up and running.

Documentation Contents
----------------------

.. toctree::
   :maxdepth: 2
   :caption: Users

   users/overview
   users/installation
   users/quickstart
   users/cli_usage
   users/topics/index

.. toctree::
   :maxdepth: 2
   :caption: Developers

   developers/architecture
   developers/extension_points
   developers/contributing

.. toctree::
   :maxdepth: 1
   :caption: About

   changelog
   authors
   license
   help


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
