STSlabels = {-1: 'all',
             1108: 'aten-voltage',
             1109: 'aten-current',
             1110: 'aten-power',
             1111: 'B1-cooler-status',
             1112: 'B1-cooler-setpoint',
             1113: 'B1-cooler-reject',
             1114: 'B1-cooler-tip',
             1115: 'B1-cooler-power',
             1116: 'B1-gauge-pressure',
             1117: 'B1-ionpump1-status',
             1118: 'B1-ionpump1-pressure',
             1119: 'B1-ionpump2-status',
             1120: 'B1-ionpump2-pressure',
             1121: 'B1-Input 24V-UPS',
             1122: 'B1-Input 24V-AUX',
             1123: 'B1-temps-Detector Box',
             1124: 'B1-temps-Mangin',
             1125: 'B1-temps-Spider',
             1126: 'B1-temps-Thermal Spreader',
             1127: 'B1-temps-Front Ring',
             1128: 'B1-temps-Detector 1',
             1129: 'B1-temps-Detector 2',
             1130: 'B1-heaters-ccd_enabled',
             1131: 'B1-heaters-spreader_enabled',
             1132: 'B1-heaters-ccd_fraction',
             1133: 'B1-heaters-spreader_fraction',
             1134: 'B1-gatevalve-position',
             1135: 'B1-gatevalve-request',
             1136: 'B1-turbo-speed',
             1137: 'R1-cooler-status',
             1138: 'R1-cooler-setpoint',
             1139: 'R1-cooler-reject',
             1140: 'R1-cooler-tip',
             1141: 'R1-cooler-power',
             1142: 'R1-gauge-pressure',
             1143: 'R1-ionpump1-status',
             1144: 'R1-ionpump1-pressure',
             1145: 'R1-ionpump2-status',
             1146: 'R1-ionpump2-pressure',
             1147: 'R1-Input 24V-UPS',
             1148: 'R1-Input 24V-AUX',
             1149: 'R1-temps-Detector Box',
             1150: 'R1-temps-Mangin',
             1151: 'R1-temps-Spider',
             1152: 'R1-temps-Thermal Spreader',
             1153: 'R1-temps-Front Ring',
             1154: 'R1-temps-Detector 1',
             1155: 'R1-temps-Detector 2',
             1156: 'R1-heaters-ccd_enabled',
             1157: 'R1-heaters-spreader_enabled',
             1158: 'R1-heaters-ccd_fraction',
             1159: 'R1-heaters-spreader_fraction',
             1160: 'R1-gatevalve-position',
             1161: 'R1-gatevalve-request',
             1162: 'R1-turbo-speed',
             }

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

