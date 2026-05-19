.. _topics:

****************
In-Depth Guides
****************

These guides provide detailed explanations of each component and concept in
``scaldys-project``.  Use them when you need to go beyond the quickstart —
to understand exactly what a build step does, tune its behaviour, or
troubleshoot an issue.

.. toctree::
   :maxdepth: 2

   project_initialization
   project_layout
   configuration
   scaldys_project_toml_reference
   compliance_checking
   documentation_building
   cython_compilation
   windows_exe
   windows_installer

Guide summaries
===============

:ref:`project_initialization`
    How to scaffold a new scaldys-compliant project from ``scaldys-template``
    using ``scaldys-project init`` — the interactive wizard, substitution map,
    excluded items, and post-init actions.

:ref:`project_layout`
    The directory structure your project must follow and where all build
    output is written.

:ref:`configuration`
    Full reference for every ``scaldys-project.toml`` setting, with defaults and
    examples.

:ref:`scaldys_project_toml_reference`
    A single, fully-annotated ``scaldys-project.toml`` block listing every available
    option with inline comments — ready to copy into a new project.

:ref:`compliance_checking`
    The full list of compliance rules validated before any build step runs,
    with a description of each requirement and links to the relevant guides.

:ref:`documentation_building`
    How ``scaldys-project`` drives Sphinx to produce the user guide and
    developer API guide.

:ref:`cython_compilation`
    How selected Python modules are compiled to native ``.pyd`` extensions —
    when to use it, how it works, and its limitations.

:ref:`windows_exe`
    How PyInstaller bundles your project into a self-contained Windows
    executable, and how to handle common issues like missing modules and
    antivirus false positives.

:ref:`windows_installer`
    How Inno Setup is invoked to produce the final ``.exe`` installer,
    including the required packaging files and a minimal ``.iss`` script
    template.
