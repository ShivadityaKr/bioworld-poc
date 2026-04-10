from rules.r1_mandatory_fields import R1MandatoryFields
from rules.r2_sku_suffix import R2SKUSuffix
from rules.r3_property_validation import R3PropertyValidation

RULE_REGISTRY: dict = {
    "R1": R1MandatoryFields(),
    "R2": R2SKUSuffix(),
    "R3": R3PropertyValidation(),
    # Future rules registered here when implemented
}
