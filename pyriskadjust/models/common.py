from datetime import datetime
import re


MODEL_DESCRIPTIONS = {
    "cna": "Community Non-Dual Aged",
    "cnd": "Community Non-Dual Disabled",
    "cfa": "Community Full Benefit Dual Aged",
    "cfd": "Community Full Benefit Dual Disabled",
    "cpa": "Community Partial Benefit Dual Aged",
    "cpd": "Community Partial Benefit Dual Disabled",
    "ins": "Long Term Institutional",
    "ne": "New Enrollees",
    "snpne": "Special Needs Plan (SNP) New Enrollees",
}

MODEL_ABBREVIATIONS = MODEL_DESCRIPTIONS.keys()


def get_age_sex_string(age, sex, new_enrollee=False):
    age_sex_string = "m" if int(sex) == 1 else "f"
    if 0 <= age <= 34:
        return age_sex_string + "0_34"
    elif 35 <= age <= 44:
        return age_sex_string + "35_44"
    elif 45 <= age <= 54:
        return age_sex_string + "45_54"
    elif 55 <= age <= 94:
        if new_enrollee and 65 <= age <= 69:
            return age_sex_string + str(age)
        else:
            lower = int(age / 5) * 5
            upper = lower + 4
            return age_sex_string + "{}_{}".format(lower, upper)
    elif 95 <= age:
        return age_sex_string + "95_gt"


def _diagnoses_to_hccs(icd_mapping, hcc_hierachy, diagnoses, age, sex):
    """Returns a list of hierachical condition categories, implied by a set of diagnoses

    Arguments:
        diagnoses {[string]} -- A list of ICD-10 codes

    Returns:
        [int] -- A list of HCCs, represented as ints
    """
    # Normalize codes by uppercasing and stripping out periods
    diagnoses = [d.strip().upper().replace(".", "") for d in diagnoses]

    hccs = set()

    # get the union of all hccs implied by individual diagnoses
    for d in diagnoses:
        # some special case edits based on V22I0ED2.TXT
        if sex == 2 and d in {"D66", "D67"}:
            hccs.update({48})
        elif age < 18 and d in {
            "J410",
            "J411",
            "J418",
            "J42",
            "J430",
            "J431",
            "J432",
            "J438",
            "J439",
            "J440",
            "J441",
            "J449",
            "J982",
            "J983",
        }:
            hccs.update({112})
        elif age < 6 or age > 18 and d == "F3481":
            pass
        else:
            # If not special case, default to general mapping
            hccs.update(icd_mapping.get(d, []))

    # remove HCCs that are already implied by more specific categories in the hierachy
    for cc in hccs.copy():
        hccs.difference_update(hcc_hierachy.get(cc, []))

    return hccs


def get_age_in_model_year(dob, model_year):
    """Gets the age of a patient relative to Feb 1 of a given model year

    Arguments:
        dob {datetime.datetime | string} -- dob as a datetime or string in format 'YYYY-MM-DD'
        model_year {int} -- Year as

    Returns:
        int -- age as an integer
    """

    if type(dob) == str:
        dob = datetime.strptime(dob, "%Y-%m-%d")
    as_of_date = datetime(year=model_year, month=2, day=1)
    return (
        as_of_date.year
        - dob.year
        - ((as_of_date.month, as_of_date.day) < (dob.month, dob.day))
    )


def _explain_score(
    model_abbreviations, interaction_var_descriptions, hcc_labels, score_components
):
    """Given a dictionay of model coefficients and scores, returns
    a more verbose explanation of what the coefficients mean, and
    how the individual components contribute to the overall score

    Arguments:
        score_components {dict} -- A dictionary of coefficients of the form
            {"coefficient_name" : coefficient_value}
        Intended to be called on the result of compute_risk_score_componenents

    Returns:
        dict -- A dictionary with more info, of the form
        {
             "total": number,
            "demographic_components": [{
                "variable_name" : name of the coefficient,
                "description" : human readable description of what the coefficient means,
                "score" : magnitude of the coefficient
            }],
            "hcc_components": [{
                "variable_name" : name of the coefficient,
                "description" : human readable description of what the coefficient means,
                "score" : magnitude of the coefficient
            }],
            "interaction_components": [{
                "variable_name" : name of the coefficient,
                "description" : human readable description of what the coefficient means,
                "score" : magnitude of the coefficient
            }],
        }
    """
    output = {
        "total": round(sum(score_components.values()), 3),
        "demographic_components": [],
        "hcc_components": [],
        "interaction_components": [],
    }
    # output["normalized_total"] = output["total"] / CODING_INTENSITY_NORMALIZATION

    demographic_regex = re.compile(
        """
        \S*                     # any chars
        (?P<sex>m|f)            # sex
        (?P<age_lo>\d{1,2})     # lower age limit
        (_                      # optional underscore
        (?P<age_hi>\d{1,2}|gt)  # optional upper age limit
        )?$
        """,
        re.VERBOSE,
    )
    interaction_regex = re.compile(
        """
        \S*                     # any
        (?P<var_name>{})$       # name of interaction variables
        """.format(
            "|".join(interaction_var_descriptions.keys())
        ),
        re.VERBOSE,
    )
    hcc_regex = re.compile(
        """
        ^(?P<model_abbr>{})      # model abbreviation
        \_hcc
        (?P<hcc>\d+)$           # hcc number
        """.format(
            "|".join(model_abbreviations)
        ),
        re.VERBOSE,
    )
    for component, score in score_components.items():
        m = re.match(demographic_regex, component)
        if m:
            sex = m.group("sex")
            age_lo = m.group("age_lo")
            age_hi = m.group("age_hi")
            description = "{} with age ".format("Male" if sex == "m" else "Female")
            if age_hi == "gt":
                description += " greater than {}".format(age_lo)
            elif age_hi:
                description += "in range {} to {}".format(age_lo, age_hi)
            else:
                description += "equal to {}".format(age_lo)

            output["demographic_components"].append(
                {"variable_name": component, "score": score, "description": description}
            )

        m = re.match(interaction_regex, component)
        if m:
            output["interaction_components"].append(
                {
                    "variable_name": component,
                    "score": score,
                    "description": interaction_var_descriptions.get(
                        m.group("var_name"), "unknown"
                    ),
                }
            )

        m = re.match(hcc_regex, component)
        if m:
            output["hcc_components"].append(
                {
                    "variable_name": component,
                    "score": score,
                    "description": hcc_labels[int(m.group("hcc"))],
                }
            )
    return output

