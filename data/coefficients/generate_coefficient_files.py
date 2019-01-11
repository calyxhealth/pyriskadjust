from collections import defaultdict
import json

# Utillity to convert raw coefficient files to more useful formats.
# Outputs both json file and python file (mapping represented as python dict)

# fmt: off
files = [
    # format is (input_name, output_name)
    ("C2110H2R", "2018_v21"),
    ("C2214O5P", "2018_v22")
]
# fmt: on

output_dir = "../../py_risk_adjustment/coefficients/"
for (inname, outname) in files:
    with open(inname + ".csv") as f:
        header = f.readline().strip().replace('"', "").split(",")
        vals = map(float, f.readline().strip().split(","))
        coefficient_mapping = dict(zip(header, vals))

        # uncomment to generate json as well
        # with open(output_dir + "coefficients_" + outname + ".json", "w") as fo:
        #     json.dump(coefficient_mapping, fo, indent=4)

        with open(output_dir + "coefficients_" + outname + ".py", "w") as fo:
            fo.write('"""Model coefficients, take from {}"""\n\n'.format(inname))
            fo.write("COEFFICIENTS = ")
            json.dump(coefficient_mapping, fo, indent=4)
