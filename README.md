# dwg-viewer

Viewer for AutoCAD .dwg files built on the dwg-reader decoder.

- Renders model and paper space, layers, layouts and viewports in the browser, using the reader in this repository.

## How it was built

Independent implementation. The format was worked out from public format descriptions (read, not copied) and by experiment, and every decoded value is checked against output of AutoCAD 2026 running in an offline virtual machine. No code, tables or constants from other DWG libraries (LibreDWG, Open Design Alliance, or others) are used. The test drawings are not redistributed.

Status: experimental.

## License

MIT, see [LICENSE](LICENSE). AutoCAD and DWG are trademarks of Autodesk, Inc. This project is independent and is not affiliated with, endorsed by or sponsored by Autodesk.
