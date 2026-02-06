import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QTabWidget,
    QLabel, QPushButton, QPlainTextEdit, QFileDialog, QLineEdit, QHBoxLayout,
    QMessageBox
)
from PySide6.QtCore import QProcess
from pathlib import Path

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Palace GUI - MVP (Windows + Conda)")
        self.resize(1100, 700)

        self.project_dir = ""
        self.gmsh_path = ""

        tabs = QTabWidget()
        tabs.addTab(self._build_project_tab(), "Project")
        tabs.addTab(self._build_meshing_tab(), "Meshing")
        tabs.addTab(self._build_run_tab(), "Run")
        self.setCentralWidget(tabs)

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

        layout.addWidget(QLabel("Tip: this folder will contain config.json, mesh/, output/ etc."))
        return w

    def _choose_project_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Choose project directory")
        if d:
            self.project_dir = d
            self.project_dir_edit.setText(d)

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

        self.launch_btn = QPushButton("Launch Gmsh")
        self.launch_btn.clicked.connect(self._launch_gmsh)
        layout.addWidget(self.launch_btn)

        self.mesh_log = QPlainTextEdit()
        self.mesh_log.setReadOnly(True)
        layout.addWidget(self.mesh_log)

        return w

    def _choose_gmsh_exe(self):
        f, _ = QFileDialog.getOpenFileName(self, "Choose gmsh.exe", filter="gmsh.exe (gmsh.exe)")
        if f:
            self.gmsh_path = f
            self.gmsh_edit.setText(f)

    def _launch_gmsh(self):
        if not self.project_dir:
            QMessageBox.warning(self, "Missing project directory", "Please choose a project directory first.")
            return
        if not self.gmsh_path or not Path(self.gmsh_path).exists():
            QMessageBox.warning(self, "Missing gmsh.exe", "Please set a valid path to gmsh.exe.")
            return

        # Optional: let user pick a file to open in gmsh
        f, _ = QFileDialog.getOpenFileName(
            self, "Open geometry/mesh in Gmsh",
            self.project_dir,
            "Geometry/Mesh (*.geo *.geo_unrolled *.step *.stp *.stl *.brep *.msh);;All files (*.*)"
        )

        args = [f] if f else []
        self.mesh_log.appendPlainText(f"Launching: {self.gmsh_path} {' '.join(args)}")
        # Use startDetached so gmsh runs independently (simplest, most stable)
        ok = QProcess.startDetached(self.gmsh_path, args, self.project_dir)
        if not ok:
            QMessageBox.critical(self, "Failed to launch", "Failed to launch Gmsh. Check path and permissions.")

    # ---------- Run tab ----------
    def _build_run_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        layout.addWidget(QLabel("Run Palace (placeholder):"))
        self.run_log = QPlainTextEdit()
        self.run_log.setReadOnly(True)
        layout.addWidget(self.run_log)

        btn = QPushButton("Run Palace (placeholder)")
        btn.clicked.connect(lambda: self.run_log.appendPlainText("TODO: run palace via QProcess"))
        layout.addWidget(btn)
        return w

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
