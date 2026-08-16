"""Steam Library folder and multi-drive storage selector widget."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from src.core.models import LibraryFolder
from src.steam.detector import steam_detector


class DiskSelectorWidget(QFrame):
    """Widget displaying multi-drive Steam libraries and available disk storage."""

    library_changed = pyqtSignal(Path)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("DiskSelectorWidget")
        self.setProperty("class", "surface-card")
        self._libraries: List[LibraryFolder] = []

        self._init_ui()
        self.refresh_libraries()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # Header Row
        header_layout = QHBoxLayout()
        title_label = QLabel("💾 Hedef Steam Kütüphanesi & Disk Alanı", self)
        title_label.setStyleSheet("font-weight: 600; color: #f3f6f9; font-size: 13px;")

        self.space_label = QLabel("", self)
        self.space_label.setStyleSheet("color: #66c0f4; font-weight: bold; font-size: 12px;")

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.space_label)

        # Combo & Progress Row
        row_layout = QHBoxLayout()
        self.combo = QComboBox(self)
        self.combo.currentIndexChanged.connect(self._on_combo_changed)

        self.progress = QProgressBar(self)
        self.progress.setFixedWidth(140)
        self.progress.setTextVisible(True)

        row_layout.addWidget(self.combo, 1)
        row_layout.addWidget(self.progress)

        layout.addLayout(header_layout)
        layout.addLayout(row_layout)

    def refresh_libraries(self) -> None:
        """Scan and populate library folders."""
        self._libraries = steam_detector.get_library_folders()
        self.combo.blockSignals(True)
        self.combo.clear()

        if not self._libraries:
            self.combo.addItem("Kütüphane bulunamadı", None)
            self.space_label.setText("Boş Alan: Yok")
            self.progress.setValue(0)
            self.combo.blockSignals(False)
            return

        for lib in self._libraries:
            label_suffix = f" [{lib.label}]" if lib.label else ""
            display_str = f"{lib.path}{label_suffix} — ({lib.free_gb:.1f} GB Boş / {lib.total_gb:.1f} GB Toplam)"
            self.combo.addItem(display_str, lib.path)

        self.combo.blockSignals(False)
        self._update_display(0)

    def _on_combo_changed(self, index: int) -> None:
        if 0 <= index < len(self._libraries):
            self._update_display(index)
            selected_path = self._libraries[index].path
            self.library_changed.emit(selected_path)

    def _update_display(self, index: int) -> None:
        if 0 <= index < len(self._libraries):
            lib = self._libraries[index]
            self.space_label.setText(f"{lib.free_gb:.1f} GB Boş")
            used_pct = int(lib.usage_percent)
            self.progress.setValue(used_pct)
            self.progress.setFormat(f"%{used_pct} Dolu")

            # Color styling based on remaining space
            if used_pct >= 90:
                self.progress.setStyleSheet("QProgressBar::chunk { background-color: #ef5350; }")
            elif used_pct >= 75:
                self.progress.setStyleSheet("QProgressBar::chunk { background-color: #f9a825; }")
            else:
                self.progress.setStyleSheet("QProgressBar::chunk { background-color: #57cb65; }")

    def get_selected_library(self) -> Optional[Path]:
        """Return the currently selected Path."""
        idx = self.combo.currentIndex()
        if 0 <= idx < len(self._libraries):
            return self._libraries[idx].path
        return None
