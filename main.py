import sys
import os
from PyQt6.QtWidgets import QApplication, QMessageBox
from gui.main_window import MainWindow
from gui.setup_wizard import load_config, run_wizard
from hamlib_manager import HamlibManager


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setApplicationName('Ham Radio AI')
    app.setApplicationVersion('1.0')
    app.setOrganizationName('HamRadioAI')
    app.setOrganizationDomain('hamradioai.co.uk')

    # ----------------------------------------------------------------
    # Load or create configuration
    # ----------------------------------------------------------------
    config = load_config()
    if not config:
        config = run_wizard()
        if not config:
            # User cancelled setup wizard - exit cleanly
            sys.exit(0)

    # ----------------------------------------------------------------
    # Set Anthropic API key from config
    # ----------------------------------------------------------------
    api_key = config.get('api_key', '')
    if api_key:
        os.environ['ANTHROPIC_API_KEY'] = api_key
    else:
        QMessageBox.critical(
            None,
            'API Key Missing',
            'No Anthropic API key found.\n\n'
            'Please run the setup wizard and enter your API key.\n'
            'Get one at: console.anthropic.com'
        )
        config = run_wizard()
        if not config:
            sys.exit(0)
        os.environ['ANTHROPIC_API_KEY'] = config.get('api_key', '')

    # ----------------------------------------------------------------
    # Start rigctld in background
    # ----------------------------------------------------------------
    hamlib = HamlibManager(config)
    rigctld_ok = hamlib.start()

    if not rigctld_ok:
        result = QMessageBox.warning(
            None,
            'Radio Connection Failed',
            'Could not connect to your radio.\n\n'
            'Please check:\n'
            '  • Radio is powered on and connected via USB\n'
            '  • Correct COM port is selected in settings\n'
            '  • Baud rate matches your radio settings\n'
            '  • No other software is using the COM port\n\n'
            'You can continue without a radio connection\n'
            'but transmitting will not work.\n\n'
            'Continue anyway?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if result == QMessageBox.StandardButton.No:
            sys.exit(0)

    # ----------------------------------------------------------------
    # Launch main window
    # ----------------------------------------------------------------
    window = MainWindow(config, hamlib)
    window.show()

    # ----------------------------------------------------------------
    # Run application event loop
    # ----------------------------------------------------------------
    exit_code = app.exec()

    # ----------------------------------------------------------------
    # Clean up on exit
    # ----------------------------------------------------------------
    hamlib.stop()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()