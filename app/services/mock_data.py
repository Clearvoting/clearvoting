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
                {"text": "This bill allows middle-income homeowners to deduct the cost of flood insurance premiums from their federal taxes. It amends the Internal Revenue Code to create a new above-the-line deduction for National Flood Insurance Program (NFIP) premiums paid by individuals with adjusted gross income below specified thresholds. The NFIP currently carries $22.5 billion in debt to the U.S. Treasury and insures approximately 4.7 million properties nationwide."}
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
                {"text": "This bill reauthorizes and reforms the National Flood Insurance Program (NFIP). The NFIP provides flood insurance to property owners, renters, and businesses in approximately 22,000 participating communities. The program's current authorization expires September 30, 2025 and has been extended 33 times through short-term reauthorizations since FY2017. This bill extends the program and addresses affordability, mapping accuracy, and mitigation funding. The NFIP currently carries $22.5 billion in debt to the U.S. Treasury."}
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
    "119-hr-6934": {
        "bill": {
            "congress": 119,
            "type": "HR",
            "number": "6934",
            "title": "National Flood Insurance Program Affordability Act",
            "originChamber": "House",
            "latestAction": {
                "actionDate": "2025-12-30",
                "text": "Referred to the House Committee on Financial Services."
            },
            "policyArea": {"name": "Finance and Financial Sector"},
            "sponsors": [
                {"bioguideId": "C001111", "fullName": "Rep. Castor, Kathy [D-FL-14]"}
            ],
            "summaries": [
                {"text": "This bill addresses the affordability of flood insurance premiums under the National Flood Insurance Program (NFIP). It caps annual premium increases for existing policyholders and directs FEMA to create a means-tested assistance program for low-income policyholders. The bill responds to premium increases under FEMA's Risk Rating 2.0 pricing methodology, which began in October 2021 and shifted to risk-based pricing. Florida has approximately 1.7 million NFIP policies, the most of any state."}
            ],
        },
        "subjects": {"legislativeSubjects": [
            {"name": "Flood insurance"},
            {"name": "National Flood Insurance Program"},
            {"name": "Insurance rates"},
        ]},
    },
    "119-hr-6017": {
        "bill": {
            "congress": 119,
            "type": "HR",
            "number": "6017",
            "title": "Veterans Bill of Rights Act",
            "originChamber": "House",
            "latestAction": {
                "actionDate": "2025-11-10",
                "text": "Referred to the House Committee on Veterans' Affairs."
            },
            "policyArea": {"name": "Armed Forces and National Security"},
            "sponsors": [
                {"bioguideId": "W000823", "fullName": "Rep. Waltz, Michael [R-FL-6]"}
            ],
            "summaries": [
                {"text": "This bill establishes a formal bill of rights for veterans receiving care through the Department of Veterans Affairs. It requires the VA to notify veterans of their rights including access to timely care, choice of provider, and appeal processes. The VA must publish wait-time data for each of its health care facilities and report annually to Congress on compliance with veterans' rights standards."}
            ],
        },
        "subjects": {"legislativeSubjects": [
            {"name": "Veterans' medical care"},
            {"name": "Department of Veterans Affairs"},
            {"name": "Government information and archives"},
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
            "The NFIP currently carries $22.5 billion in debt to the U.S. Treasury as of February 2025",
            "Florida has the most NFIP policies of any state; the state added nearly 100,000 new NFIP policies since Risk Rating 2.0 began in 2021",
            "Sponsored by Rep. Byron Donalds of Florida's 19th Congressional District",
        ],
        "impact_categories": ["Taxes", "Housing", "Insurance"],
    },
    "119-hr-152": {
        "provisions": [
            "Requires FEMA to develop a plan to reduce duplicative information collection from disaster assistance applicants",
            "Establishes a working group to identify overlapping preliminary damage assessment processes across federal agencies",
            "Directs FEMA to evaluate using drones and other emerging technologies to speed up damage assessments",
            "Requires a public report to Congress with findings and recommendations within 1 year of enactment",
            "Florida sustained over $38.85 billion in damages from hurricanes and flooding in 2023-2024",
            "Passed the House 405-5 with bipartisan support",
        ],
        "impact_categories": ["Government Operations", "Infrastructure", "Emergency Management"],
    },
    "119-s-770": {
        "provisions": [
            "Increases Social Security benefits by changing the calculation of the primary insurance amount",
            "Revises cost-of-living adjustments to use the CPI-E (Consumer Price Index for the Elderly) instead of CPI-W, which typically shows higher inflation for seniors",
            "Establishes a new minimum benefit for workers who earned low wages over a career of at least 30 years",
            "Extends the 12.4% Social Security payroll tax to income above $250,000; income between $176,100 and $250,000 would not be taxed (a 'donut hole')",
            "Combines the Old-Age and Survivors Insurance Trust Fund and Disability Insurance Trust Fund into one fund",
            "About 72.5 million Americans currently receive Social Security benefits; the combined trust funds are projected to be depleted by 2033 without legislative changes",
            "Allows full-time students who are children of deceased or disabled workers to collect benefits until age 22",
        ],
        "impact_categories": ["Social Security & Medicare", "Taxes", "Wages & Income"],
    },
    "119-hr-318": {
        "provisions": [
            "Requires DHS to suspend entry of non-U.S. nationals without valid entry documents when DHS cannot detain or return them",
            "Allows any of the 50 states to sue DHS in federal court to enforce the entry suspension requirement",
            "Authorizes DHS to suspend entry at any of the 328 official ports of entry to achieve operational control of the border",
            "Applies to the approximately 1,954-mile U.S.-Mexico land border",
            "Individuals found to have a credible fear of persecution are currently subject to detention while their asylum claim is considered; this bill adds suspension of entry when detention capacity is unavailable",
        ],
        "impact_categories": ["Immigration", "Criminal Justice", "Government Operations"],
    },
    "119-s-219": {
        "provisions": [
            "Creates a 3-year pilot program allowing enrolled veterans to choose any provider in the VA covered care system",
            "Covered care system includes VA medical facilities, Veterans Community Care Program providers, and Veterans Care Agreement providers",
            "Removes the current requirement that veterans must live more than 30 minutes from a VA facility or wait more than 20 days for an appointment to access community care",
            "After 4 years, permanently eliminates location and wait-time requirements for accessing care under VCCP and Veterans Care Agreements",
            "Allows veterans to receive care at any VA medical facility regardless of which of the 18 Veterans Integrated Service Networks they reside in",
            "Florida has the 3rd-largest veteran population in the U.S. with approximately 1.4 million veterans",
        ],
        "impact_categories": ["Military & Veterans", "Healthcare"],
    },
    "119-hr-1040": {
        "provisions": [
            "Eliminates federal income tax on all Social Security benefits",
            "Under current law, single filers with combined income above $25,000 pay tax on up to 50% of benefits; above $34,000, up to 85% is taxable",
            "For joint filers, the thresholds are $32,000 (50% taxable) and $44,000 (85% taxable)",
            "These thresholds have not been adjusted for inflation since they were set in 1984 and 1993, causing more recipients to be taxed each year",
            "Repeals Internal Revenue Code Sections 86(a) and 86(b) that determine the taxable portion of Social Security benefits",
            "Applies to all 72.5 million recipients of Social Security benefits regardless of income level",
        ],
        "impact_categories": ["Taxes", "Social Security & Medicare"],
    },
    "119-hr-6934": {
        "provisions": [
            "Addresses affordability of National Flood Insurance Program (NFIP) premiums that increased under FEMA's Risk Rating 2.0 methodology",
            "Caps annual premium increases for existing policyholders to limit financial impact of new risk-based pricing",
            "Florida policyholders saw average premium increases of 11-18% per year under Risk Rating 2.0",
            "The NFIP insures approximately 4.7 million properties nationwide; Florida accounts for roughly 1.7 million of those policies",
            "Directs FEMA to provide a means-tested assistance program for low-income policyholders",
        ],
        "impact_categories": ["Housing", "Insurance", "Government Operations"],
    },
    "119-hr-6017": {
        "provisions": [
            "Establishes a formal bill of rights for veterans receiving care through the Department of Veterans Affairs",
            "Requires the VA to notify veterans of their rights including access to timely care, choice of provider, and appeal processes",
            "Mandates the VA publish wait-time data for each of its 1,321 health care facilities nationwide",
            "Requires annual reporting to Congress on compliance with veterans' rights standards",
            "Florida has approximately 1.4 million veterans, the 3rd-highest veteran population of any state",
        ],
        "impact_categories": ["Military & Veterans", "Healthcare", "Government Operations"],
    },
    "119-hr-5484": {
        "provisions": [
            "Reauthorizes the National Flood Insurance Program (NFIP), which currently has $22.5 billion in debt to the U.S. Treasury",
            "The NFIP has been reauthorized 33 times through short-term extensions since FY2017; current authorization expires September 30, 2025",
            "Addresses affordability of flood insurance premiums under FEMA's Risk Rating 2.0 pricing methodology, which began in October 2021",
            "Updates flood mapping accuracy requirements for the roughly 22,000 communities participating in the NFIP",
            "On February 10, 2025, the NFIP borrowed an additional $2 billion from Treasury to pay claims, leaving $7.9 billion in remaining borrowing authority",
            "Provides funding for flood mitigation projects to reduce future claims",
        ],
        "impact_categories": ["Housing", "Environment", "Insurance", "Government Operations"],
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

# --- Member Voting Records (119th Congress) ---

MOCK_MEMBER_VOTES = {
    "S001217": {  # Rick Scott
        "member_id": "S001217",
        "congress": 119,
        "stats": {
            "total_votes": 187,
            "yea_count": 112,
            "nay_count": 67,
            "not_voting_count": 8,
            "participation_rate": 95.7,
        },
        "scorecard": [
            {
                "issue": "Cost of Living",
                "subtitle": "Healthcare, housing, and everyday costs",
                "votes": [
                    {"bill_number": "H.R. 318", "vote": "Yea", "summary": "Stops taxing tips for servers, bartenders, and other tipped workers"},
                    {"bill_number": "H.R. 4494", "vote": "Yea", "summary": "Doubles the maximum flood insurance coverage for homeowners"},
                    {"bill_number": "H.R. 1", "vote": "Yea", "summary": "Makes cuts to Medicaid and food assistance programs"},
                    {"bill_number": "H.R. 152", "vote": "Yea", "summary": "Sends $100 billion in hurricane relief to affected communities"},
                ],
            },
            {
                "issue": "Social Security",
                "subtitle": "Protecting retirement benefits",
                "votes": [
                    {"bill_number": "S. 770", "vote": "Yea", "summary": "Restores Social Security checks that were being cut for retired teachers and firefighters"},
                    {"bill_number": "S. 2012", "vote": "Yea", "summary": "Requires the government to post daily updates on the national debt — which affects Social Security's future"},
                ],
            },
            {
                "issue": "National Debt",
                "subtitle": "Government spending and the deficit",
                "votes": [
                    {"bill_number": "H.R. 1", "vote": "Yea", "summary": "Tax cuts and spending increases", "deficit": "+$3.4 trillion"},
                    {"bill_number": "S. 770", "vote": "Yea", "summary": "Social Security expansion", "deficit": "+$196 billion"},
                    {"bill_number": "H.R. 152", "vote": "Yea", "summary": "Hurricane relief spending", "deficit": "+$100 billion"},
                    {"bill_number": "H.R. 4", "vote": "Yea", "summary": "Cut foreign aid and PBS funding", "deficit": "-$9.1 billion"},
                    {"bill_number": "S.Amdt. 4236", "vote": "Yea", "summary": "Tried to remove special spending projects from the budget (failed)", "deficit": "$0"},
                    {"bill_number": "S. 2012", "vote": "Yea", "summary": "Requires daily public tracking of the national debt"},
                ],
            },
        ],
        "votes": [
            {
                "bill_number": "H.R. 1",
                "bill_title": "One Big Beautiful Bill Act",
                "one_liner": "Keeps tax cuts in place, adds money for border security and the military, and makes cuts to Medicaid and other government aid programs — all in one big bill.",
                "vote": "Yea",
                "date": "2025-07-01",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Taxes",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 1,
                "cbo_deficit_impact": "+$3.4 trillion over 10 years",
                "cbo_deficit_billions": 3400,
            },
            {
                "bill_number": "H.R. 4",
                "bill_title": "Rescissions Package",
                "one_liner": "Cuts $8 billion from foreign aid programs and $1.1 billion from NPR and PBS funding.",
                "vote": "Yea",
                "date": "2025-07-17",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Government Operations",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 4,
                "cbo_deficit_impact": "-$9.1 billion",
                "cbo_deficit_billions": -9.1,
            },
            {
                "bill_number": "H.R. 6938",
                "bill_title": "Commerce, Justice, Science Appropriations Act, 2026",
                "one_liner": "Pays for government programs like law enforcement, science research, energy, and environmental protection for the year.",
                "vote": "Nay",
                "date": "2026-01-15",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Government Operations",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 6938,
            },
            {
                "bill_number": "S.Amdt. 4236",
                "bill_title": "Lee Amendment to Strike Earmarks",
                "one_liner": "Tried to remove all special hometown spending projects that lawmakers added to the government funding bill.",
                "vote": "Yea",
                "date": "2026-01-30",
                "result": "Failed",
                "chamber": "Senate",
                "policy_area": "Government Operations",
                "congress": 119,
                "bill_type": "SAMDT",
                "bill_number_raw": 4236,
            },
            {
                "bill_number": "H.R. 4494",
                "bill_title": "National Flood Insurance Program Extension Act of 2025",
                "one_liner": "Keeps the government flood insurance program running through 2029 and doubles the maximum home coverage from $250,000 to $500,000.",
                "vote": "Yea",
                "date": "2025-06-12",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Housing",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 4494,
            },
            {
                "bill_number": "S. 770",
                "bill_title": "Social Security Fairness Act",
                "one_liner": "Stops the rule that cut Social Security checks for people who also get a government pension, like retired teachers and firefighters.",
                "vote": "Yea",
                "date": "2025-03-18",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Social Security & Medicare",
                "congress": 119,
                "bill_type": "S",
                "bill_number_raw": 770,
                "cbo_deficit_impact": "+$196 billion over 10 years",
                "cbo_deficit_billions": 196,
            },
            {
                "bill_number": "S. 219",
                "bill_title": "Veterans' COLA Act of 2025",
                "one_liner": "Gives veterans a raise in their disability and survivor benefit payments to keep up with the rising cost of living.",
                "vote": "Yea",
                "date": "2025-05-08",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Military & Veterans",
                "congress": 119,
                "bill_type": "S",
                "bill_number_raw": 219,
            },
            {
                "bill_number": "H.R. 152",
                "bill_title": "Disaster Relief Supplemental Appropriations Act",
                "one_liner": "Sends $100 billion in emergency aid to communities hit by Hurricanes Helene and Milton for disaster relief, small business loans, and rebuilding roads and bridges.",
                "vote": "Yea",
                "date": "2025-03-28",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Infrastructure",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 152,
                "cbo_deficit_impact": "+$100 billion",
                "cbo_deficit_billions": 100,
            },
            {
                "bill_number": "H.R. 1040",
                "bill_title": "REAL ID Modernization Act",
                "one_liner": "Pushes back the deadline for REAL ID to May 2027 and lets states offer digital driver's licenses on your phone.",
                "vote": "Yea",
                "date": "2025-04-22",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Government Operations",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 1040,
            },
            {
                "bill_number": "S. 1182",
                "bill_title": "HALT Fentanyl Act",
                "one_liner": "Makes fentanyl and similar drugs fully illegal and increases jail time for people caught selling them.",
                "vote": "Yea",
                "date": "2025-05-22",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Criminal Justice",
                "congress": 119,
                "bill_type": "S",
                "bill_number_raw": 1182,
            },
            {
                "bill_number": "S. 2341",
                "bill_title": "Laken Riley Act",
                "one_liner": "Requires immigration officers to hold undocumented immigrants charged with theft or violent crimes, and lets states sue the federal government over immigration enforcement.",
                "vote": "Yea",
                "date": "2025-01-29",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Immigration",
                "congress": 119,
                "bill_type": "S",
                "bill_number_raw": 2341,
            },
            {
                "bill_number": "S. 3100",
                "bill_title": "NDAA FY2026",
                "one_liner": "Approves $923 billion for the military, gives troops a 3.8% pay raise, and bans buying military computers and solar panels made in China.",
                "vote": "Yea",
                "date": "2025-12-10",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Defense",
                "congress": 119,
                "bill_type": "S",
                "bill_number_raw": 3100,
            },
            {
                "bill_number": "S. 890",
                "bill_title": "TikTok Ban Extension Act",
                "one_liner": "Gives TikTok's owner more time — until January 2026 — to sell the app's US business or face a ban.",
                "vote": "Yea",
                "date": "2025-04-05",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Technology",
                "congress": 119,
                "bill_type": "S",
                "bill_number_raw": 890,
            },
            {
                "bill_number": "S. 1455",
                "bill_title": "No Taxpayer Funding for Abortion Act",
                "one_liner": "Bans the use of taxpayer money for abortion, except in cases of rape, incest, or when the mother's life is in danger.",
                "vote": "Yea",
                "date": "2025-06-04",
                "result": "Failed",
                "chamber": "Senate",
                "policy_area": "Healthcare",
                "congress": 119,
                "bill_type": "S",
                "bill_number_raw": 1455,
            },
            {
                "bill_number": "S. 2012",
                "bill_title": "Federal Debt Transparency Act",
                "one_liner": "Makes the government post a daily online update showing how much the country owes, how much we pay in interest, and where the debt is headed over the next 10 years.",
                "vote": "Yea",
                "date": "2025-08-14",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Economy",
                "congress": 119,
                "bill_type": "S",
                "bill_number_raw": 2012,
            },
            {
                "bill_number": "H.R. 318",
                "bill_title": "No Tax on Tips Act",
                "one_liner": "Stops the government from taxing tips for workers like servers and bartenders, up to $25,000 a year.",
                "vote": "Yea",
                "date": "2025-05-15",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Taxes",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 318,
            },
        ],
        "policy_areas": ["Taxes", "Government Operations", "Defense", "Immigration", "Healthcare", "Housing", "Social Security & Medicare", "Military & Veterans", "Infrastructure", "Criminal Justice", "Technology", "Economy"],
    },
    "M001244": {  # Ashley Moody
        "member_id": "M001244",
        "congress": 119,
        "stats": {
            "total_votes": 187,
            "yea_count": 118,
            "nay_count": 63,
            "not_voting_count": 6,
            "participation_rate": 96.8,
        },
        "scorecard": [
            {
                "issue": "Cost of Living",
                "subtitle": "Healthcare, housing, and everyday costs",
                "votes": [
                    {"bill_number": "H.R. 318", "vote": "Yea", "summary": "Stops taxing tips for servers, bartenders, and other tipped workers"},
                    {"bill_number": "H.R. 1", "vote": "Yea", "summary": "Makes cuts to Medicaid and food assistance programs"},
                    {"bill_number": "H.R. 152", "vote": "Yea", "summary": "Sends $100 billion in hurricane relief to affected communities"},
                ],
            },
            {
                "issue": "Social Security",
                "subtitle": "Protecting retirement benefits",
                "votes": [
                    {"bill_number": "S. 770", "vote": "Yea", "summary": "Restores Social Security checks that were being cut for retired teachers and firefighters"},
                ],
            },
            {
                "issue": "National Debt",
                "subtitle": "Government spending and the deficit",
                "votes": [
                    {"bill_number": "H.R. 1", "vote": "Yea", "summary": "Tax cuts and spending increases", "deficit": "+$3.4 trillion"},
                    {"bill_number": "S. 770", "vote": "Yea", "summary": "Social Security expansion", "deficit": "+$196 billion"},
                    {"bill_number": "H.R. 152", "vote": "Yea", "summary": "Hurricane relief spending", "deficit": "+$100 billion"},
                    {"bill_number": "H.R. 4", "vote": "Yea", "summary": "Cut foreign aid and PBS funding", "deficit": "-$9.1 billion"},
                ],
            },
        ],
        "votes": [
            {
                "bill_number": "H.R. 1",
                "bill_title": "One Big Beautiful Bill Act",
                "one_liner": "Keeps tax cuts in place, adds money for border security and the military, and makes cuts to Medicaid and other government aid programs — all in one big bill.",
                "vote": "Yea",
                "date": "2025-07-01",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Taxes",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 1,
                "cbo_deficit_impact": "+$3.4 trillion over 10 years",
                "cbo_deficit_billions": 3400,
            },
            {
                "bill_number": "S. 2341",
                "bill_title": "Laken Riley Act",
                "one_liner": "Requires immigration officers to hold undocumented immigrants charged with theft or violent crimes, and lets states sue the federal government over immigration enforcement.",
                "vote": "Yea",
                "date": "2025-01-29",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Immigration",
                "congress": 119,
                "bill_type": "S",
                "bill_number_raw": 2341,
            },
            {
                "bill_number": "S. 770",
                "bill_title": "Social Security Fairness Act",
                "one_liner": "Stops the rule that cut Social Security checks for people who also get a government pension, like retired teachers and firefighters.",
                "vote": "Yea",
                "date": "2025-03-18",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Social Security & Medicare",
                "congress": 119,
                "bill_type": "S",
                "bill_number_raw": 770,
                "cbo_deficit_impact": "+$196 billion over 10 years",
                "cbo_deficit_billions": 196,
            },
            {
                "bill_number": "H.R. 4",
                "bill_title": "Rescissions Package",
                "one_liner": "Cuts $8 billion from foreign aid programs and $1.1 billion from NPR and PBS funding.",
                "vote": "Yea",
                "date": "2025-07-17",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Government Operations",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 4,
                "cbo_deficit_impact": "-$9.1 billion",
                "cbo_deficit_billions": -9.1,
            },
            {
                "bill_number": "H.R. 6938",
                "bill_title": "Commerce, Justice, Science Appropriations Act, 2026",
                "one_liner": "Pays for government programs like law enforcement, science research, energy, and environmental protection for the year.",
                "vote": "Yea",
                "date": "2026-01-15",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Government Operations",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 6938,
            },
            {
                "bill_number": "S. 3100",
                "bill_title": "NDAA FY2026",
                "one_liner": "Approves $923 billion for the military, gives troops a 3.8% pay raise, and bans buying military computers and solar panels made in China.",
                "vote": "Yea",
                "date": "2025-12-10",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Defense",
                "congress": 119,
                "bill_type": "S",
                "bill_number_raw": 3100,
            },
            {
                "bill_number": "H.R. 152",
                "bill_title": "Disaster Relief Supplemental Appropriations Act",
                "one_liner": "Sends $100 billion in emergency aid to communities hit by Hurricanes Helene and Milton for disaster relief, small business loans, and rebuilding roads and bridges.",
                "vote": "Yea",
                "date": "2025-03-28",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Infrastructure",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 152,
                "cbo_deficit_impact": "+$100 billion",
                "cbo_deficit_billions": 100,
            },
            {
                "bill_number": "H.R. 318",
                "bill_title": "No Tax on Tips Act",
                "one_liner": "Stops the government from taxing tips for workers like servers and bartenders, up to $25,000 a year.",
                "vote": "Yea",
                "date": "2025-05-15",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Taxes",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 318,
            },
            {
                "bill_number": "S. 1182",
                "bill_title": "HALT Fentanyl Act",
                "one_liner": "Makes fentanyl and similar drugs fully illegal and increases jail time for people caught selling them.",
                "vote": "Yea",
                "date": "2025-05-22",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Criminal Justice",
                "congress": 119,
                "bill_type": "S",
                "bill_number_raw": 1182,
            },
            {
                "bill_number": "S. 219",
                "bill_title": "Veterans' COLA Act of 2025",
                "one_liner": "Gives veterans a raise in their disability and survivor benefit payments to keep up with the rising cost of living.",
                "vote": "Yea",
                "date": "2025-05-08",
                "result": "Passed",
                "chamber": "Senate",
                "policy_area": "Military & Veterans",
                "congress": 119,
                "bill_type": "S",
                "bill_number_raw": 219,
            },
        ],
        "policy_areas": ["Taxes", "Government Operations", "Defense", "Immigration", "Social Security & Medicare", "Military & Veterans", "Infrastructure", "Criminal Justice"],
    },
    "D000032": {  # Byron Donalds
        "member_id": "D000032",
        "congress": 119,
        "stats": {
            "total_votes": 234,
            "yea_count": 155,
            "nay_count": 71,
            "not_voting_count": 8,
            "participation_rate": 96.6,
        },
        "scorecard": [
            {
                "issue": "Cost of Living",
                "subtitle": "Healthcare, housing, and everyday costs",
                "votes": [
                    {"bill_number": "H.R. 318", "vote": "Yea", "summary": "Stops taxing tips for servers, bartenders, and other tipped workers"},
                    {"bill_number": "H.R. 4494", "vote": "Yea", "summary": "Doubles the maximum flood insurance coverage for homeowners"},
                    {"bill_number": "H.R. 1", "vote": "Yea", "summary": "Makes cuts to Medicaid and food assistance programs"},
                    {"bill_number": "H.R. 152", "vote": "Yea", "summary": "Sends $100 billion in hurricane relief to affected communities"},
                ],
            },
            {
                "issue": "Social Security",
                "subtitle": "Protecting retirement benefits",
                "votes": [],
            },
            {
                "issue": "National Debt",
                "subtitle": "Government spending and the deficit",
                "votes": [
                    {"bill_number": "H.R. 1", "vote": "Yea", "summary": "Tax cuts and spending increases", "deficit": "+$3.4 trillion"},
                    {"bill_number": "H.R. 152", "vote": "Yea", "summary": "Hurricane relief spending", "deficit": "+$100 billion"},
                ],
            },
        ],
        "votes": [
            {
                "bill_number": "H.R. 1",
                "bill_title": "One Big Beautiful Bill Act",
                "one_liner": "Keeps tax cuts in place, adds money for border security and the military, and makes cuts to Medicaid and other government aid programs — all in one big bill.",
                "vote": "Yea",
                "date": "2025-05-22",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Taxes",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 1,
                "cbo_deficit_impact": "+$3.4 trillion over 10 years",
                "cbo_deficit_billions": 3400,
            },
            {
                "bill_number": "H.R. 4494",
                "bill_title": "National Flood Insurance Program Extension Act of 2025",
                "one_liner": "Keeps the government flood insurance program running through 2029 and doubles the maximum home coverage from $250,000 to $500,000.",
                "vote": "Yea",
                "date": "2025-06-12",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Housing",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 4494,
            },
            {
                "bill_number": "H.R. 152",
                "bill_title": "Disaster Relief Supplemental Appropriations Act",
                "one_liner": "Sends $100 billion in emergency aid to communities hit by Hurricanes Helene and Milton for disaster relief, small business loans, and rebuilding roads and bridges.",
                "vote": "Yea",
                "date": "2025-03-14",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Infrastructure",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 152,
                "cbo_deficit_impact": "+$100 billion",
                "cbo_deficit_billions": 100,
            },
            {
                "bill_number": "H.R. 318",
                "bill_title": "No Tax on Tips Act",
                "one_liner": "Stops the government from taxing tips for workers like servers and bartenders, up to $25,000 a year.",
                "vote": "Yea",
                "date": "2025-04-30",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Taxes",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 318,
            },
            {
                "bill_number": "H.R. 5484",
                "bill_title": "Securing the Border for America Act",
                "one_liner": "Hires 22,000 new Border Patrol agents over 5 years, finishes building the border wall, and requires asylum seekers to wait in Mexico.",
                "vote": "Yea",
                "date": "2025-02-04",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Immigration",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 5484,
            },
            {
                "bill_number": "H.R. 1040",
                "bill_title": "REAL ID Modernization Act",
                "one_liner": "Pushes back the deadline for REAL ID to May 2027 and lets states offer digital driver's licenses on your phone.",
                "vote": "Yea",
                "date": "2025-04-10",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Government Operations",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 1040,
            },
            {
                "bill_number": "H.R. 6017",
                "bill_title": "SAVE Act",
                "one_liner": "Requires people to prove they are US citizens to register to vote and makes states remove non-citizens from voter lists within 90 days.",
                "vote": "Yea",
                "date": "2025-02-27",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Government Operations",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 6017,
            },
            {
                "bill_number": "H.R. 6934",
                "bill_title": "Parents Bill of Rights Act",
                "one_liner": "Gives parents the right to see what their kids are being taught, be told about any violence at school, and say yes or no before their kids take personal surveys.",
                "vote": "Yea",
                "date": "2025-03-06",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Education",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 6934,
            },
        ],
        "policy_areas": ["Taxes", "Government Operations", "Immigration", "Housing", "Infrastructure", "Education"],
    },
    "W000823": {  # Michael Waltz
        "member_id": "W000823",
        "congress": 119,
        "stats": {
            "total_votes": 234,
            "yea_count": 148,
            "nay_count": 76,
            "not_voting_count": 10,
            "participation_rate": 95.7,
        },
        "scorecard": [
            {
                "issue": "Cost of Living",
                "subtitle": "Healthcare, housing, and everyday costs",
                "votes": [
                    {"bill_number": "H.R. 318", "vote": "Yea", "summary": "Stops taxing tips for servers, bartenders, and other tipped workers"},
                    {"bill_number": "H.R. 1", "vote": "Yea", "summary": "Makes cuts to Medicaid and food assistance programs"},
                    {"bill_number": "H.R. 152", "vote": "Yea", "summary": "Sends $100 billion in hurricane relief to affected communities"},
                ],
            },
            {
                "issue": "Social Security",
                "subtitle": "Protecting retirement benefits",
                "votes": [],
            },
            {
                "issue": "National Debt",
                "subtitle": "Government spending and the deficit",
                "votes": [
                    {"bill_number": "H.R. 1", "vote": "Yea", "summary": "Tax cuts and spending increases", "deficit": "+$3.4 trillion"},
                    {"bill_number": "H.R. 152", "vote": "Yea", "summary": "Hurricane relief spending", "deficit": "+$100 billion"},
                ],
            },
        ],
        "votes": [
            {
                "bill_number": "H.R. 1",
                "bill_title": "One Big Beautiful Bill Act",
                "one_liner": "Keeps tax cuts in place, adds money for border security and the military, and makes cuts to Medicaid and other government aid programs — all in one big bill.",
                "vote": "Yea",
                "date": "2025-05-22",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Taxes",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 1,
                "cbo_deficit_impact": "+$3.4 trillion over 10 years",
                "cbo_deficit_billions": 3400,
            },
            {
                "bill_number": "H.R. 5484",
                "bill_title": "Securing the Border for America Act",
                "one_liner": "Hires 22,000 new Border Patrol agents over 5 years, finishes building the border wall, and requires asylum seekers to wait in Mexico.",
                "vote": "Yea",
                "date": "2025-02-04",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Immigration",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 5484,
            },
            {
                "bill_number": "H.R. 152",
                "bill_title": "Disaster Relief Supplemental Appropriations Act",
                "one_liner": "Sends $100 billion in emergency aid to communities hit by Hurricanes Helene and Milton for disaster relief, small business loans, and rebuilding roads and bridges.",
                "vote": "Yea",
                "date": "2025-03-14",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Infrastructure",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 152,
                "cbo_deficit_impact": "+$100 billion",
                "cbo_deficit_billions": 100,
            },
            {
                "bill_number": "H.R. 318",
                "bill_title": "No Tax on Tips Act",
                "one_liner": "Stops the government from taxing tips for workers like servers and bartenders, up to $25,000 a year.",
                "vote": "Yea",
                "date": "2025-04-30",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Taxes",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 318,
            },
            {
                "bill_number": "H.R. 6934",
                "bill_title": "Parents Bill of Rights Act",
                "one_liner": "Gives parents the right to see what their kids are being taught, be told about any violence at school, and say yes or no before their kids take personal surveys.",
                "vote": "Yea",
                "date": "2025-03-06",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Education",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 6934,
            },
            {
                "bill_number": "H.R. 1040",
                "bill_title": "REAL ID Modernization Act",
                "one_liner": "Pushes back the deadline for REAL ID to May 2027 and lets states offer digital driver's licenses on your phone.",
                "vote": "Yea",
                "date": "2025-04-10",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Government Operations",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 1040,
            },
            {
                "bill_number": "H.R. 6017",
                "bill_title": "SAVE Act",
                "one_liner": "Requires people to prove they are US citizens to register to vote and makes states remove non-citizens from voter lists within 90 days.",
                "vote": "Yea",
                "date": "2025-02-27",
                "result": "Passed",
                "chamber": "House",
                "policy_area": "Government Operations",
                "congress": 119,
                "bill_type": "HR",
                "bill_number_raw": 6017,
            },
        ],
        "policy_areas": ["Taxes", "Government Operations", "Immigration", "Infrastructure", "Education"],
    },
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


def get_mock_member_votes(bioguide_id: str) -> dict | None:
    """Return mock voting record for a member in demo mode."""
    return MOCK_MEMBER_VOTES.get(bioguide_id)
