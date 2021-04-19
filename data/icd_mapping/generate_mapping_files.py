from collections import defaultdict
import json

# Utillity to convert raw ICD-10 to HCC mapping files to more useful formats.
# Outputs both json file and python file (mapping represented as python dict)

# fmt: off
files = [
    # format is (input_name, output_name)
    ("F2118H1R", "2018_v21"),
    ("F2218O1P", "2018_v22"),
    ("F2318P1Q", "2019_v23"),
    ("F2419P1M", "2020_v24"),
    ("F2221O1P", "2021_v22"),
    ("F2421P1M", "2021_v24")
]
# fmt: on

output_dir = "../../pyriskadjust/icd_mapping/"
for (inname, outname) in files:
    with open(inname + ".TXT") as f:
        d = defaultdict(list)
        for line in f.readlines():
            l = line.strip().split()
            d[l[0]].append(int(l[1]))

        # uncomment to generate json as well
        # with open(output_dir + "mapping_" + outname + ".json", "w") as fo:
        #     json.dump(d, fo, indent=4)

        with open(output_dir + "mapping_" + outname + ".py", "w") as fo:
            fo.write('"""ICD to HCC mapping based on {}.TXT"""\n\n'.format(inname))
            fo.write("ICD_MAPPING = ")
            json.dump(d, fo, indent=4)
