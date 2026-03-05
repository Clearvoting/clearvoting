"""Mock data for demo mode when no Congress API key is configured.

Bills and members are based on real 119th Congress (2025-2026) data
researched from Congress.gov. Summaries are written in ClearVote's
factual, no-adjectives style.
"""

# --- Florida Members (current as of 2025) ---

MOCK_MEMBERS_FL = {
    "members": [
        {
            "bioguideId": "S001217",
            "name": "Scott, Rick",
            "directOrderName": "Rick Scott",
            "state": "Florida",
            "district": None,
            "partyName": "Republican",
            "partyCode": "R",
            "terms": {"item": [
                {"chamber": "Senate", "congress": 119, "startYear": 2025, "endYear": None, "stateCode": "FL"},
                {"chamber": "Senate", "congress": 118, "startYear": 2023, "endYear": 2025, "stateCode": "FL"},
                {"chamber": "Senate", "congress": 117, "startYear": 2021, "endYear": 2023, "stateCode": "FL"},
                {"chamber": "Senate", "congress": 116, "startYear": 2019, "endYear": 2021, "stateCode": "FL"},
            ]},
            "depiction": {"imageUrl": "https://www.congress.gov/img/member/s001217_200.jpg", "attribution": ""},
            "currentMember": True,
        },
        {
            "bioguideId": "M001244",
            "name": "Moody, Ashley",
            "directOrderName": "Ashley Moody",
            "state": "Florida",
            "district": None,
            "partyName": "Republican",
            "partyCode": "R",
            "terms": {"item": [
                {"chamber": "Senate", "congress": 119, "startYear": 2025, "endYear": None, "stateCode": "FL"},
            ]},
            "depiction": {"imageUrl": "https://bioguide.congress.gov/photo/695d82c8550dfb80c3063bee.jpg", "attribution": ""},
            "currentMember": True,
        },
        {
            "bioguideId": "D000032",
            "name": "Donalds, Byron",
            "directOrderName": "Byron Donalds",
            "state": "Florida",
            "district": 19,
            "partyName": "Republican",
            "partyCode": "R",
            "terms": {"item": [
                {"chamber": "House of Representatives", "congress": 119, "startYear": 2025, "endYear": None, "stateCode": "FL"},
                {"chamber": "House of Representatives", "congress": 118, "startYear": 2023, "endYear": 2025, "stateCode": "FL"},
                {"chamber": "House of Representatives", "congress": 117, "startYear": 2021, "endYear": 2023, "stateCode": "FL"},
            ]},
            "depiction": {"imageUrl": "https://www.congress.gov/img/member/d000032_200.jpg", "attribution": ""},
            "currentMember": True,
        },
        {
            "bioguideId": "W000823",
            "name": "Waltz, Michael",
            "directOrderName": "Michael Waltz",
            "state": "Florida",
            "district": 6,
            "partyName": "Republican",
            "partyCode": "R",
            "terms": {"item": [
                {"chamber": "House of Representatives", "congress": 119, "startYear": 2025, "endYear": None, "stateCode": "FL"},
                {"chamber": "House of Representatives", "congress": 118, "startYear": 2023, "endYear": 2025, "stateCode": "FL"},
                {"chamber": "House of Representatives", "congress": 117, "startYear": 2021, "endYear": 2023, "stateCode": "FL"},
            ]},
            "depiction": {"imageUrl": "https://www.congress.gov/img/member/w000823_200.jpg", "attribution": ""},
            "currentMember": True,
        },
    ]
}

MOCK_MEMBERS_NY = {
    "members": [
        {
            "bioguideId": "G000555",
            "name": "Gillibrand, Kirsten",
            "directOrderName": "Kirsten Gillibrand",
            "state": "New York",
            "district": None,
            "partyName": "Democrat",
            "partyCode": "D",
            "terms": {"item": [
                {"chamber": "Senate", "congress": 119, "startYear": 2025, "endYear": None, "stateCode": "NY"},
            ]},
            "depiction": {"imageUrl": "https://www.congress.gov/img/member/g000555_200.jpg", "attribution": ""},
            "currentMember": True,
        },
        {
            "bioguideId": "S000148",
            "name": "Schumer, Charles",
            "directOrderName": "Charles Schumer",
            "state": "New York",
            "district": None,
            "partyName": "Democrat",
            "partyCode": "D",
            "terms": {"item": [
                {"chamber": "Senate", "congress": 119, "startYear": 2025, "endYear": None, "stateCode": "NY"},
            ]},
            "depiction": {"imageUrl": "https://www.congress.gov/img/member/s000148_200.jpg", "attribution": ""},
            "currentMember": True,
        },
    ]
}

MOCK_MEMBERS_TX = {
    "members": [
        {
            "bioguideId": "C001098",
            "name": "Cruz, Ted",
            "directOrderName": "Ted Cruz",
            "state": "Texas",
            "district": None,
            "partyName": "Republican",
            "partyCode": "R",
            "terms": {"item": [
                {"chamber": "Senate", "congress": 119, "startYear": 2025, "endYear": None, "stateCode": "TX"},
            ]},
            "depiction": {"imageUrl": "https://www.congress.gov/img/member/c001098_200.jpg", "attribution": ""},
            "currentMember": True,
        },
        {
            "bioguideId": "C001056",
            "name": "Cornyn, John",
            "directOrderName": "John Cornyn",
            "state": "Texas",
            "district": None,
            "partyName": "Republican",
            "partyCode": "R",
            "terms": {"item": [
                {"chamber": "Senate", "congress": 119, "startYear": 2025, "endYear": None, "stateCode": "TX"},
            ]},
            "depiction": {"imageUrl": "https://www.congress.gov/img/member/c001056_200.jpg", "attribution": ""},
            "currentMember": True,
        },
    ]
}

# --- Member Details ---

MOCK_MEMBER_DETAILS = {
    "S001217": {
        "member": {
            "bioguideId": "S001217",
            "firstName": "Rick",
            "lastName": "Scott",
            "directOrderName": "Rick Scott",
            "state": "Florida",
            "partyName": "Republican",
            "party": "Republican",
            "currentMember": True,
            "terms": {"item": [
                {"chamber": "Senate", "congress": 119, "startYear": 2025, "endYear": None, "stateCode": "FL"},
                {"chamber": "Senate", "congress": 118, "startYear": 2023, "endYear": 2025, "stateCode": "FL"},
                {"chamber": "Senate", "congress": 117, "startYear": 2021, "endYear": 2023, "stateCode": "FL"},
                {"chamber": "Senate", "congress": 116, "startYear": 2019, "endYear": 2021, "stateCode": "FL"},
            ]},
            "depiction": {"imageUrl": "https://www.congress.gov/img/member/s001217_200.jpg"},
            "sponsoredLegislation": {"count": 618, "url": ""},
            "cosponsoredLegislation": {"count": 1695, "url": ""},
        }
    },
    "M001244": {
        "member": {
            "bioguideId": "M001244",
            "firstName": "Ashley",
            "lastName": "Moody",
            "directOrderName": "Ashley Moody",
            "state": "Florida",
            "partyName": "Republican",
            "party": "Republican",
            "currentMember": True,
            "terms": {"item": [
                {"chamber": "Senate", "congress": 119, "startYear": 2025, "endYear": None, "stateCode": "FL"},
            ]},
            "depiction": {"imageUrl": "https://bioguide.congress.gov/photo/695d82c8550dfb80c3063bee.jpg"},
            "sponsoredLegislation": {"count": 33, "url": ""},
            "cosponsoredLegislation": {"count": 112, "url": ""},
        }
    },
    "D000032": {
        "member": {
            "bioguideId": "D000032",
            "firstName": "Byron",
            "lastName": "Donalds",
            "directOrderName": "Byron Donalds",
            "state": "Florida",
            "district": 19,
            "partyName": "Republican",
            "party": "Republican",
            "currentMember": True,
            "terms": {"item": [
                {"chamber": "House of Representatives", "congress": 119, "startYear": 2025, "endYear": None, "stateCode": "FL"},
                {"chamber": "House of Representatives", "congress": 118, "startYear": 2023, "endYear": 2025, "stateCode": "FL"},
                {"chamber": "House of Representatives", "congress": 117, "startYear": 2021, "endYear": 2023, "stateCode": "FL"},
            ]},
            "depiction": {"imageUrl": "https://www.congress.gov/img/member/d000032_200.jpg"},
            "sponsoredLegislation": {"count": 84, "url": ""},
            "cosponsoredLegislation": {"count": 315, "url": ""},
        }
    },
    "G000555": {
        "member": {
            "bioguideId": "G000555",
            "firstName": "Kirsten",
            "lastName": "Gillibrand",
            "directOrderName": "Kirsten Gillibrand",
            "state": "New York",
            "partyName": "Democrat",
            "party": "Democrat",
            "currentMember": True,
            "terms": {"item": [
                {"chamber": "Senate", "congress": 119, "startYear": 2025, "endYear": None, "stateCode": "NY"},
                {"chamber": "Senate", "congress": 118, "startYear": 2023, "endYear": 2025, "stateCode": "NY"},
                {"chamber": "Senate", "congress": 117, "startYear": 2021, "endYear": 2023, "stateCode": "NY"},
                {"chamber": "Senate", "congress": 116, "startYear": 2019, "endYear": 2021, "stateCode": "NY"},
                {"chamber": "Senate", "congress": 115, "startYear": 2017, "endYear": 2019, "stateCode": "NY"},
                {"chamber": "House of Representatives", "congress": 111, "startYear": 2009, "endYear": 2011, "stateCode": "NY"},
            ]},
            "depiction": {"imageUrl": "https://www.congress.gov/img/member/g000555_200.jpg"},
            "sponsoredLegislation": {"count": 612, "url": ""},
            "cosponsoredLegislation": {"count": 3041, "url": ""},
        }
    },
}

# --- Bills (real 119th Congress bills relevant to Florida) ---

MOCK_BILLS = {
    "bills": [
        {
            "congress": 119,
            "type": "HR",
            "number": "1",
            "title": "One Big Beautiful Bill Act",
            "latestTitle": "One Big Beautiful Bill Act",
            "latestAction": {
                "actionDate": "2025-07-04",
                "text": "Became Public Law No: 119-21."
            },
            "policyArea": {"name": "Economics and Public Finance"},
        },
        {
            "congress": 119,
            "type": "HR",
            "number": "4494",
            "title": "Flood Insurance Relief Act",
            "latestTitle": "Flood Insurance Relief Act",
            "latestAction": {
                "actionDate": "2025-07-17",
                "text": "Referred to the House Committee on Ways and Means."
            },
            "policyArea": {"name": "Taxation"},
        },
        {
            "congress": 119,
            "type": "HR",
            "number": "152",
            "title": "Federal Disaster Assistance Coordination Act",
            "latestTitle": "Federal Disaster Assistance Coordination Act",
            "latestAction": {
                "actionDate": "2025-01-14",
                "text": "Received in the Senate. Read twice and referred to the Committee on Homeland Security and Governmental Affairs."
            },
            "policyArea": {"name": "Emergency Management"},
        },
        {
            "congress": 119,
            "type": "HR",
            "number": "5484",
            "title": "National Flood Insurance Program Reauthorization and Reform Act of 2025",
            "latestTitle": "National Flood Insurance Program Reauthorization and Reform Act of 2025",
            "latestAction": {
                "actionDate": "2025-09-19",
                "text": "Referred to the Subcommittee on Economic Development, Public Buildings, and Emergency Management."
            },
            "policyArea": {"name": "Finance and Financial Sector"},
        },
        {
            "congress": 119,
            "type": "S",
            "number": "770",
            "title": "Social Security Expansion Act",
            "latestTitle": "Social Security Expansion Act",
            "latestAction": {
                "actionDate": "2025-02-27",
                "text": "Read twice and referred to the Committee on Finance."
            },
            "policyArea": {"name": "Social Welfare"},
        },
        {
            "congress": 119,
            "type": "HR",
            "number": "318",
            "title": "Border Safety and Security Act of 2025",
            "latestTitle": "Border Safety and Security Act of 2025",
            "latestAction": {
                "actionDate": "2025-01-09",
                "text": "Referred to the Subcommittee on Border Security and Enforcement."
            },
            "policyArea": {"name": "Immigration"},
        },
        {
            "congress": 119,
            "type": "S",
            "number": "219",
            "title": "Veterans Health Care Freedom Act",
            "latestTitle": "Veterans Health Care Freedom Act",
            "latestAction": {
                "actionDate": "2025-05-21",
                "text": "Committee on Veterans' Affairs. Hearings held."
            },
            "policyArea": {"name": "Armed Forces and National Security"},
        },
        {
            "congress": 119,
            "type": "HR",
            "number": "1040",
            "title": "Senior Citizens Tax Elimination Act",
            "latestTitle": "Senior Citizens Tax Elimination Act",
            "latestAction": {
                "actionDate": "2025-02-06",
                "text": "Referred to the House Committee on Ways and Means."
            },
            "policyArea": {"name": "Taxation"},
        },
        {
            "congress": 119,
            "type": "HR",
            "number": "6934",
            "title": "National Flood Insurance Program Affordability Act",
            "latestTitle": "National Flood Insurance Program Affordability Act",
            "latestAction": {
                "actionDate": "2025-12-30",
                "text": "Referred to the House Committee on Financial Services."
            },
            "policyArea": {"name": "Finance and Financial Sector"},
        },
        {
            "congress": 119,
            "type": "HR",
            "number": "6017",
            "title": "Veterans Bill of Rights Act",
            "latestTitle": "Veterans Bill of Rights Act",
            "latestAction": {
                "actionDate": "2025-11-10",
                "text": "Referred to the House Committee on Veterans' Affairs."
            },
            "policyArea": {"name": "Armed Forces and National Security"},
        },
    ]
}

# --- Bill Details ---

MOCK_BILL_DETAILS = {
    "119-hr-1": {
        "bill": {
            "congress": 119,
            "type": "HR",
            "number": "1",
            "title": "One Big Beautiful Bill Act",
            "originChamber": "House",
            "latestAction": {
                "actionDate": "2025-07-04",
                "text": "Became Public Law No: 119-21."
            },
            "policyArea": {"name": "Economics and Public Finance"},
            "sponsors": [
                {"bioguideId": "A000375", "fullName": "Rep. Arrington, Jodey C. [R-TX-19]"}
            ],
            "summaries": [
                {"text": "This act reduces taxes, reduces or increases spending for various federal programs, increases the statutory debt limit, and otherwise addresses agencies and programs throughout the federal government. It is a reconciliation bill that includes legislation submitted by several congressional committees. Key provisions include changes to the Supplemental Nutrition Assistance Program (SNAP) work requirements, Medicaid eligibility verification, tax provisions including extensions of the 2017 Tax Cuts and Jobs Act, border security funding, and energy policy changes. The bill passed the House 215-214 and the Senate 51-50."}
            ],
        },
        "subjects": {"legislativeSubjects": [
            {"name": "Budget process"},
            {"name": "Tax rates and credits"},
            {"name": "Immigration"},
            {"name": "Medicaid"},
            {"name": "Supplemental Nutrition Assistance Program (SNAP)"},
            {"name": "Debt ceiling"},
        ]},
    },
    "119-hr-4494": {
        "bill": {
            "congress": 119,
            "type": "HR",
            "number": "4494",
            "title": "Flood Insurance Relief Act",
            "originChamber": "House",
            "latestAction": {
                "actionDate": "2025-07-17",
                "text": "Referred to the House Committee on Ways and Means."
            },
            "policyArea": {"name": "Taxation"},
            "sponsors": [
                {"bioguideId": "D000032", "fullName": "Rep. Donalds, Byron [R-FL-19]"}
            ],
            "summaries": [
                {"text": "This bill allows middle-income homeowners to deduct the cost of flood insurance premiums from their federal taxes. It amends the Internal Revenue Code to create a new above-the-line deduction for National Flood Insurance Program premiums paid by individuals with adjusted gross income below specified thresholds."}
            ],
        },
        "subjects": {"legislativeSubjects": [
            {"name": "Flood insurance"},
            {"name": "Income tax deductions"},
            {"name": "National Flood Insurance Program"},
        ]},
    },
    "119-hr-152": {
        "bill": {
            "congress": 119,
            "type": "HR",
            "number": "152",
            "title": "Federal Disaster Assistance Coordination Act",
            "originChamber": "House",
            "latestAction": {
                "actionDate": "2025-01-14",
                "text": "Received in the Senate. Read twice and referred to the Committee on Homeland Security and Governmental Affairs."
            },
            "policyArea": {"name": "Emergency Management"},
            "sponsors": [
                {"bioguideId": "E000235", "fullName": "Rep. Ezell, Mike [R-MS-4]"}
            ],
            "summaries": [
                {"text": "This bill requires the Federal Emergency Management Agency (FEMA) to streamline disaster information collection, convene a working group on preliminary damage assessments, and provide a report to Congress. FEMA must conduct a study and develop a plan to make information collection from disaster assistance applicants less burdensome, duplicative, and time consuming. The bill also requires FEMA to identify potential emerging technologies such as drones to expedite preliminary damage assessments. The bill passed the House 405-5."}
            ],
        },
        "subjects": {"legislativeSubjects": [
            {"name": "Disaster relief and insurance"},
            {"name": "Federal Emergency Management Agency (FEMA)"},
            {"name": "Government information and archives"},
        ]},
    },
    "119-hr-5484": {
        "bill": {
            "congress": 119,
            "type": "HR",
            "number": "5484",
            "title": "National Flood Insurance Program Reauthorization and Reform Act of 2025",
            "originChamber": "House",
            "latestAction": {
                "actionDate": "2025-09-19",
                "text": "Referred to the Subcommittee on Economic Development, Public Buildings, and Emergency Management."
            },
            "policyArea": {"name": "Finance and Financial Sector"},
            "sponsors": [
                {"bioguideId": "P000034", "fullName": "Rep. Pallone, Frank [D-NJ-6]"}
            ],
            "summaries": [
                {"text": "This bill reauthorizes and reforms the National Flood Insurance Program (NFIP). The NFIP provides flood insurance to property owners, renters, and businesses in participating communities. The program is set to expire without reauthorization. This bill extends the program and addresses affordability, mapping accuracy, and mitigation funding."}
            ],
        },
        "subjects": {"legislativeSubjects": [
            {"name": "Flood insurance"},
            {"name": "National Flood Insurance Program"},
            {"name": "Disaster mitigation"},
        ]},
    },
    "119-s-770": {
        "bill": {
            "congress": 119,
            "type": "S",
            "number": "770",
            "title": "Social Security Expansion Act",
            "originChamber": "Senate",
            "latestAction": {
                "actionDate": "2025-02-27",
                "text": "Read twice and referred to the Committee on Finance."
            },
            "policyArea": {"name": "Social Welfare"},
            "sponsors": [
                {"bioguideId": "S000033", "fullName": "Sen. Sanders, Bernard [I-VT]"}
            ],
            "summaries": [
                {"text": "This bill increases Social Security benefits, expands Social Security payroll taxes, and makes other changes to the Social Security program. It changes the way benefits are calculated by increasing the primary insurance amount, revises cost-of-living adjustments to account for spending of individuals over age 62, and establishes a new minimum benefit for low earners. The bill extends payroll taxes to income above $250,000 (currently capped at $176,100) and combines the Old-Age and Survivors Insurance Trust Fund and Disability Insurance Trust Fund into a single Social Security Trust Fund."}
            ],
        },
        "subjects": {"legislativeSubjects": [
            {"name": "Social Security benefits"},
            {"name": "Payroll taxes"},
            {"name": "Cost-of-living adjustments"},
        ]},
    },
    "119-hr-318": {
        "bill": {
            "congress": 119,
            "type": "HR",
            "number": "318",
            "title": "Border Safety and Security Act of 2025",
            "originChamber": "House",
            "latestAction": {
                "actionDate": "2025-01-09",
                "text": "Referred to the Subcommittee on Border Security and Enforcement."
            },
            "policyArea": {"name": "Immigration"},
            "sponsors": [
                {"bioguideId": "R000614", "fullName": "Rep. Roy, Chip [R-TX-21]"}
            ],
            "summaries": [
                {"text": "This bill requires the Department of Homeland Security (DHS) to suspend the entry of non-U.S. nationals without valid entry documents during any period when DHS cannot detain such an individual or return the individual to a foreign country contiguous to the United States. A state may sue DHS to enforce this requirement. The bill also authorizes DHS to suspend entry of non-U.S. nationals without entry documents at the border if DHS determines such a suspension is necessary to achieve operational control."}
            ],
        },
        "subjects": {"legislativeSubjects": [
            {"name": "Border security"},
            {"name": "Immigration enforcement"},
            {"name": "Asylum"},
        ]},
    },
    "119-s-219": {
        "bill": {
            "congress": 119,
            "type": "S",
            "number": "219",
            "title": "Veterans Health Care Freedom Act",
            "originChamber": "Senate",
            "latestAction": {
                "actionDate": "2025-05-21",
                "text": "Committee on Veterans' Affairs. Hearings held."
            },
            "policyArea": {"name": "Armed Forces and National Security"},
            "sponsors": [
                {"bioguideId": "B001243", "fullName": "Sen. Blackburn, Marsha [R-TN]"}
            ],
            "summaries": [
                {"text": "This bill requires the Department of Veterans Affairs (VA) to implement a three-year pilot program allowing veterans enrolled in the VA health care system to choose health care providers through VA medical facilities, the Veterans Community Care Program (VCCP), or Veterans Care Agreements. The pilot program removes location-based requirements for accessing care. After four years, the bill permanently phases out the location requirements for accessing care under the VCCP and Veterans Care Agreements."}
            ],
        },
        "subjects": {"legislativeSubjects": [
            {"name": "Veterans' health care"},
            {"name": "Veterans Community Care Program"},
            {"name": "Department of Veterans Affairs"},
        ]},
    },
    "119-hr-1040": {
        "bill": {
            "congress": 119,
            "type": "HR",
            "number": "1040",
            "title": "Senior Citizens Tax Elimination Act",
            "originChamber": "House",
            "latestAction": {
                "actionDate": "2025-02-06",
                "text": "Referred to the House Committee on Ways and Means."
            },
            "policyArea": {"name": "Taxation"},
            "sponsors": [
                {"bioguideId": "M001184", "fullName": "Rep. Massie, Thomas [R-KY-4]"}
            ],
            "summaries": [
                {"text": "This bill amends the Internal Revenue Code to eliminate federal income tax on Social Security benefits. Under current law, up to 85% of Social Security benefits may be included in taxable income depending on a recipient's total income. This bill repeals those provisions, making all Social Security benefits exempt from federal income tax."}
            ],
        },
        "subjects": {"legislativeSubjects": [
            {"name": "Social Security benefits"},
            {"name": "Income tax exclusion"},
            {"name": "Tax policy"},
        ]},
    },
}

# --- AI Summaries (factual, no adjectives, mechanisms only) ---

MOCK_AI_SUMMARIES = {
    "119-hr-1": {
        "provisions": [
            "Extends provisions of the 2017 Tax Cuts and Jobs Act, including individual income tax rates and the $10,000 state and local tax (SALT) deduction cap, through 2033",
            "Increases SNAP work requirements: adults up to age 65 (currently 55) must meet work requirements; parents must meet requirements if their child is age 14 or older (currently 18)",
            "Requires states to verify Medicaid eligibility every 6 months for certain populations and adds work reporting requirements; estimated to reduce Medicaid enrollment by 7.6 million people over 10 years",
            "Allocates $46.5 billion for border security including physical barriers, technology, and 10,000 new Border Patrol and ICE agents",
            "Increases the statutory debt limit by $4 trillion, from $36.1 trillion to $40.1 trillion",
            "Creates a new tax deduction for tip income up to $25,000 per year for workers in tipped occupations",
            "Estimated to add $3.8 trillion to the federal deficit over 10 years according to the Congressional Budget Office",
            "Passed the House 215-214 and the Senate 51-50 (Vice President cast tiebreaking vote)",
        ],
        "impact_categories": ["Taxes", "Healthcare", "Immigration", "Wages & Income", "Government Operations"],
    },
    "119-hr-4494": {
        "provisions": [
            "Creates a federal tax deduction for National Flood Insurance Program (NFIP) premiums paid by homeowners",
            "Applies to homeowners with adjusted gross income below specified thresholds",
            "The deduction is above-the-line, meaning taxpayers can claim it without itemizing",
            "Sponsored by Rep. Byron Donalds of Florida's 19th Congressional District",
        ],
        "impact_categories": ["Taxes", "Housing"],
    },
    "119-hr-152": {
        "provisions": [
            "Requires FEMA to develop a plan to reduce duplicative information collection from disaster assistance applicants",
            "Establishes a working group to identify overlapping preliminary damage assessment processes across federal agencies",
            "Directs FEMA to evaluate using drones and other emerging technologies to speed up damage assessments",
            "Requires a public report to Congress with findings and recommendations",
            "Passed the House 405-5",
        ],
        "impact_categories": ["Government Operations", "Infrastructure"],
    },
    "119-s-770": {
        "provisions": [
            "Increases Social Security benefits by changing the calculation of the primary insurance amount",
            "Revises cost-of-living adjustments to reflect spending patterns of individuals over age 62",
            "Establishes a new minimum benefit for workers who earned low wages over a career of at least 30 years",
            "Extends Social Security payroll taxes to income above $250,000 (current cap is $176,100 in 2025)",
            "Combines the Old-Age and Survivors Insurance Trust Fund and Disability Insurance Trust Fund into one fund",
            "Allows full-time students who are children of deceased or disabled workers to collect benefits until age 22",
        ],
        "impact_categories": ["Social Security & Medicare", "Taxes", "Wages & Income"],
    },
    "119-hr-318": {
        "provisions": [
            "Requires DHS to suspend entry of non-U.S. nationals without valid entry documents when DHS cannot detain or return them",
            "Allows states to sue DHS to enforce the entry suspension requirement",
            "Authorizes DHS to suspend entry at the border to achieve operational control",
            "Individuals found to have a credible fear of persecution are currently subject to detention while their asylum claim is considered; this bill adds suspension of entry when detention capacity is unavailable",
        ],
        "impact_categories": ["Immigration", "Criminal Justice", "Government Operations"],
    },
    "119-s-219": {
        "provisions": [
            "Creates a three-year pilot program allowing enrolled veterans to choose any provider in the VA covered care system",
            "Covered care system includes VA medical facilities, Veterans Community Care Program providers, and Veterans Care Agreement providers",
            "Removes location-based requirements that currently limit where veterans can receive care",
            "After four years, permanently eliminates location requirements for accessing care under VCCP and Veterans Care Agreements",
            "Allows veterans to receive care at any VA medical facility regardless of which Veterans Integrated Service Network they reside in",
        ],
        "impact_categories": ["Military & Veterans", "Healthcare"],
    },
    "119-hr-1040": {
        "provisions": [
            "Eliminates federal income tax on all Social Security benefits",
            "Under current law, up to 85% of Social Security benefits may be included in taxable income depending on total income",
            "Repeals Internal Revenue Code provisions that determine the taxable portion of Social Security benefits",
            "Applies to all recipients of Social Security benefits regardless of income level",
        ],
        "impact_categories": ["Taxes", "Social Security & Medicare"],
    },
    "119-hr-5484": {
        "provisions": [
            "Reauthorizes the National Flood Insurance Program (NFIP), which provides flood insurance to property owners, renters, and businesses in participating communities",
            "Addresses affordability of flood insurance premiums for policyholders",
            "Updates flood mapping accuracy requirements",
            "Provides funding for flood mitigation projects",
        ],
        "impact_categories": ["Housing", "Environment"],
    },
}

# --- Senate Vote: H.R.1 (Vote #372, July 1, 2025 — 50-50 + VP tiebreak) ---

MOCK_SENATE_VOTES = {
    "119-1-372": {
        "congress": 119,
        "session": 1,
        "vote_number": 372,
        "question": "On Passage of the Bill (H.R. 1, as Amended)",
        "result": "Bill Passed",
        "vote_date": "2025-07-01",
        "counts": {"yeas": 50, "nays": 50, "present": 0, "absent": 0},
        "note": "Vice President voted Yea to break the tie.",
        "members": [
            {"first_name": "Angela", "last_name": "Alsobrooks", "party": "D", "state": "MD", "vote": "Nay"},
            {"first_name": "Tammy", "last_name": "Baldwin", "party": "D", "state": "WI", "vote": "Nay"},
            {"first_name": "Jim", "last_name": "Banks", "party": "R", "state": "IN", "vote": "Yea"},
            {"first_name": "John", "last_name": "Barrasso", "party": "R", "state": "WY", "vote": "Yea"},
            {"first_name": "Michael", "last_name": "Bennet", "party": "D", "state": "CO", "vote": "Nay"},
            {"first_name": "Marsha", "last_name": "Blackburn", "party": "R", "state": "TN", "vote": "Yea"},
            {"first_name": "Richard", "last_name": "Blumenthal", "party": "D", "state": "CT", "vote": "Nay"},
            {"first_name": "Lisa", "last_name": "Blunt Rochester", "party": "D", "state": "DE", "vote": "Nay"},
            {"first_name": "Cory", "last_name": "Booker", "party": "D", "state": "NJ", "vote": "Nay"},
            {"first_name": "John", "last_name": "Boozman", "party": "R", "state": "AR", "vote": "Yea"},
            {"first_name": "Katie", "last_name": "Britt", "party": "R", "state": "AL", "vote": "Yea"},
            {"first_name": "Ted", "last_name": "Budd", "party": "R", "state": "NC", "vote": "Yea"},
            {"first_name": "Maria", "last_name": "Cantwell", "party": "D", "state": "WA", "vote": "Nay"},
            {"first_name": "Shelley Moore", "last_name": "Capito", "party": "R", "state": "WV", "vote": "Yea"},
            {"first_name": "Bill", "last_name": "Cassidy", "party": "R", "state": "LA", "vote": "Yea"},
            {"first_name": "Susan", "last_name": "Collins", "party": "R", "state": "ME", "vote": "Nay"},
            {"first_name": "Chris", "last_name": "Coons", "party": "D", "state": "DE", "vote": "Nay"},
            {"first_name": "John", "last_name": "Cornyn", "party": "R", "state": "TX", "vote": "Yea"},
            {"first_name": "Catherine", "last_name": "Cortez Masto", "party": "D", "state": "NV", "vote": "Nay"},
            {"first_name": "Tom", "last_name": "Cotton", "party": "R", "state": "AR", "vote": "Yea"},
            {"first_name": "Kevin", "last_name": "Cramer", "party": "R", "state": "ND", "vote": "Yea"},
            {"first_name": "Mike", "last_name": "Crapo", "party": "R", "state": "ID", "vote": "Yea"},
            {"first_name": "Ted", "last_name": "Cruz", "party": "R", "state": "TX", "vote": "Yea"},
            {"first_name": "John", "last_name": "Curtis", "party": "R", "state": "UT", "vote": "Yea"},
            {"first_name": "Steve", "last_name": "Daines", "party": "R", "state": "MT", "vote": "Yea"},
            {"first_name": "Tammy", "last_name": "Duckworth", "party": "D", "state": "IL", "vote": "Nay"},
            {"first_name": "Dick", "last_name": "Durbin", "party": "D", "state": "IL", "vote": "Nay"},
            {"first_name": "Joni", "last_name": "Ernst", "party": "R", "state": "IA", "vote": "Yea"},
            {"first_name": "John", "last_name": "Fetterman", "party": "D", "state": "PA", "vote": "Nay"},
            {"first_name": "Deb", "last_name": "Fischer", "party": "R", "state": "NE", "vote": "Yea"},
            {"first_name": "Ruben", "last_name": "Gallego", "party": "D", "state": "AZ", "vote": "Nay"},
            {"first_name": "Kirsten", "last_name": "Gillibrand", "party": "D", "state": "NY", "vote": "Nay"},
            {"first_name": "Lindsey", "last_name": "Graham", "party": "R", "state": "SC", "vote": "Yea"},
            {"first_name": "Chuck", "last_name": "Grassley", "party": "R", "state": "IA", "vote": "Yea"},
            {"first_name": "Bill", "last_name": "Hagerty", "party": "R", "state": "TN", "vote": "Yea"},
            {"first_name": "Maggie", "last_name": "Hassan", "party": "D", "state": "NH", "vote": "Nay"},
            {"first_name": "Josh", "last_name": "Hawley", "party": "R", "state": "MO", "vote": "Yea"},
            {"first_name": "Martin", "last_name": "Heinrich", "party": "D", "state": "NM", "vote": "Nay"},
            {"first_name": "John", "last_name": "Hickenlooper", "party": "D", "state": "CO", "vote": "Nay"},
            {"first_name": "Mazie", "last_name": "Hirono", "party": "D", "state": "HI", "vote": "Nay"},
            {"first_name": "John", "last_name": "Hoeven", "party": "R", "state": "ND", "vote": "Yea"},
            {"first_name": "Jon", "last_name": "Husted", "party": "R", "state": "OH", "vote": "Yea"},
            {"first_name": "Cindy", "last_name": "Hyde-Smith", "party": "R", "state": "MS", "vote": "Yea"},
            {"first_name": "Ron", "last_name": "Johnson", "party": "R", "state": "WI", "vote": "Yea"},
            {"first_name": "Jim", "last_name": "Justice", "party": "R", "state": "WV", "vote": "Yea"},
            {"first_name": "Tim", "last_name": "Kaine", "party": "D", "state": "VA", "vote": "Nay"},
            {"first_name": "Mark", "last_name": "Kelly", "party": "D", "state": "AZ", "vote": "Nay"},
            {"first_name": "John", "last_name": "Kennedy", "party": "R", "state": "LA", "vote": "Yea"},
            {"first_name": "Andy", "last_name": "Kim", "party": "D", "state": "NJ", "vote": "Nay"},
            {"first_name": "Angus", "last_name": "King", "party": "I", "state": "ME", "vote": "Nay"},
            {"first_name": "Amy", "last_name": "Klobuchar", "party": "D", "state": "MN", "vote": "Nay"},
            {"first_name": "James", "last_name": "Lankford", "party": "R", "state": "OK", "vote": "Yea"},
            {"first_name": "Mike", "last_name": "Lee", "party": "R", "state": "UT", "vote": "Yea"},
            {"first_name": "Ben Ray", "last_name": "Lujan", "party": "D", "state": "NM", "vote": "Nay"},
            {"first_name": "Cynthia", "last_name": "Lummis", "party": "R", "state": "WY", "vote": "Yea"},
            {"first_name": "Ed", "last_name": "Markey", "party": "D", "state": "MA", "vote": "Nay"},
            {"first_name": "Roger", "last_name": "Marshall", "party": "R", "state": "KS", "vote": "Yea"},
            {"first_name": "Mitch", "last_name": "McConnell", "party": "R", "state": "KY", "vote": "Yea"},
            {"first_name": "Dave", "last_name": "McCormick", "party": "R", "state": "PA", "vote": "Yea"},
            {"first_name": "Jeff", "last_name": "Merkley", "party": "D", "state": "OR", "vote": "Nay"},
            {"first_name": "Ashley", "last_name": "Moody", "party": "R", "state": "FL", "vote": "Yea"},
            {"first_name": "Jerry", "last_name": "Moran", "party": "R", "state": "KS", "vote": "Yea"},
            {"first_name": "Bernie", "last_name": "Moreno", "party": "R", "state": "OH", "vote": "Yea"},
            {"first_name": "Markwayne", "last_name": "Mullin", "party": "R", "state": "OK", "vote": "Yea"},
            {"first_name": "Lisa", "last_name": "Murkowski", "party": "R", "state": "AK", "vote": "Yea"},
            {"first_name": "Chris", "last_name": "Murphy", "party": "D", "state": "CT", "vote": "Nay"},
            {"first_name": "Patty", "last_name": "Murray", "party": "D", "state": "WA", "vote": "Nay"},
            {"first_name": "Jon", "last_name": "Ossoff", "party": "D", "state": "GA", "vote": "Nay"},
            {"first_name": "Alex", "last_name": "Padilla", "party": "D", "state": "CA", "vote": "Nay"},
            {"first_name": "Rand", "last_name": "Paul", "party": "R", "state": "KY", "vote": "Nay"},
            {"first_name": "Gary", "last_name": "Peters", "party": "D", "state": "MI", "vote": "Nay"},
            {"first_name": "Jack", "last_name": "Reed", "party": "D", "state": "RI", "vote": "Nay"},
            {"first_name": "Pete", "last_name": "Ricketts", "party": "R", "state": "NE", "vote": "Yea"},
            {"first_name": "Jim", "last_name": "Risch", "party": "R", "state": "ID", "vote": "Yea"},
            {"first_name": "Jacky", "last_name": "Rosen", "party": "D", "state": "NV", "vote": "Nay"},
            {"first_name": "Mike", "last_name": "Rounds", "party": "R", "state": "SD", "vote": "Yea"},
            {"first_name": "Bernie", "last_name": "Sanders", "party": "I", "state": "VT", "vote": "Nay"},
            {"first_name": "Brian", "last_name": "Schatz", "party": "D", "state": "HI", "vote": "Nay"},
            {"first_name": "Adam", "last_name": "Schiff", "party": "D", "state": "CA", "vote": "Nay"},
            {"first_name": "Eric", "last_name": "Schmitt", "party": "R", "state": "MO", "vote": "Yea"},
            {"first_name": "Chuck", "last_name": "Schumer", "party": "D", "state": "NY", "vote": "Nay"},
            {"first_name": "Rick", "last_name": "Scott", "party": "R", "state": "FL", "vote": "Yea"},
            {"first_name": "Tim", "last_name": "Scott", "party": "R", "state": "SC", "vote": "Yea"},
            {"first_name": "Jeanne", "last_name": "Shaheen", "party": "D", "state": "NH", "vote": "Nay"},
            {"first_name": "Tim", "last_name": "Sheehy", "party": "R", "state": "MT", "vote": "Yea"},
            {"first_name": "Elissa", "last_name": "Slotkin", "party": "D", "state": "MI", "vote": "Nay"},
            {"first_name": "Tina", "last_name": "Smith", "party": "D", "state": "MN", "vote": "Nay"},
            {"first_name": "Dan", "last_name": "Sullivan", "party": "R", "state": "AK", "vote": "Yea"},
            {"first_name": "John", "last_name": "Thune", "party": "R", "state": "SD", "vote": "Yea"},
            {"first_name": "Thom", "last_name": "Tillis", "party": "R", "state": "NC", "vote": "Nay"},
            {"first_name": "Tommy", "last_name": "Tuberville", "party": "R", "state": "AL", "vote": "Yea"},
            {"first_name": "Chris", "last_name": "Van Hollen", "party": "D", "state": "MD", "vote": "Nay"},
            {"first_name": "Mark", "last_name": "Warner", "party": "D", "state": "VA", "vote": "Nay"},
            {"first_name": "Raphael", "last_name": "Warnock", "party": "D", "state": "GA", "vote": "Nay"},
            {"first_name": "Elizabeth", "last_name": "Warren", "party": "D", "state": "MA", "vote": "Nay"},
            {"first_name": "Peter", "last_name": "Welch", "party": "D", "state": "VT", "vote": "Nay"},
            {"first_name": "Sheldon", "last_name": "Whitehouse", "party": "D", "state": "RI", "vote": "Nay"},
            {"first_name": "Roger", "last_name": "Wicker", "party": "R", "state": "MS", "vote": "Yea"},
            {"first_name": "Ron", "last_name": "Wyden", "party": "D", "state": "OR", "vote": "Nay"},
            {"first_name": "Todd", "last_name": "Young", "party": "R", "state": "IN", "vote": "Yea"},
        ],
    },
}

# --- Bill → Vote mapping ---

MOCK_BILL_VOTES = {
    "119-hr-1": {"senate": [{"congress": 119, "session": 1, "vote_number": 372}]},
}

MOCK_STATE_MEMBERS = {
    "FL": MOCK_MEMBERS_FL,
    "NY": MOCK_MEMBERS_NY,
    "TX": MOCK_MEMBERS_TX,
}


def get_mock_members(state_code: str) -> dict | None:
    return MOCK_STATE_MEMBERS.get(state_code.upper())


def get_mock_member_detail(bioguide_id: str) -> dict | None:
    if bioguide_id in MOCK_MEMBER_DETAILS:
        return MOCK_MEMBER_DETAILS[bioguide_id]
    # Search all member lists for a fallback
    for members_data in MOCK_STATE_MEMBERS.values():
        for m in members_data["members"]:
            if m["bioguideId"] == bioguide_id:
                return {"member": m}
    return None


def get_mock_bills() -> dict:
    return MOCK_BILLS


def get_mock_bill_detail(congress: int, bill_type: str, bill_number: int) -> dict | None:
    key = f"{congress}-{bill_type.lower()}-{bill_number}"
    return MOCK_BILL_DETAILS.get(key)


def get_mock_ai_summary(congress: int, bill_type: str, bill_number: int) -> dict | None:
    key = f"{congress}-{bill_type.lower()}-{bill_number}"
    return MOCK_AI_SUMMARIES.get(key)


def get_mock_senate_vote(congress: int, session: int, vote_number: int) -> dict | None:
    key = f"{congress}-{session}-{vote_number}"
    return MOCK_SENATE_VOTES.get(key)


def get_mock_bill_votes(congress: int, bill_type: str, bill_number: int) -> dict | None:
    key = f"{congress}-{bill_type.lower()}-{bill_number}"
    return MOCK_BILL_VOTES.get(key)
