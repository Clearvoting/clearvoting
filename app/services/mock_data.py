"""Mock data for demo mode when no Congress API key is configured."""

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
            ]},
            "depiction": {"imageUrl": "https://www.congress.gov/img/member/s001217_200.jpg", "attribution": ""},
            "currentMember": True,
        },
        {
            "bioguideId": "R000595",
            "name": "Rubio, Marco",
            "directOrderName": "Marco Rubio",
            "state": "Florida",
            "district": None,
            "partyName": "Republican",
            "partyCode": "R",
            "terms": {"item": [
                {"chamber": "Senate", "congress": 119, "startYear": 2025, "endYear": None, "stateCode": "FL"},
            ]},
            "depiction": {"imageUrl": "https://www.congress.gov/img/member/r000595_200.jpg", "attribution": ""},
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
        {
            "bioguideId": "A000376",
            "name": "Ocasio-Cortez, Alexandria",
            "directOrderName": "Alexandria Ocasio-Cortez",
            "state": "New York",
            "district": 14,
            "partyName": "Democrat",
            "partyCode": "D",
            "terms": {"item": [
                {"chamber": "House of Representatives", "congress": 119, "startYear": 2025, "endYear": None, "stateCode": "NY"},
            ]},
            "depiction": {"imageUrl": "https://www.congress.gov/img/member/o000172_200.jpg", "attribution": ""},
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
            "sponsoredLegislation": {"count": 287, "url": ""},
            "cosponsoredLegislation": {"count": 1024, "url": ""},
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

MOCK_BILLS = {
    "bills": [
        {
            "congress": 119,
            "type": "HR",
            "number": "6644",
            "title": "End the Housing Crisis Act of 2026",
            "latestTitle": "End the Housing Crisis Act of 2026",
            "latestAction": {
                "actionDate": "2026-03-02",
                "text": "Cloture motion agreed to in Senate by Yea-Nay Vote. 84-6."
            },
            "policyArea": {"name": "Housing and Community Development"},
        },
        {
            "congress": 119,
            "type": "S",
            "number": "1247",
            "title": "Working Families Tax Relief Act",
            "latestTitle": "Working Families Tax Relief Act",
            "latestAction": {
                "actionDate": "2026-02-28",
                "text": "Read twice and referred to the Committee on Finance."
            },
            "policyArea": {"name": "Taxation"},
        },
        {
            "congress": 119,
            "type": "HR",
            "number": "5891",
            "title": "Secure the Border Act of 2026",
            "latestTitle": "Secure the Border Act of 2026",
            "latestAction": {
                "actionDate": "2026-02-25",
                "text": "Passed the House by Yea-Nay Vote. 228-201."
            },
            "policyArea": {"name": "Immigration"},
        },
        {
            "congress": 119,
            "type": "HR",
            "number": "4102",
            "title": "Prescription Drug Pricing Transparency Act",
            "latestTitle": "Prescription Drug Pricing Transparency Act",
            "latestAction": {
                "actionDate": "2026-02-20",
                "text": "Referred to the Subcommittee on Health."
            },
            "policyArea": {"name": "Health"},
        },
        {
            "congress": 119,
            "type": "S",
            "number": "892",
            "title": "Veterans Mental Health Access Act",
            "latestTitle": "Veterans Mental Health Access Act",
            "latestAction": {
                "actionDate": "2026-02-18",
                "text": "Committee on Veterans Affairs. Ordered to be reported with an amendment favorably."
            },
            "policyArea": {"name": "Armed Forces and National Security"},
        },
        {
            "congress": 119,
            "type": "HR",
            "number": "7201",
            "title": "Small Business AI Adoption Act",
            "latestTitle": "Small Business AI Adoption Act",
            "latestAction": {
                "actionDate": "2026-02-15",
                "text": "Referred to the Committee on Small Business."
            },
            "policyArea": {"name": "Commerce"},
        },
        {
            "congress": 119,
            "type": "S",
            "number": "601",
            "title": "Infrastructure Investment and Maintenance Act",
            "latestTitle": "Infrastructure Investment and Maintenance Act",
            "latestAction": {
                "actionDate": "2026-02-10",
                "text": "Read twice and referred to the Committee on Environment and Public Works."
            },
            "policyArea": {"name": "Transportation and Public Works"},
        },
        {
            "congress": 119,
            "type": "HR",
            "number": "3350",
            "title": "Federal Minimum Wage Increase Act",
            "latestTitle": "Federal Minimum Wage Increase Act",
            "latestAction": {
                "actionDate": "2026-02-05",
                "text": "Referred to the Committee on Education and the Workforce."
            },
            "policyArea": {"name": "Labor and Employment"},
        },
    ]
}

MOCK_BILL_DETAILS = {
    "119-hr-6644": {
        "bill": {
            "congress": 119,
            "type": "HR",
            "number": "6644",
            "title": "End the Housing Crisis Act of 2026",
            "originChamber": "House",
            "latestAction": {
                "actionDate": "2026-03-02",
                "text": "Cloture motion agreed to in Senate by Yea-Nay Vote. 84-6."
            },
            "policyArea": {"name": "Housing and Community Development"},
            "sponsors": [
                {"bioguideId": "W000823", "fullName": "Rep. Waltz, Michael [R-FL-6]"}
            ],
            "summaries": [
                {"text": "This bill addresses the housing supply shortage by providing incentives for new construction, reforming zoning regulations at the federal level, and establishing grant programs for states that reduce barriers to housing development. It authorizes $50 billion over five years for affordable housing construction and mixed-income developments."}
            ],
        },
        "subjects": {"legislativeSubjects": [
            {"name": "Housing supply and affordability"},
            {"name": "Zoning and land use"},
            {"name": "Government lending and loan guarantees"},
        ]},
    },
    "119-hr-3350": {
        "bill": {
            "congress": 119,
            "type": "HR",
            "number": "3350",
            "title": "Federal Minimum Wage Increase Act",
            "originChamber": "House",
            "latestAction": {
                "actionDate": "2026-02-05",
                "text": "Referred to the Committee on Education and the Workforce."
            },
            "policyArea": {"name": "Labor and Employment"},
            "sponsors": [
                {"bioguideId": "A000376", "fullName": "Rep. Ocasio-Cortez, Alexandria [D-NY-14]"}
            ],
            "summaries": [
                {"text": "This bill amends the Fair Labor Standards Act to increase the federal minimum wage to $17.00 per hour over a three-year period, beginning at $12.00 in the first year, $14.50 in the second year, and $17.00 in the third year. After reaching $17.00, the minimum wage would be indexed to the median hourly wage."}
            ],
        },
        "subjects": {"legislativeSubjects": [
            {"name": "Wages and earnings"},
            {"name": "Labor standards"},
        ]},
    },
}

MOCK_AI_SUMMARIES = {
    "119-hr-6644": {
        "provisions": [
            "Authorizes $50 billion over five years for construction of affordable and mixed-income housing units",
            "Establishes federal grants for states that reduce zoning restrictions on multi-family housing",
            "Creates a loan guarantee program for developers building housing in areas with vacancy rates below 5%",
            "Requires federal agencies to identify surplus federal land suitable for housing development",
            "Sets a target of 2 million new housing units within five years",
        ],
        "impact_categories": ["Housing", "Government Operations", "Infrastructure"],
    },
    "119-hr-3350": {
        "provisions": [
            "Raises the federal minimum wage from $7.25 to $12.00 per hour in year one",
            "Increases the minimum wage to $14.50 per hour in year two",
            "Increases the minimum wage to $17.00 per hour in year three",
            "After reaching $17.00, the minimum wage would be adjusted annually based on the median hourly wage",
            "Applies to all employers covered by the Fair Labor Standards Act",
        ],
        "impact_categories": ["Wages & Income", "Small Business"],
    },
    "119-s-1247": {
        "provisions": [
            "Increases the Child Tax Credit from $2,000 to $3,600 per child under age 6 and $3,000 for ages 6-17",
            "Makes the Child Tax Credit fully refundable for families with income below $75,000",
            "Increases the Earned Income Tax Credit maximum by $1,500 for workers without children",
            "Raises the standard deduction by $2,000 for individuals and $4,000 for married couples filing jointly",
        ],
        "impact_categories": ["Taxes", "Wages & Income"],
    },
    "119-hr-5891": {
        "provisions": [
            "Allocates $8 billion for construction and maintenance of physical barriers along the southern border",
            "Increases the number of Border Patrol agents by 10,000 over three years",
            "Requires employers with more than 25 employees to use E-Verify for employment eligibility",
            "Establishes a digital entry-exit tracking system at all ports of entry",
            "Reduces the asylum processing backlog by adding 200 immigration judges",
        ],
        "impact_categories": ["Immigration", "Government Operations"],
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
