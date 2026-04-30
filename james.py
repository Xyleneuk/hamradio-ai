from gui.setup_wizard import load_config, save_config
c = load_config()
print('repeater_callsign:', c.get('repeater_callsign'))
c['repeater_callsign'] = 'MX0MXO'
save_config(c)
print('Fixed')