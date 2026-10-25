from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                               QHBoxLayout, QLabel, QLineEdit, QPushButton, QSlider, QVBoxLayout)
from PySide6.QtCore import Qt
from ..converters.base import Options

class ConversionDialog(QDialog):
    """Compact options/confirmation dialog shown only when a conversion has choices or caveats."""
    def __init__(self, src, conv, settings, parent=None):
        super().__init__(parent); self.setWindowTitle("Convert"); self.conv = conv; self.src = src
        lay = QVBoxLayout(self)
        t = QLabel(f"<b>{src.name}</b> → <b>{conv.target.upper()}</b>"); t.setWordWrap(True); lay.addWidget(t)
        if conv.notes:
            n = QLabel(conv.notes); n.setWordWrap(True); n.setObjectName("muted"); lay.addWidget(n)
        form = QFormLayout(); lay.addLayout(form)
        self.quality = QSlider(Qt.Horizontal); self.quality.setRange(10, 100); self.quality.setValue(settings.image_quality)
        self.bitrate = QComboBox(); [self.bitrate.addItem(f"{b} kbps", b) for b in (96, 128, 160, 192, 256, 320)]
        self.bitrate.setCurrentIndex(max(0, self.bitrate.findData(settings.audio_bitrate_kbps)))
        self.preset = QComboBox(); [self.preset.addItem(x.title(), x) for x in ("small", "balanced", "quality")]
        self.preset.setCurrentIndex(max(0, self.preset.findData(settings.video_preset)))
        e = conv.engine
        if conv.target in ("jpg", "webp"): form.addRow("Quality", self.quality)
        if e == "ffmpeg":
            if conv.target in ("mp3", "aac", "m4a", "ogg", "opus"): form.addRow("Audio bitrate", self.bitrate)
            elif conv.target not in ("wav", "flac"): form.addRow("Video preset", self.preset)
        self.meta = QCheckBox("Preserve metadata"); self.meta.setChecked(settings.preserve_metadata); form.addRow(self.meta)
        self.name = QLineEdit(f"{src.stem}_converted.{conv.target}"); form.addRow("File name", self.name)
        row = QHBoxLayout(); self.dest = QLineEdit(settings.default_output_dir or str(src.parent))
        b = QPushButton("Browse…"); b.clicked.connect(self._browse); row.addWidget(self.dest); row.addWidget(b)
        form.addRow("Save to", row)
        bb = QDialogButtonBox(); ok = bb.addButton("Convert", QDialogButtonBox.AcceptRole); ok.setObjectName("primary")
        bb.addButton(QDialogButtonBox.Cancel); bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); lay.addWidget(bb)
    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "Output folder", self.dest.text())
        if d: self.dest.setText(d)
    def result_options(self) -> tuple[Options, str, str]:
        o = Options(image_quality=self.quality.value(), audio_bitrate_kbps=self.bitrate.currentData(),
                    video_preset=self.preset.currentData(), preserve_metadata=self.meta.isChecked())
        return o, self.dest.text(), self.name.text()
