import sys
import os
import logging
from PyQt6.QtWidgets import QApplication, QMessageBox
from gui.main_window import MainWindow
from gui.setup_wizard import load_config, run_wizard, save_config
from hamlib_manager import HamlibManager

# Set up logging to both console and file
log_file = os.path.join(os.path.expanduser('~'), 'hamradio_ai.log')
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logging.info("=== Ham Radio AI Started ===")
logging.info(f"Log file: {log_file}")


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setApplicationName('Ham Radio AI')
    app.setApplicationVersion('3.0')
    app.setOrganizationName('HamRadioAI')
    app.setOrganizationDomain('hamradioai.co.uk')
    logging.info("Qt application initialized")

    # ----------------------------------------------------------------
    # Load or create configuration
    # ----------------------------------------------------------------
    logging.info("Loading configuration...")
    config = load_config()
    if not config or not config.get('setup_complete'):
        logging.info("No config found or setup incomplete, running wizard...")
        config = run_wizard()
        if not config:
            logging.info("User cancelled setup wizard")
            sys.exit(0)
        if config:
            config['setup_complete'] = True
            save_config(config)

    logging.info(f"Config loaded: radio_model={config.get('radio_model')}, com_port={config.get('com_port')}, baud={config.get('baud_rate')}")

    # ----------------------------------------------------------------
    # Set Anthropic API key from config
    # ----------------------------------------------------------------
    api_key = config.get('api_key', '')
    if api_key:
        os.environ['ANTHROPIC_API_KEY'] = api_key
        logging.info("API key set from config")
    else:
        logging.warning("No API key in config, prompting user...")
        QMessageBox.critical(
            None,
            'API Key Missing',
            'No Anthropic API key found.\n\n'
            'Please run the setup wizard and enter your API key.\n'
            'Get one at: console.anthropic.com'
        )
        config = run_wizard()
        if not config:
            logging.info("User cancelled setup wizard")
            sys.exit(0)
        os.environ['ANTHROPIC_API_KEY'] = config.get('api_key', '')
        logging.info("API key set from wizard")

    # ----------------------------------------------------------------
    # Start rigctld in background
    # ----------------------------------------------------------------
    logging.info("Attempting to start rigctld...")
    hamlib = HamlibManager(config)
    rigctld_ok = hamlib.start()

    if not rigctld_ok:
        logging.error("Failed to start rigctld")
        result = QMessageBox.warning(
            None,
            'Radio Connection Failed',
            'Could not connect to your radio.\n\n'
            'Please check:\n'
            '  • Radio is powered on and connected via USB\n'
            '  • Correct COM port is selected in settings\n'
            '  • Baud rate matches your radio settings\n'
            '  • No other software is using the COM port\n'
            '  • Run the app with Admin privileges (may be needed)\n\n'
            'You can continue without a radio connection\n'
            'but transmitting will not work.\n\n'
            'Continue anyway?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if result == QMessageBox.StandardButton.No:
            logging.info("User chose not to continue without radio")
            sys.exit(0)
    else:
        logging.info("rigctld started successfully")

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