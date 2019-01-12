"""Model implements CMS-HCC software V2218.79.O1"""

import re
from pyriskadjust.icd_mapping.mapping_2018_v22 import ICD_MAPPING
from pyriskadjust.hccs.hccs_v22 import HCC_HIERARCHY
from pyriskadjust.hccs.hccs_v22 import HCC_LABELS
from pyriskadjust.coefficients.coefficients_2018_v22 import COEFFICIENTS


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

INTERACTION_VARIABLE_DESCRIPTIONS = {
    "hcc47_gcancer": "Immunity Disorders & Cancer",
    "hcc85_gdiabetesmellit": "Congestive Heart Failure & Diabetes",
    "hcc85_gcopdcf": "Congestive Heart Failure & Cystic Fibrosis/COPD",
    "hcc85_grenal": "Congestive Heart Failure & Renal Failure",
    "grespdepandarre_gcopdcf": "Cardio-Respiratory Failure & Cystic Fibrosis/COPD",
    "hcc85_hcc96": "Congestive Heart failure & Specified Heart Arrhythmias",
    "gsubstanceabuse_gpsychiatric": "Drug/Alcohol Misuse & Psychiatric Disorder",
    "originallydisabled_female": "Female who originally qualified due to disability",
    "originallydisabled_male": "Male who originally qualified due to disability",
    "chf_gcopdcf": "Congestive Heart Failure & Cystic Fibrosis/COPD",
    "gcopdcf_card_resp_fail": "Cardio-Respiratory Failure & Cystic Fibrosis/COPD",
    "asp_spec_bact_pneum_pres_ulc": "Pressure Ulcer & Aspiration and Specified Bacterial Pneumonias",
    "sepsis_asp_spec_bact_pneum": "Sepsis & Aspiration and Specified Bacterial Pneumonias",
    "schizophrenia_gcopdcf": "Schizophrenia & Cystic Fibrosis/COPD",
    "schizophrenia_chf": "Schizophrenia & Congestive Heart Failure",
    "schizophrenia_seizures": "Schizophrenia & Seizures",
    "disabled_hcc85": "Disabled & Congestive Heart Failure",
    "disabled_pressure_ulcer": "Disabled & Pressure Ulcer",
    "disabled_hcc161": "Disabled & Chronic Ulcer of Skin, Except Pressure",
    "disabled_hcc39": "Disabled & Bone/Joint/Muscle Infections/Necrosis",
    "disabled_hcc77": "Disabled & Multiple Sclerosis",
    "disabled_hcc6": "Disbaled & Opportunistic Infections",
    "ltimcaid": "Institutional Model & Patient on Medicaid at least part of the payment year",
    "origds": "Patient is over 65 & Original reason for entitlement is disability",
}

INTERACTION_VARIABLES = INTERACTION_VARIABLE_DESCRIPTIONS.keys()


def compute_risk_score_components(
    diagnoses,
    age,
    sex,
    long_term_institutional_in_medicaid=False,
    new_enrollee_in_medicaid=False,
    original_entitlement_reason=0,
    model="cna",
):
    """Computes the risk score for a patient, given a list of diagnoses as ICD_10 codes,
    their age, sex, etc. 

    Arguments:
        diagnoses {[list]} -- List of ICD-10 codes, as strings
        age {int} -- patient's age, as integer. This should be computed as of Feb 1 for a given model year
        sex {int} -- 1=male, 2=femail

    Keyword Arguments:
        long_term_institutional_in_medicaid {bool} -- True if number of months in Medicaid in payment year > 0. This is only relevant to the Institutional model (default: {False})
        new_enrollee_in_medicaid {bool} -- True if new Medicare enrollee and number of months in Medicaid in payment year > 0. This is only relevant to the two New Enrollee models (default: {False})
        original_entitlement_reason {int} -- Original entitlement reason. 0 = Old Age, 1 = Disability, 2 = End Stage Renal Disease, 3 = both Disability and ESRD (default: {0})
        model {str} -- Abbreviation for the model to use (default: {"cna"})

    Raises:
        ValueError -- if model coefficient isn't found

    Returns:
        dict -- Dictionary of the form 
        {
            "coefficient_name" : coefficient_value,
            "coefficient_name" : coefficient_value
        }
    """

    output = {}

    model_prefix = "{}_".format(model)

    # young and disabled
    is_disabled = age < 65 and int(original_entitlement_reason) != 0
    # old but original entitlement reason is disability
    is_originally_disabled = age >= 65 and int(original_entitlement_reason) == 1

    # --------- New Enrollee and SNP New Enrollee models -----

    # These models are not based on HCCs. They are based solely on sex, age,
    # whether the new enrollee qualified due to disability, and
    # whether the new enrollee was on medicaid for at least part of the year
    if model == "ne" or model == "snpne":
        if not new_enrollee_in_medicaid and not is_originally_disabled:
            demographic_var = model_prefix + "nmcaid_norigdis_"
        elif new_enrollee_in_medicaid and not is_originally_disabled:
            demographic_var = model_prefix + "mcaid_norigdis_"
        elif not new_enrollee_in_medicaid and is_originally_disabled:
            demographic_var = model_prefix + "nmcaid_origdis_"
        elif new_enrollee_in_medicaid and is_originally_disabled:
            demographic_var = model_prefix + "mcaid_origdis_"

        demographic_var += get_age_sex_string(age, sex, new_enrollee=True)
        if demographic_var in COEFFICIENTS:
            output[demographic_var] = COEFFICIENTS[demographic_var]
        else:
            raise ValueError("No demographic coefficient found for new enrollee")
        return output

    # --------- For all other models -----------------------------------

    # Start by getting the demographic variable based on age and sex
    demographic_var = model_prefix + get_age_sex_string(age, sex, new_enrollee=False)
    if demographic_var in COEFFICIENTS:
        output[demographic_var] = COEFFICIENTS[demographic_var]
    else:
        raise ValueError("No demographic coefficient found for model")

    # Now compute the relevant HCCs
    hccs = diagnoses_to_hccs(diagnoses, age, sex)
    hcc_vars = [model_prefix + "hcc{}".format(hcc) for hcc in hccs]
    for v in hcc_vars:
        if v in COEFFICIENTS:
            output[v] = COEFFICIENTS[v]
        else:
            raise ValueError("HCC coefficient not found")

    # Now compute the interaction components
    interaction_vars = []

    # common variables to compute interaction vars
    cancer = bool(hccs.intersection({8, 9, 10, 11, 12}))
    diabetes = bool(hccs.intersection({17, 18, 19}))
    card_resp_fail = bool(hccs.intersection({82, 83, 84}))
    chf = 85 in hccs
    gCopdCF = bool(hccs.intersection({110, 111, 112}))
    renal = bool(hccs.intersection({134, 135, 136, 137}))
    sepsis = 2 in hccs
    gSubstanceAbuse = bool(hccs.intersection({54, 55}))
    gPsychiatric = bool(hccs.intersection({57, 58}))

    # --------- Community Models ------------------

    if model in {"cna", "cnd", "cfa", "cfd", "cpa", "cpd"}:
        # %*community models interactions
        if 47 in hccs and cancer:
            interaction_vars.append("hcc47_gcancer")
        if chf and diabetes:
            interaction_vars.append("hcc85_gdiabetesmellit")
        if chf and gCopdCF:
            interaction_vars.append("hcc85_gcopdcf")
        if chf and renal:
            interaction_vars.append("hcc85_grenal")
        if card_resp_fail and gCopdCF:
            interaction_vars.append("grespdepandarre_gcopdcf")
        if chf and 96 in hccs:
            interaction_vars.append("hcc85_hcc96")
        if gSubstanceAbuse and gPsychiatric:
            interaction_vars.append("gsubstanceabuse_gpsychiatric")

        # in the models for aged patients, we also take into account
        # whether they originally qualified due to disability
        if model in {"cna", "cfa", "cpa"}:
            if is_originally_disabled and int(sex) == 2:
                interaction_vars.append("originallydisabled_female")
            if is_originally_disabled and int(sex) == 1:
                interaction_vars.append("originallydisabled_male")

    # --------- Institutional Model ------------------

    if model == "ins":
        # %*institutional model;
        pressure_ulcer = bool(hccs.intersection({157, 158}))  # /*10/19/2012*/

        if chf and gCopdCF:
            interaction_vars.append("chf_gcopdcf")
        if gCopdCF and card_resp_fail:
            interaction_vars.append("gcopdcf_card_resp_fail")
        if sepsis and pressure_ulcer:
            interaction_vars.append("sepsis_pressure_ulcer")
        if sepsis and 188 in hccs:
            interaction_vars.append("sepsis_artif_openings")
        if pressure_ulcer and 188 in hccs:
            interaction_vars.append("art_openings_pressure_ulcer")

        if diabetes and chf:
            interaction_vars.append("diabetes_chf")
        if gCopdCF and 114 in hccs:
            interaction_vars.append("gcopdcf_asp_spec_bact_pneum")
        if pressure_ulcer and 114 in hccs:
            interaction_vars.append("asp_spec_bact_pneum_pres_ulc")
        if sepsis and 114 in hccs:
            interaction_vars.append("sepsis_asp_spec_bact_pneum")
        if gCopdCF and 57 in hccs:
            interaction_vars.append("schizophrenia_gcopdcf")
        if chf and 57 in hccs:
            interaction_vars.append("schizophrenia_chf")
        if 57 in hccs and 79 in hccs:
            interaction_vars.append("schizophrenia_seizures")

        if is_disabled and 85 in hccs:
            interaction_vars.append("disabled_hcc85")
        if is_disabled and pressure_ulcer:
            interaction_vars.append("disabled_pressure_ulcer")
        if is_disabled and 161 in hccs:
            interaction_vars.append("disabled_hcc161")
        if is_disabled and 39 in hccs:
            interaction_vars.append("disabled_hcc39")
        if is_disabled and 77 in hccs:
            interaction_vars.append("disabled_hcc77")
        if is_disabled and 6 in hccs:
            interaction_vars.append("disabled_hcc6")

        if long_term_institutional_in_medicaid:
            interaction_vars.append("ltimcaid")
        if is_originally_disabled:
            interaction_vars.append("origds")

    for v in (model_prefix + iv for iv in interaction_vars):
        if v in COEFFICIENTS:
            output[v] = COEFFICIENTS[v]
        else:
            raise ValueError("Interaction coefficient not found")

    return output


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


def hcc_to_label(hcc):
    return HCC_LABELS.get(hcc, "")


def diagnoses_to_hccs(diagnoses, age, sex):
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
            hccs.update(ICD_MAPPING.get(d, []))

    # remove HCCs that are already implied by more specific categories in the hierachy
    for cc in hccs.copy():
        hccs.difference_update(HCC_HIERARCHY.get(cc, []))

    return hccs


# CODING_INTENSITY_NORMALIZATION = 1.017
def explain_score(score_components):
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
            "|".join(INTERACTION_VARIABLES)
        ),
        re.VERBOSE,
    )
    hcc_regex = re.compile(
        """
        ^(?P<model_abbr>{})      # model abbreviation
        \_hcc
        (?P<hcc>\d+)$           # hcc number
        """.format(
            "|".join(MODEL_ABBREVIATIONS)
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
                    "description": INTERACTION_VARIABLE_DESCRIPTIONS.get(
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
                    "description": HCC_LABELS[int(m.group("hcc"))],
                }
            )
    return output
