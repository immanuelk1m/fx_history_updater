# FX Updater Script (`fx_updater.py`) Scheduling Guide

This document provides instructions on how to schedule the `fx_updater.py` script to run automatically every 10 minutes. This is essential for keeping the FX data in `fx_data.json` up-to-date.

## Prerequisites

Before scheduling, ensure:
1.  The `fx_updater.py` script is complete, functional, and saved on your system.
2.  Python 3.x is installed and correctly configured in your system's PATH (or you know the absolute path to the interpreter).
3.  The `requests` Python library is installed (`pip install requests`).
4.  You have a valid Alpha Vantage API Key. The script `fx_updater.py` should be configured to use this key, preferably via an environment variable (`ALPHA_VANTAGE_API_KEY`).

## Scheduling on Linux/macOS using Cron

Cron is a standard job scheduler on Unix-like systems.

**1. Open your Crontab:**
   Open a terminal and enter the following command to edit your cron table:
   ```bash
   crontab -e
   ```
   If it's your first time, you might be asked to choose a text editor (e.g., nano, vim).

**2. Add the Cron Job Entry:**
   Add the following line to the end of the crontab file. **You must replace `/path/to/your/python3` and `/path/to/your/script_directory/fx_updater.py` with the correct absolute paths for your system.**
   ```cron
   */10 * * * * /path/to/your/python3 /path/to/your/script_directory/fx_updater.py
   ```
   *   `*/10 * * * *`: This is the cron schedule expression. It means "run at every 10th minute of every hour, every day of the month, every month, and every day of the week."
   *   `/path/to/your/python3`: This is the absolute path to your Python 3 interpreter. You can find this by typing `which python3` in your terminal. Common paths include `/usr/bin/python3` or `/usr/local/bin/python3`.
   *   `/path/to/your/script_directory/fx_updater.py`: This is the absolute path to your `fx_updater.py` script. For example, `/home/username/projects/fx_app/fx_updater.py`.

**3. Save and Exit:**
   *   If using nano: Press `Ctrl+O`, then `Enter` to save, then `Ctrl+X` to exit.
   *   If using vim: Press `Esc`, type `:wq`, then press `Enter`.
   The cron job is now active.

## Scheduling on Windows using Task Scheduler

Windows uses Task Scheduler to automate tasks.

**1. Open Task Scheduler:**
   Search for "Task Scheduler" in the Windows Start Menu and open it.

**2. Create a New Task:**
   In the right-hand "Actions" pane, click **"Create Task..."** (this provides more configuration options than "Create Basic Task...").

   *   **General Tab:**
       *   **Name:** Give your task a descriptive name, e.g., `FX Rate Updater (10 min)`.
       *   **Description:** (Optional) e.g., `Runs fx_updater.py to fetch FX rates every 10 minutes.`
       *   Select "Run whether user is logged on or not" if you want it to run even when you're not logged in (this might require entering your password). Configure for your Windows version if needed.

   *   **Triggers Tab:**
       *   Click **"New..."**.
       *   **Begin the task:** Select "On a schedule".
       *   **Settings:** Choose "Daily". Set a "Start" time (e.g., the next convenient minute).
       *   **Advanced settings:**
           *   Check **"Repeat task every:"**.
           *   In the dropdown, select **"10 minutes"**.
           *   For **"for a duration of:"**, select **"Indefinitely"**.
           *   Ensure **"Enabled"** (at the bottom) is checked.
       *   Click **"OK"**.

   *   **Actions Tab:**
       *   Click **"New..."**.
       *   **Action:** Select "Start a program".
       *   **Program/script:** Enter the **full absolute path** to your Python interpreter (e.g., `C:\Python39\python.exe` or `C:\Users\YourName\AppData\Local\Programs\Python\Python39\python.exe`).
       *   **Add arguments (optional):** Enter the **full absolute path** to your `fx_updater.py` script (e.g., `C:\Users\YourName\Documents\Scripts\fx_updater.py`).
       *   **Start in (optional):** **This is crucial.** Set this to the directory where your `fx_updater.py` script is located (e.g., `C:\Users\YourName\Documents\Scripts\`). This ensures that files like `fx_data.json` are written to the expected directory.
       *   Click **"OK"**.

   *   **Conditions/Settings Tabs:** Review these for other preferences (e.g., power options). Defaults are often suitable.

   *   Click **"OK"** to save the task. You may be prompted for your user password.

## Important Considerations for Scheduled Tasks

*   **Absolute Paths:**
    *   **Always use absolute paths** for the Python interpreter and the script itself in your scheduler configuration. Relative paths (like `python3 my_script.py` or `.\my_script.py`) are unreliable in scheduled environments because the default "current directory" can be unexpected.

*   **Environment Variables (e.g., `ALPHA_VANTAGE_API_KEY`):**
    *   Scheduled tasks run in a non-interactive environment and may not inherit the environment variables set in your regular shell or user profile.
    *   The `fx_updater.py` script uses `os.getenv("ALPHA_VANTAGE_API_KEY", "YOUR_API_KEY_REPLACE_ME")`.
    *   **Cron (Linux/macOS):**
        1.  You can define the variable directly within the crontab file (less secure if the file is widely readable):
            ```cron
            ALPHA_VANTAGE_API_KEY="your_actual_key"
            */10 * * * * /path/to/python3 /path/to/fx_updater.py
            ```
        2.  Alternatively, ensure the variable is set in a file that cron's environment sources, like `/etc/environment` or user-specific shell profiles if your cron daemon is configured to read them (this can vary).
    *   **Task Scheduler (Windows):**
        1.  If you've set `ALPHA_VANTAGE_API_KEY` as a **system-wide or user environment variable** through the System Properties control panel, Task Scheduler can usually access it when the task is run under that user's account.
        2.  If not, consider creating a wrapper batch file (`.bat`) that sets the variable and then calls the Python script. Schedule the batch file instead.
            ```batch
            :: run_fx_updater.bat
            @echo off
            set ALPHA_VANTAGE_API_KEY=your_actual_key
            C:\Path\To\Python\python.exe C:\Path\To\Your\fx_updater.py
            ```

*   **Permissions:**
    *   The user account under which the scheduled task executes needs:
        *   **Read and execute permissions** for the Python interpreter.
        *   **Read permission** for the `fx_updater.py` script.
        *   **Write permission** for the directory where `fx_data.json` will be created (this is the "Start in" directory for Task Scheduler, or the directory you `cd` to in cron, or the script's directory if it handles pathing internally).
        *   Write permission for any log files the script might create.

*   **Working Directory:**
    *   The default current working directory (CWD) for a scheduled task is often not the script's own directory. `fx_updater.py` writes `fx_data.json` to its CWD.
    *   **Cron (Linux/macOS):** It's best practice to explicitly `cd` to the script's directory:
        ```cron
        */10 * * * * cd /path/to/your/script_directory/ && /path/to/your/python3 /path/to/your/script_directory/fx_updater.py
        ```
        The `&&` ensures the script only runs if the `cd` is successful.
    *   **Task Scheduler (Windows):** The **"Start in (optional):"** field in the "Action" settings correctly handles the CWD. Ensure it's set to the script's directory.

*   **Logging and Error Handling:**
    *   Output from `print()` statements or unhandled exceptions in scheduled scripts can be lost or hard to find (cron often emails output, which might not be ideal; Task Scheduler has basic history logs).
    *   **It is strongly recommended to implement robust logging within `fx_updater.py` itself** using Python's `logging` module. Write logs (including errors) to a dedicated file. This makes debugging much easier.
      ```python
      # Example snippet for fx_updater.py:
      import logging
      import os
      script_dir = os.path.dirname(os.path.abspath(__file__)) # Get script's own directory
      log_file = os.path.join(script_dir, "fx_updater.log")
      logging.basicConfig(filename=log_file,
                          level=logging.INFO,
                          format='%(asctime)s - %(levelname)s - %(message)s')

      # In your script:
      # logging.info("Script started.")
      # try:
      #   # ... your code ...
      #   logging.info("Data fetched successfully.")
      # except Exception as e:
      #   logging.error(f"An error occurred: {e}", exc_info=True)
      ```
    *   For cron, you can also redirect stdout/stderr of the command to a log file:
        ```cron
        ... fx_updater.py >> /path/to/your/script_directory/output.log 2>&1
        ```

By carefully considering these points, you can set up a reliable schedule for `fx_updater.py` to run every 10 minutes. Always test your configuration after setting it up.
