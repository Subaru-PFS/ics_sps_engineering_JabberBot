STSlabels = {-1: 'all',
             1108: 'aten-voltage',
             1109: 'aten-current',
             1110: 'aten-power'}

xcuLabels = ['cooler-status',
             'cooler-setpoint',
             'cooler-reject',
             'cooler-tip',
             'cooler-power',
             'gauge-pressure',
             'ionpump1-status',
             'ionpump1-pressure',
             'ionpump2-status',
             'ionpump2-pressure',
             'Input 24V-UPS',
             'Input 24V-AUX',
             'temps-Detector Box',
             'temps-Mangin',
             'temps-Spider',
             'temps-Thermal Spreader',
             'temps-Front Ring',
             'temps-Detector 1',
             'temps-Detector 2',
             'heaters-ccd_enabled',
             'heaters-spreader_enabled',
             'heaters-ccd_fraction',
             'heaters-spreader_fraction',
             'gatevalve-position',
             'gatevalve-request',
             'turbo-speed']

enuLabels = ['MOTOR_RDA',
             'MOTOR_SHUTTER_B',
             'MOTOR_SHUTTER_R',
             'BIA_BOX_UPPER',
             'BIA_BOX_LOWER',
             'FIBER_UNIT_BENCH_LEVEL',
             'FIBER_UNIT_HEXAPOD_TOP',
             'FIBER_UNIT_FIBER_FRAME_TOP',
             'COLLIMATOR_FRAME_BENCH_LEVEL',
             'COLLIMATOR_FRAME_TOP'
             'BENCH_LEFT_TOP',
             'BENCH_LEFT_BOTTOM',
             'BENCH_RIGHT_TOP',
             'BENCH_RIGHT_BOTTOM',
             'BENCH_FAR_TOP',
             'BENCH_FAR_BOTTOM',
             'BENCH_NEAR_TOP',
             'BENCH_NEAR_BOTTOM',
             'BENCH_CENTRAL_BOTTOM']

xcuSTS = dict(b1=1120, r1=1150)
enuSTS = dict(enu_sm1=1180)

for cam, stsId in xcuSTS.iteritems():
    for i, label in enumerate(xcuLabels):
        STSlabels[stsId + i] = '%s-%s' % (cam.upper(), label)

for sm, stsId in enuSTS.iteritems():
    for i, label in enumerate(enuLabels):
        STSlabels[stsId + i] = '%s-%s' % (sm.upper(), label)

alertsFromMode = {'offline': [('cooler-power', False), ('ionpump1-pressure', False), ('ionpump2-pressure', False),
                              ('turbo-speed', False), ('gauge-pressure', False), ('heaters-ccd_enabled', False)],

                  'pumpdown': [('cooler-power', False), ('ionpump1-pressure', False), ('ionpump2-pressure', False),
                               ('turbo-speed', True), ('gauge-pressure', True), ('heaters-ccd_enabled', False)],

                  'cooldown': [('cooler-power', True), ('ionpump1-pressure', False), ('ionpump2-pressure', False),
                               ('turbo-speed', True), ('gauge-pressure', True), ('heaters-ccd_enabled', False)],

                  'operation': [('cooler-power', True), ('ionpump1-pressure', True), ('ionpump2-pressure', True),
                                ('turbo-speed', False), ('gauge-pressure', True), ('heaters-ccd_enabled', False)],

                  'warmup': [('cooler-power', False), ('ionpump1-pressure', False), ('ionpump2-pressure', False),
                             ('turbo-speed', True), ('gauge-pressure', True), ('heaters-ccd_enabled', True)]}