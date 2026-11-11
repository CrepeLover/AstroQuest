# Local build files

What goes with this build but isn't emulator source:

- `install/settings.txt`: the launcher settings this build runs with (Steam Frame, 120 Hz, 3960 pixels an eye). Each shadow, level-of-detail and field-of-view knob is explained inline.
- `install/BUILD.txt`: every local build with its SHA-256.
- `install/Play Astro Bot VR (Steam).bat`: the target of the Steam shortcut.
- `work/`: build scripts (`build-astroquest.cmd`, `build-and-install-when-idle.ps1`, `compile-check.cmd`), reverse-engineering helpers (`re/`), frame-timing analysis (`perf/`), Wi-Fi QoS scripts for the headset stream (`net/`), the microphone level test (`mic-test/`) and capture tools (`tools/`).

The scripts expect this layout:

| Folder | Contents |
|---|---|
| `C:\Games\AstroQuest` | the PC VR release |
| `C:\Games\AstroQuest-src` | this repository |
| `C:\Games\astroquest-work` | the work folder |

`C:\Users\<user>` stands for the Windows profile folder. Placeholders in angle brackets replace local machine and network details.
