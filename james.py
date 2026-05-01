from gui.setup_wizard import load_config, save_config
c = load_config()
c['whisper_model'] = 'medium'
save_config(c)
print('Whisper set to mediumf')