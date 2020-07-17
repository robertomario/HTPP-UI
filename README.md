# Rapid Phenotyping UI

This project creates the UI to run the High-Throughput Plant Phenotyping
Platform I built as part of my PhD research at McGill University.

## Installation

Create an executable by doing

```bash
pyinstaller HTPP_UI.py
```

## Usage

In Windows, just double-click

```bash
HTPP_UI.bat
```

in order to launch.

After that go to the Settings menu in the toolbar and select
the correct ports where the sensors are located.

The default sensor connections in the Serial to USB converters:

```bash
1 >> Environmental
2 >> Multispectral
3 >> Multispectral
4 >> Multispectral
5 >> Ultrasonic
6 >> Ultrasonic
7 >> Ultrasonic
8 >> GPS
```

Edit the settings as desired and click Measure in the bottom right corner to do
a test. If data appears in the log and plots, you are good to go.
