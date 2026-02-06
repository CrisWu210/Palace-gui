# Palace GUI (Windows + Conda)

This project provides a Windows PySide6 desktop GUI for preparing Palace simulation projects.
The GUI **only generates shell scripts** for Linux/HPC use and does **not** run Palace on Windows.

## Requirements

- Windows 10/11
- Anaconda or Miniconda
- External installations:
  - Palace (Linux/HPC)
  - Gmsh (Windows)

## Install (Conda)

```bash
conda create -n palace-gui python=3.11
conda activate palace-gui
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

## Notes

- The GUI only generates `run_palace.sh` and **never** executes Palace.
- Gmsh is launched as an external Windows application.
