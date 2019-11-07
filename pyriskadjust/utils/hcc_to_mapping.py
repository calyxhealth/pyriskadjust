from pyriskadjust.icd_mapping.mapping_2020_v24 import ICD_MAPPING
from pyriskadjust.hccs.hccs_v24 import HCC_LABELS

import json

output = dict((n, []) for n in HCC_LABELS.keys())
for icd, hccs in ICD_MAPPING.items():
    for hcc in hccs:
        output[hcc].append(icd)

with open("hcc_to_icd_2020.json", "w") as f:
    json.dump(output, f, indent=4)
