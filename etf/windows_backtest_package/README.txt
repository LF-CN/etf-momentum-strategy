ETF Windows Backtest Package

1. Purpose
This is the Windows native ETF backtest package.
After the first full installation, future updates can usually be done by replacing files in presets\.

2. First-time setup
(1) Install Python 3.11 or newer on Windows
(2) Double-click install.bat
(3) Wait for dependencies to finish installing

3. Common runs
- Double-click run_baseline.bat
- Double-click run_max_single_weight_3way.bat
- Or run: run_preset.bat presets\edge_param_scan.json

4. Results
All outputs are saved in the results\ folder.

5. Main folders
- core\        backtest engine and preset runner
- etf_data\    ETF CSV history
- presets\     backtest presets
- results\     output json files

6. Future updates
Usually only update:
- presets\*.json
- core\run_preset.py or core\momentum_backtest.py when needed
