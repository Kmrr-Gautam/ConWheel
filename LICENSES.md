# Dependency and licensing report (to be re-verified before every release)

| Component | Role | License (as generally published) | Redistribution note |
|---|---|---|---|
| PySide6 / Qt | GUI | LGPLv3 / GPL / commercial | Dynamic linking via PyInstaller one-folder build keeps LGPL compliance; ship license text |
| Pillow | images | HPND (permissive) | OK |
| PyMuPDF | PDF text | AGPL-3.0 / commercial (Artifex) | **AGPL obligations apply to distribution**; obtain a commercial license or remove PDF→TXT for closed-source distribution |
| pypdf, reportlab, python-docx, openpyxl, python-pptx, pandas, markdown | listed in requirements | BSD / MIT / BSD-style | OK (reportlab: BSD) |
| pynput | global input listener | LGPLv3 | Bundled dynamically; ship license text |
| pywin32 | Explorer COM | PSF | OK |
| PyInstaller | packaging | GPL-2.0 with bootloader exception | Output may be distributed under your license |
| FFmpeg | audio/video | LGPLv2.1+ or GPL depending on build (libx264/libx265 builds are GPL) | Not bundled by default. If you bundle a GPL build, the distribution must comply with the GPL (source offer). |
| LibreOffice | office conversion | MPL-2.0 | Not bundled (size); user installs separately |
| Inno Setup | installer | Inno Setup License (free) | Build-time tool only |

This table is a starting point, not legal advice; confirm exact versions and licences before distributing.
