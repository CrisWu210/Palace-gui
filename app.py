import json
import os
import sys
from pathlib import Path

from PySide6.QtCore import QProcess, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

DEFAULT_TEMPLATES = {
    "MPI (mpiexec)": "\n".join(
        [
            "# Run with MPI",
            "mpiexec -n 4 palace -c \"$CONFIG\"",
        ]
    ),
    "Slurm (srun + SBATCH)": "\n".join(
        [
            "#SBATCH --job-name=palace",
            "#SBATCH --nodes=1",
            "#SBATCH --ntasks=4",
            "#SBATCH --time=01:00:00",
            "",
            "srun palace -c \"$CONFIG\"",
        ]
    ),
    "Custom": "# Write your custom command here",
}

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Palace GUI - MVP (Windows + Conda)")
        self.resize(1100, 700)

        self.project_dir = ""
        self.gmsh_path = ""
        self.settings_path = Path(__file__).resolve().parent / "settings.json"

        tabs = QTabWidget()
        tabs.addTab(self._build_project_tab(), "Project")
        tabs.addTab(self._build_meshing_tab(), "Meshing")
        tabs.addTab(self._build_run_tab(), "Run")
        self.setCentralWidget(tabs)
        self._load_settings()

    # ---------- Project tab ----------
    def _build_project_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        layout.addWidget(QLabel("Project directory:"))
        row = QHBoxLayout()
        self.project_dir_edit = QLineEdit()
        btn = QPushButton("Browse...")
        btn.clicked.connect(self._choose_project_dir)
        row.addWidget(self.project_dir_edit)
        row.addWidget(btn)
        layout.addLayout(row)

        layout.addWidget(QLabel("Tip: this folder will contain config.json, mesh/, run_palace.sh, etc."))
        return w

    def _choose_project_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Choose project directory")
        if d:
            self.project_dir = d
            self.project_dir_edit.setText(d)
            self._save_settings()

    # ---------- Meshing tab ----------
    def _build_meshing_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        layout.addWidget(QLabel("Gmsh executable path (gmsh.exe):"))
        row = QHBoxLayout()
        self.gmsh_edit = QLineEdit()
        btn = QPushButton("Browse...")
        btn.clicked.connect(self._choose_gmsh_exe)
        row.addWidget(self.gmsh_edit)
        row.addWidget(btn)
        layout.addLayout(row)

        layout.addWidget(QLabel("Optional: open a geometry/mesh file in Gmsh"))
        file_row = QHBoxLayout()
        self.geometry_edit = QLineEdit()
        file_btn = QPushButton("Browse...")
        file_btn.clicked.connect(self._choose_geometry_file)
        file_row.addWidget(self.geometry_edit)
        file_row.addWidget(file_btn)
        layout.addLayout(file_row)
        self.geometry_edit.textChanged.connect(self._save_settings)

        self.launch_btn = QPushButton("Launch Gmsh")
        self.launch_btn.clicked.connect(self._launch_gmsh)
        layout.addWidget(self.launch_btn)

        return w

    def _choose_gmsh_exe(self):
        f, _ = QFileDialog.getOpenFileName(self, "Choose gmsh.exe", filter="gmsh.exe (gmsh.exe)")
        if f:
            self.gmsh_path = f
            self.gmsh_edit.setText(f)
            self._save_settings()

    def _choose_geometry_file(self):
        file_filter = "Geometry/Mesh (*.geo *.geo_unrolled *.step *.stp *.stl *.brep *.msh);;All files (*.*)"
        f, _ = QFileDialog.getOpenFileName(self, "Choose geometry/mesh file", self.project_dir, file_filter)
        if f:
            self.geometry_edit.setText(f)
            self._save_settings()

    def _launch_gmsh(self):
        if not self.project_dir:
            QMessageBox.warning(self, "Missing project directory", "Please choose a project directory first.")
            return
        if not self.gmsh_path or not Path(self.gmsh_path).exists():
            QMessageBox.warning(self, "Missing gmsh.exe", "Please set a valid path to gmsh.exe.")
            return

        geometry_file = self.geometry_edit.text().strip()
        args = [geometry_file] if geometry_file else []
        # Use startDetached so gmsh runs independently (simplest, most stable)
        ok = QProcess.startDetached(self.gmsh_path, args, self.project_dir)
        if not ok:
            QMessageBox.critical(self, "Failed to launch", "Failed to launch Gmsh. Check path and permissions.")

    # ---------- Run tab ----------
    def _build_run_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        layout.addWidget(QLabel("Script mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(DEFAULT_TEMPLATES.keys())
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        layout.addWidget(self.mode_combo)

        layout.addWidget(QLabel("Script template:"))
        self.script_edit = QPlainTextEdit()
        self.script_edit.setPlainText(DEFAULT_TEMPLATES["MPI (mpiexec)"])
        self.script_edit.textChanged.connect(self._save_settings)
        layout.addWidget(self.script_edit)

        btn_row = QHBoxLayout()
        generate_btn = QPushButton("Generate Script")
        generate_btn.clicked.connect(self._generate_script)
        open_btn = QPushButton("Open Folder")
        open_btn.clicked.connect(self._open_project_folder)
        btn_row.addWidget(generate_btn)
        btn_row.addWidget(open_btn)
        layout.addLayout(btn_row)

        return w

    def _on_mode_changed(self, mode: str):
        if mode in DEFAULT_TEMPLATES:
            self.script_edit.setPlainText(DEFAULT_TEMPLATES[mode])
        self._save_settings()

    def _open_project_folder(self):
        if not self.project_dir:
            QMessageBox.warning(self, "Missing project directory", "Please choose a project directory first.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.project_dir))

    def _generate_script(self):
        if not self.project_dir:
            QMessageBox.warning(self, "Missing project directory", "Please choose a project directory first.")
            return

        project_dir = Path(self.project_dir)
        script_path = project_dir / "run_palace.sh"
        config_path = project_dir / "config.json"

        template_body = self.script_edit.toPlainText().strip()
        script_content = "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -e",
                "SCRIPT_DIR=\"$(cd \"$(dirname \"$0\")\" && pwd)\"",
                "cd \"$SCRIPT_DIR\"",
                f"PROJECT_DIR=\"{project_dir.as_posix()}\"",
                "CONFIG=\"$PROJECT_DIR/config.json\"",
                "cd \"$PROJECT_DIR\"",
                "",
                template_body,
                "",
            ]
        )

        script_path.write_text(script_content, encoding="utf-8")
        if os.name != "nt":
            current_mode = script_path.stat().st_mode
            script_path.chmod(current_mode | 0o111)

        self._save_settings()
        QMessageBox.information(
            self,
            "Script generated",
            f"Generated {script_path}\nConfig path: {config_path}",
        )

    def _load_settings(self):
        if not self.settings_path.exists():
            return
        try:
            settings = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return

        self.project_dir = settings.get("project_dir", "")
        self.project_dir_edit.setText(self.project_dir)

        self.gmsh_path = settings.get("gmsh_path", "")
        self.gmsh_edit.setText(self.gmsh_path)

        saved_mode = settings.get("run_mode", "MPI (mpiexec)")
        if saved_mode in DEFAULT_TEMPLATES:
            self.mode_combo.setCurrentText(saved_mode)
        saved_template = settings.get("script_template")
        if saved_template:
            self.script_edit.setPlainText(saved_template)

        geometry_file = settings.get("geometry_file", "")
        self.geometry_edit.setText(geometry_file)

    def _save_settings(self):
        settings = {
            "project_dir": self.project_dir,
            "gmsh_path": self.gmsh_path,
            "run_mode": self.mode_combo.currentText(),
            "script_template": self.script_edit.toPlainText(),
            "geometry_file": self.geometry_edit.text().strip(),
        }
        self.settings_path.write_text(json.dumps(settings, indent=2), encoding="utf-8")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
