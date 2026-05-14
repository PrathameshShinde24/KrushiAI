"""
KrushiAI — Government Schemes Database
Curated central government agricultural schemes for Indian farmers.
"""

SCHEMES = [
    {
        "name": "PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)",
        "category": "Income Support", "emoji": "💰",
        "description": "Direct income support of ₹6,000/year to small and marginal farmer families, paid in 3 equal instalments of ₹2,000 directly to bank accounts.",
        "eligibility": "Small & marginal farmer families with cultivable land up to 2 hectares. Excludes income-tax payers and government employees.",
        "benefits": "₹6,000/year in 3 instalments of ₹2,000 each via Direct Benefit Transfer (DBT).",
        "how_to_apply": "Visit pmkisan.gov.in or nearest Common Service Centre (CSC). Aadhaar card and bank account (linked to Aadhaar) required.",
        "website": "https://pmkisan.gov.in",
        "ministry": "Ministry of Agriculture & Farmers Welfare",
    },
    {
        "name": "Pradhan Mantri Fasal Bima Yojana (PMFBY)",
        "category": "Crop Insurance", "emoji": "🛡️",
        "description": "Comprehensive crop insurance providing financial support to farmers suffering crop loss or damage due to natural calamities, pests, and diseases.",
        "eligibility": "All farmers growing notified crops in notified areas. Mandatory for loanee farmers; voluntary for non-loanee farmers.",
        "benefits": "Full insured sum for total crop loss. Premium: 2% for Kharif, 1.5% for Rabi, 5% for commercial/horticultural crops — rest paid by government.",
        "how_to_apply": "Apply through nearest bank, CSC, or pmfby.gov.in before the cut-off date for each season. Keep land records and bank details ready.",
        "website": "https://pmfby.gov.in",
        "ministry": "Ministry of Agriculture & Farmers Welfare",
    },
    {
        "name": "Kisan Credit Card (KCC)",
        "category": "Credit & Finance", "emoji": "💳",
        "description": "Flexible, revolving credit facility for farmers to meet agricultural input costs, post-harvest expenses, and personal/consumption needs.",
        "eligibility": "All farmers, tenant farmers, oral lessees, sharecroppers, and self-help groups engaged in agriculture and allied activities.",
        "benefits": "Credit up to ₹3 lakh at 7% p.a. (effective 4% with timely repayment). No collateral required up to ₹1.6 lakh.",
        "how_to_apply": "Apply at nearest nationalised bank, cooperative bank, or RRB with land records, ID proof, and passport photo.",
        "website": "https://www.nabard.org",
        "ministry": "Ministry of Agriculture & Farmers Welfare / RBI",
    },
    {
        "name": "Pradhan Mantri Krishi Sinchai Yojana (PMKSY)",
        "category": "Irrigation", "emoji": "💧",
        "description": "End-to-end irrigation solution with the motto 'Har Khet Ko Pani' (water to every field) and 'More Crop Per Drop' focusing on micro-irrigation.",
        "eligibility": "All farmers. Priority to drought-prone, water-stressed districts, and small/marginal farmers.",
        "benefits": "Subsidy on drip & sprinkler irrigation systems: 55% for small/marginal farmers, 45% for others. Includes farm ponds, water harvesting structures.",
        "how_to_apply": "Apply through State Agriculture/Horticulture Department or pmksy.gov.in. Contact Block Agriculture Officer.",
        "website": "https://pmksy.gov.in",
        "ministry": "Ministry of Jal Shakti / Agriculture & Farmers Welfare",
    },
    {
        "name": "Soil Health Card Scheme",
        "category": "Soil & Fertilizer", "emoji": "🧪",
        "description": "Provides every farmer a Soil Health Card every 2 years with crop-wise nutrient recommendations to improve productivity and reduce fertilizer costs.",
        "eligibility": "All farmers across India — free of cost.",
        "benefits": "Free soil testing every 2 years. Personalised fertilizer recommendation report with NPK and micro-nutrient advice per crop.",
        "how_to_apply": "Contact nearest Krishi Vigyan Kendra (KVK), Block Agriculture Office, or soilhealth.dac.gov.in to request soil testing.",
        "website": "https://soilhealth.dac.gov.in",
        "ministry": "Ministry of Agriculture & Farmers Welfare",
    },
    {
        "name": "National Agriculture Market (eNAM)",
        "category": "Market Access", "emoji": "🏪",
        "description": "Pan-India electronic trading portal connecting APMCs for transparent price discovery, allowing farmers to sell to buyers across India online.",
        "eligibility": "All farmers registered with their local APMC (Agricultural Produce Market Committee) mandi.",
        "benefits": "Access to pan-India market. Better price realisation through online bidding. Reduced dependence on local middlemen.",
        "how_to_apply": "Register at enam.gov.in or visit nearest eNAM-connected mandi with land record, Aadhaar, and bank passbook.",
        "website": "https://enam.gov.in",
        "ministry": "Ministry of Agriculture & Farmers Welfare",
    },
    {
        "name": "Paramparagat Krishi Vikas Yojana (PKVY)",
        "category": "Organic Farming", "emoji": "🌱",
        "description": "Promotes organic farming through cluster approach — groups of 50 farmers form clusters of 50 acres to adopt and certify organic practices together.",
        "eligibility": "Groups of minimum 50 farmers willing to adopt organic farming and form a cluster of 50 acres.",
        "benefits": "₹50,000/hectare over 3 years for certification, organic inputs, and farm conversion. PGS certification support.",
        "how_to_apply": "Contact State Agriculture Department or nearest Krishi Vigyan Kendra (KVK) to form a farmer group.",
        "website": "https://pgsindia-ncof.gov.in",
        "ministry": "Ministry of Agriculture & Farmers Welfare",
    },
    {
        "name": "PM Kisan Maandhan Yojana (PM-KMY)",
        "category": "Pension", "emoji": "👴",
        "description": "Voluntary contributory pension scheme ensuring ₹3,000/month to small and marginal farmers on reaching age 60, for a secure retirement.",
        "eligibility": "Small & marginal farmers aged 18–40 years with land holding up to 2 hectares. Must not be covered under any other pension scheme.",
        "benefits": "₹3,000/month pension after age 60. Central government contributes matching amount. Family pension on death.",
        "how_to_apply": "Enrol at nearest CSC with Aadhaar and bank passbook. Monthly contribution ranges from ₹55–₹200 depending on entry age.",
        "website": "https://maandhan.in",
        "ministry": "Ministry of Agriculture & Farmers Welfare",
    },
    {
        "name": "Agriculture Infrastructure Fund (AIF)",
        "category": "Infrastructure", "emoji": "🏗️",
        "description": "Medium–long term debt financing for post-harvest management infrastructure and community farming assets like cold storage, processing units, and warehouses.",
        "eligibility": "Farmers, FPOs, PACS, Agri-entrepreneurs, Startups, State Agencies.",
        "benefits": "Loans up to ₹2 crore with 3% interest subvention per year for up to 7 years. Credit guarantee for loans up to ₹2 crore.",
        "how_to_apply": "Apply online at agriinfra.dac.gov.in through participating banks, cooperative banks, or NABARD.",
        "website": "https://agriinfra.dac.gov.in",
        "ministry": "Ministry of Agriculture & Farmers Welfare",
    },
    {
        "name": "Rashtriya Krishi Vikas Yojana (RKVY)",
        "category": "Development", "emoji": "📈",
        "description": "Incentivises states to increase public investment in agriculture by funding projects in farm mechanisation, horticulture, and agri-infrastructure.",
        "eligibility": "State government-driven; individual farmers benefit through state-level projects and subsidies.",
        "benefits": "Farm machinery subsidies, cold chain development, post-harvest infrastructure, and agri-startup funding under RAFTAAR component.",
        "how_to_apply": "Benefits flow through State Agriculture Department. Contact District Agriculture Officer for current state schemes.",
        "website": "https://rkvy.nic.in",
        "ministry": "Ministry of Agriculture & Farmers Welfare",
    },
]

CATEGORIES = [
    "All Categories", "Income Support", "Crop Insurance", "Credit & Finance",
    "Irrigation", "Soil & Fertilizer", "Market Access",
    "Organic Farming", "Pension", "Infrastructure", "Development",
]


def search_schemes(query: str = "", category: str = "All Categories") -> list[dict]:
    """Filter and return schemes matching query and category."""
    results = SCHEMES
    if category != "All Categories":
        results = [s for s in results if s["category"] == category]
    if query.strip():
        q = query.strip().lower()
        results = [
            s for s in results
            if q in s["name"].lower()
            or q in s["description"].lower()
            or q in s["category"].lower()
            or q in s["benefits"].lower()
        ]
    return results
