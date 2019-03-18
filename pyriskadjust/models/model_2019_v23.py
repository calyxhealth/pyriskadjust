"""Model implements CMS-HCC software V2318.83.P1"""

from pyriskadjust.icd_mapping.mapping_2019_v23 import ICD_MAPPING
from pyriskadjust.hccs.hccs_v23 import HCC_HIERARCHY
from pyriskadjust.hccs.hccs_v23 import HCC_LABELS
from pyriskadjust.coefficients.coefficients_2019_v23 import COEFFICIENTS
from pyriskadjust.models.common import (
    MODEL_DESCRIPTIONS,
    MODEL_ABBREVIATIONS,
    get_age_sex_string,
    _diagnoses_to_hccs,
    _explain_score,
)
import logging

INTERACTION_VARIABLE_DESCRIPTIONS = {
    "hcc47_gcancer": "Immunity Disorders & Cancer",
    "hcc85_gdiabetesmellit": "Congestive Heart Failure & Diabetes",
    "hcc85_gcopdcf": "Congestive Heart Failure & Cystic Fibrosis/COPD",
    "hcc85_grenal_v23": "Congestive Heart Failure & Renal Failure (2019)",
    "grespdepandarre_gcopdcf": "Cardio-Respiratory Failure & Cystic Fibrosis/COPD",
    "hcc85_hcc96": "Congestive Heart failure & Specified Heart Arrhythmias",
    "disable_substabuse_psych_v23": "Substance Misuse & Psychiatric Disorder (2019)",
    "originallydisabled_female": "Female who originally qualified due to disability",
    "originallydisabled_male": "Male who originally qualified due to disability",
    "chf_gcopdcf": "Congestive Heart Failure & Cystic Fibrosis/COPD",
    "gcopdcf_card_resp_fail": "Cardio-Respiratory Failure & Cystic Fibrosis/COPD",
    "sepsis_pressure_ulcer": "Sepsis & Pressure Ulcer",
    "sepsis_artif_openings": "Sepis & Angina Pectoris",
    "art_openings_press_ulcer": "Pressure Ulcer & Angina Pectoris",
    "diabetes_chf": "Diabetes & Congestive Heart Failure",
    "gcopdcf_asp_spec_bact_pneum": "COPD & Aspiration and Specified Bacterial Pneumonias",
    "asp_spec_b_pneum_pres_ulc": "Pressure Ulcer & Aspiration and Specified Bacterial Pneumonias",
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


def explain_score(score_components):
    return _explain_score(
        MODEL_ABBREVIATIONS,
        INTERACTION_VARIABLE_DESCRIPTIONS,
        HCC_LABELS,
        score_components,
    )


def diagnoses_to_hccs(diagnoses, age, sex):
    return _diagnoses_to_hccs(ICD_MAPPING, HCC_HIERARCHY, diagnoses, age, sex)


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
        sex {int} -- 1=male, 2=female

    Keyword Arguments:
        long_term_institutional_in_medicaid {bool} -- True if number of months in Medicaid in payment year > 0. This is only relevant to the Institutional model (default: {False})
        new_enrollee_in_medicaid {bool} -- True if new Medicare enrollee and number of months in Medicaid in payment year > 0. This is only relevant to the two New Enrollee models (default: {False})
        original_entitlement_reason {int} -- Original entitlement reason. 0 = Old Age, 1 = Disability, 2 = End Stage Renal Disease, 3 = both Disability and ESRD (default: {0})
        model {str} -- Abbreviation for the model to use (default: {"cna"})

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
            logging.warning(
                "Demographic coefficient not found for patient with age {} and sex {}: {}".format(
                    age, sex, demographic_var
                )
            )
        return output

    # --------- For all other models -----------------------------------

    # Start by getting the demographic variable based on age and sex
    demographic_var = model_prefix + get_age_sex_string(age, sex, new_enrollee=False)
    if demographic_var in COEFFICIENTS:
        output[demographic_var] = COEFFICIENTS[demographic_var]
    else:
        logging.warning(
            "Demographic coefficient not found for patient with age {} and sex {}: {}".format(
                age, sex, demographic_var
            )
        )

    # Now compute the relevant HCCs
    hccs = diagnoses_to_hccs(diagnoses, age, sex)
    hcc_vars = [model_prefix + "hcc{}".format(hcc) for hcc in hccs]
    for v in hcc_vars:
        if v in COEFFICIENTS:
            output[v] = COEFFICIENTS[v]
        else:
            logging.warning("HCC coefficient not found: {}".format(v))

    # Now compute the interaction components
    interaction_vars = []

    # common variables to compute interaction vars
    cancer = bool(hccs.intersection({8, 9, 10, 11, 12}))
    diabetes = bool(hccs.intersection({17, 18, 19}))
    card_resp_fail = bool(hccs.intersection({82, 83, 84}))
    chf = 85 in hccs
    gCopdCF = bool(hccs.intersection({110, 111, 112}))
    renal_v23 = bool(hccs.intersection({134, 135, 136, 137, 138}))
    sepsis = 2 in hccs
    gSubstanceAbuse_v23 = bool(hccs.intersection({54, 55, 56}))
    gPsychiatric_v23 = bool(hccs.intersection({57, 58, 59, 60}))

    # --------- Community Models ------------------

    if model in {"cna", "cnd", "cfa", "cfd", "cpa", "cpd"}:
        # %*community models interactions
        if 47 in hccs and cancer:
            interaction_vars.append("hcc47_gcancer")
        if chf and diabetes:
            interaction_vars.append("hcc85_gdiabetesmellit")
        if chf and gCopdCF:
            interaction_vars.append("hcc85_gcopdcf")
        if chf and renal_v23:
            interaction_vars.append("hcc85_grenal_v23")
        if card_resp_fail and gCopdCF:
            interaction_vars.append("grespdepandarre_gcopdcf")
        if chf and 96 in hccs:
            interaction_vars.append("hcc85_hcc96")

        # in the models for aged patients, we also take into account
        # whether they originally qualified due to disability
        if model in {"cna", "cfa", "cpa"}:
            if is_originally_disabled and int(sex) == 2:
                interaction_vars.append("originallydisabled_female")
            if is_originally_disabled and int(sex) == 1:
                interaction_vars.append("originallydisabled_male")

        if model in {"cnd", "cfd", "cpd"}:
            if age < 65 and gSubstanceAbuse_v23 and gPsychiatric_v23:
                interaction_vars.append("disable_substabuse_psych_v23")

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
            interaction_vars.append("art_openings_press_ulcer")

        if diabetes and chf:
            interaction_vars.append("diabetes_chf")
        if gCopdCF and 114 in hccs:
            interaction_vars.append("gcopdcf_asp_spec_b_pneum")
        if pressure_ulcer and 114 in hccs:
            interaction_vars.append("asp_spec_b_pneum_pres_ulc")
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
            logging.warning("Warning, interaction coefficient not found: {}".format(v))

    return output
