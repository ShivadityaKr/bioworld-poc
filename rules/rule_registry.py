from rules.r1_1_mandatory_fields import R1_1_MandatoryFields
from rules.r1_2_sku_suffix import R1_2_SKUSuffix
from rules.r2_1_property_art import R2_1_PropertyArt
from rules.r2_2_character_mapping import R2_2_CharacterMapping
from rules.r3_1_property_rules import R3_1_PropertyRules
from rules.r3_2_property_mixing import R3_2_PropertyMixing
from rules.r4_1_rights_distribution import R4_1_RightsDistribution
from rules.r5_1_packaging import R5_1_Packaging
from rules.r5_2_tm_validation import R5_2_TMValidation

RULE_REGISTRY: dict = {
    "R1.1": R1_1_MandatoryFields(),
    "R1.2": R1_2_SKUSuffix(),
    "R2.1": R2_1_PropertyArt(),
    "R2.2": R2_2_CharacterMapping(),
    "R3.1": R3_1_PropertyRules(),
    "R3.2": R3_2_PropertyMixing(),
    "R4.1": R4_1_RightsDistribution(),
    "R5.1": R5_1_Packaging(),
    "R5.2": R5_2_TMValidation(),
}
