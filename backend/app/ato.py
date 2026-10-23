"""ATO rental property schedule labels and default categories.

Every category maps to one schedule label so the accountant report always
lines up with the rental schedule / myTax "Rent" section, no matter how the
user names their own categories.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AtoLabel:
    key: str
    label: str
    kind: str  # income | expense | excluded
    order: int
    help: str = ""


ATO_LABELS: list[AtoLabel] = [
    AtoLabel("gross_rent", "Gross rent", "income", 1, "Rent received, including from the agent before fees"),
    AtoLabel("other_income", "Other rental-related income", "income", 2,
             "Insurance payouts for lost rent, bond kept for damage/unpaid rent, letting fees reimbursed"),
    AtoLabel("advertising", "Advertising for tenants", "expense", 10),
    AtoLabel("body_corporate", "Body corporate fees and charges", "expense", 11),
    AtoLabel("borrowing", "Borrowing expenses", "expense", 12, "Loan establishment, mortgage registration, LMI – usually spread over 5 years"),
    AtoLabel("cleaning", "Cleaning", "expense", 13),
    AtoLabel("council_rates", "Council rates", "expense", 14),
    AtoLabel("capital_allowances", "Capital allowances (depreciation on plant)", "expense", 15, "Usually from a depreciation schedule"),
    AtoLabel("gardening", "Gardening/lawn mowing", "expense", 16),
    AtoLabel("insurance", "Insurance", "expense", 17, "Landlord, building and contents insurance"),
    AtoLabel("interest", "Interest on loans", "expense", 18, "Interest only – principal repayments are not deductible"),
    AtoLabel("land_tax", "Land tax", "expense", 19),
    AtoLabel("legal", "Legal fees", "expense", 20),
    AtoLabel("pest_control", "Pest control", "expense", 21),
    AtoLabel("agent_fees", "Property agent fees/commission", "expense", 22),
    AtoLabel("repairs", "Repairs and maintenance", "expense", 23, "Repairs only – improvements are capital"),
    AtoLabel("capital_works", "Capital works deductions", "expense", 24, "Usually from a depreciation schedule"),
    AtoLabel("stationery_phone", "Stationery, telephone and postage", "expense", 25),
    AtoLabel("travel", "Travel expenses", "expense", 26, "Generally not deductible for residential rentals since 1 July 2017"),
    AtoLabel("water", "Water charges", "expense", 27),
    AtoLabel("sundry", "Sundry rental expenses", "expense", 28),
    AtoLabel("excluded", "Capital / non-deductible (tracked, not claimed)", "excluded", 90,
             "Improvements, purchase costs, principal repayments – kept for the CGT cost base"),
]

ATO_BY_KEY = {a.key: a for a in ATO_LABELS}

# name, ato key, import keywords (lower-case substrings)
DEFAULT_CATEGORIES: list[tuple[str, str, list[str]]] = [
    ("Rent received", "gross_rent", ["rent received", "rental income", "rent"]),
    ("Other rental income", "other_income", ["insurance claim", "bond"]),
    ("Interest on loan", "interest", ["interest"]),
    ("Council rates", "council_rates", ["rates"]),
    ("Water", "water", ["water"]),
    ("Landlord insurance", "insurance", ["insurance", "youi"]),
    ("Pest control", "pest_control", ["pest"]),
    ("Repairs & maintenance", "repairs", ["repair", "maintenance", "plumb", "electric"]),
    ("Property management fees", "agent_fees", ["management fee", "agent", "commission", "letting fee"]),
    ("Advertising", "advertising", ["advertis"]),
    ("Body corporate", "body_corporate", ["body corp", "strata"]),
    ("Borrowing expenses", "borrowing", ["borrowing", "loan establishment", "lmi"]),
    ("Cleaning", "cleaning", ["clean"]),
    ("Gardening & lawns", "gardening", ["garden", "lawn", "mowing"]),
    ("Land tax", "land_tax", ["land tax"]),
    ("Legal fees", "legal", ["legal", "solicitor", "conveyanc"]),
    ("Depreciation (plant & equipment)", "capital_allowances", ["depreciation"]),
    ("Capital works deduction", "capital_works", ["capital works"]),
    ("Phone, internet & postage", "stationery_phone", ["internet", "phone", "postage", "stationery"]),
    ("Smoke alarm servicing", "sundry", ["smoke alarm"]),
    ("Bank fees", "sundry", ["bank fee", "account fee"]),
    ("Sundry", "sundry", ["sundry"]),
    ("Capital improvement", "excluded", ["renovation", "improvement"]),
    ("Loan principal repayment", "excluded", ["principal"]),
]
