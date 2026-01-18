"""
Dutch to English job title translations
Common municipal employee roles and functions
"""

DUTCH_TO_ENGLISH_ROLES = {
    # Council and governance
    "Raadslid": "Council Member",
    "Burgemeester": "Mayor",
    "Burgemeester waarnemend": "Acting Mayor",
    "Locoburgemeester": "Deputy Mayor",
    "Wethouder": "Alderman",
    "Griffier": "Secretary to the Council",
    "Raadsgriffier": "Council Secretary",
    "Plaatsvervangend griffier": "Deputy Council Secretary",
    "Fractievoorzitter": "Faction Leader",
    "Fractievertegenwoordiger": "Faction Representative",
    "Gemeentesecretaris": "Municipal Secretary",
    
    # Management and administration
    "Directeur": "Director",
    "Adjunct-directeur": "Deputy Director",
    "Teamleider": "Team Leader",
    "Manager": "Manager",
    "Coördinator": "Coordinator",
    "Beleidsadviseur": "Policy Advisor",
    "Beleidsmedewerker": "Policy Officer",
    "Beleidscoördinator": "Policy Coordinator",
    
    # Legal and compliance
    "Juridische zaken": "Legal Affairs",
    "Juriste": "Legal Counsel",
    "Woo-contactpersoon": "WOO Contact Person",
    "Woo-coördinator": "WOO Coordinator",
    "Compliance officer": "Compliance Officer",
    
    # Finance and audit
    "Financieel adviseur": "Financial Advisor",
    "Boekhoudkundige": "Accountant",
    "Controller": "Controller",
    "Auditeur": "Auditor",
    
    # HR and Organization
    "HR-adviseur": "HR Advisor",
    "Personeelsadviseur": "Personnel Advisor",
    "Organisatieadviseur": "Organization Advisor",
    
    # Communication and PR
    "Communicatiemedewerker": "Communications Officer",
    "Persvoorlichter": "Press Officer",
    "Communicatieadviseur": "Communications Advisor",
    
    # IT and Systems
    "ICT-beheerder": "IT Administrator",
    "Systeembeheerder": "Systems Administrator",
    "Informatiemanager": "Information Manager",
    
    # Social services
    "Maatschappelijk werker": "Social Worker",
    "Casemanager": "Case Manager",
    "Hulpverlener": "Support Worker",
    
    # Planning and development
    "Planner": "Planner",
    "Urbanist": "Urban Planner",
    "Architect": "Architect",
    "Projectmanager": "Project Manager",
    
    # Maintenance and facilities
    "Onderhoudsmedewerker": "Maintenance Worker",
    "Facilities manager": "Facilities Manager",
    
    # Support staff
    "Secretaresse": "Secretary",
    "Receptionist": "Receptionist",
    "Administratieve medewerker": "Administrative Officer",
    "Baliemedewerker": "Counter Staff",
    
    # Specific departments (fallback to department name in English)
    "Bestuursondersteuning": "Administration & Support",
    "Financiën": "Finance",
    "Personeelszaken": "Human Resources",
    "Diensten": "Services",
    "Ruimte": "Spatial Planning",
    "Mobiliteit": "Mobility",
    "Duurzaamheid": "Sustainability",
    "Sociaal": "Social Affairs",
    "Economie": "Economy",
}


def translate_role(dutch_role: str) -> str:
    """
    Translate Dutch job title to English
    Returns original if translation not found
    """
    if not dutch_role:
        return dutch_role
    
    # Exact match
    if dutch_role in DUTCH_TO_ENGLISH_ROLES:
        return DUTCH_TO_ENGLISH_ROLES[dutch_role]
    
    # Case-insensitive match
    for dutch, english in DUTCH_TO_ENGLISH_ROLES.items():
        if dutch.lower() == dutch_role.lower():
            return english
    
    # Partial match (if it's part of a compound title)
    for dutch, english in DUTCH_TO_ENGLISH_ROLES.items():
        if dutch.lower() in dutch_role.lower():
            return english + " (derived from: " + dutch_role + ")"
    
    # Return original if no translation found
    return dutch_role
