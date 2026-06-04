@echo off
REM Generate WireViz wiring diagrams
REM Because Windows can't manage a PATH to save its life.

REM Graphviz: installed system-wide but not on PATH because... reasons.
set PATH=%PATH%;C:\Program Files\Graphviz\bin

REM WireViz: installed via pip. If wireviz isn't found, install it:
REM   pip install wireviz
REM and ensure your Python Scripts dir is on PATH. The line below adds the
REM Microsoft Store Python per-user Scripts dir for the current user (adjust
REM the Python version if needed); harmless if the dir doesn't exist.
set PATH=%PATH%;%LOCALAPPDATA%\Packages\PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0\LocalCache\local-packages\Python311\Scripts

REM Verify tools exist before wasting everyone's time
where dot >nul 2>&1 || (echo ERROR: Graphviz dot not found. Install from https://graphviz.org/ & exit /b 1)
where wireviz >nul 2>&1 || (echo ERROR: wireviz not found. pip install wireviz & exit /b 1)

echo Generating wiring diagrams...

pushd "%~dp0"
wireviz wiring_encoder.yml
if errorlevel 1 echo FAILED: wiring_encoder.yml
wireviz wiring_stepper.yml
if errorlevel 1 echo FAILED: wiring_stepper.yml
popd

echo Done.
