from gui.setup_wizard import load_config, save_config
c = load_config()
print('Current input_device:', c.get('input_device'))
print('Current output_device:', c.get('output_device'))
c['input_device'] = 1
c['output_device'] = 7
save_config(c)
print('Fixed - input=1 output=7')