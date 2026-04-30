from gui.setup_wizard import load_config, save_config
c = load_config()
c['enable_general'] = True
c['enable_contest'] = True
c['enable_repeater'] = True
c['contest_name'] = 'RSGB'
c['repeater_callsign'] = c.get('repeater_callsign', 'mx0mxo')
c['beacon_interval'] = 60
save_config(c)
print('All personalities enabled')