"""Versioned, editable peer-universe presets for the strategy lab."""

UNIVERSE_VERSION = 1
MIN_UNIVERSE_SIZE = 4
MAX_UNIVERSE_SIZE = 8


PEER_GROUPS = [
    {
        "id": "platforms",
        "name": "Technology Platforms",
        "sector": "Technology",
        "members": [
            {"ticker": "GOOGL", "name": "Alphabet"},
            {"ticker": "META", "name": "Meta Platforms"},
            {"ticker": "MSFT", "name": "Microsoft"},
            {"ticker": "AMZN", "name": "Amazon"},
        ],
    },
    {
        "id": "semiconductors",
        "name": "Semiconductors",
        "sector": "Technology",
        "members": [
            {"ticker": "AMD", "name": "AMD"},
            {"ticker": "NVDA", "name": "NVIDIA"},
            {"ticker": "AVGO", "name": "Broadcom"},
            {"ticker": "QCOM", "name": "Qualcomm"},
            {"ticker": "MU", "name": "Micron"},
        ],
    },
    {
        "id": "cloud-software",
        "name": "Cloud Software",
        "sector": "Technology",
        "members": [
            {"ticker": "DDOG", "name": "Datadog"},
            {"ticker": "NET", "name": "Cloudflare"},
            {"ticker": "CRWD", "name": "CrowdStrike"},
            {"ticker": "SNOW", "name": "Snowflake"},
            {"ticker": "NOW", "name": "ServiceNow"},
        ],
    },
    {
        "id": "pharma",
        "name": "Pharmaceuticals",
        "sector": "Healthcare",
        "members": [
            {"ticker": "JNJ", "name": "Johnson & Johnson"},
            {"ticker": "PFE", "name": "Pfizer"},
            {"ticker": "MRK", "name": "Merck"},
            {"ticker": "BMY", "name": "Bristol Myers Squibb"},
            {"ticker": "LLY", "name": "Eli Lilly"},
        ],
    },
    {
        "id": "managed-care",
        "name": "Managed Care",
        "sector": "Healthcare",
        "members": [
            {"ticker": "CVS", "name": "CVS Health"},
            {"ticker": "UNH", "name": "UnitedHealth"},
            {"ticker": "CI", "name": "Cigna"},
            {"ticker": "HUM", "name": "Humana"},
            {"ticker": "ELV", "name": "Elevance Health"},
        ],
    },
    {
        "id": "staples",
        "name": "Consumer Staples",
        "sector": "Consumer",
        "members": [
            {"ticker": "KO", "name": "Coca-Cola"},
            {"ticker": "PEP", "name": "PepsiCo"},
            {"ticker": "CL", "name": "Colgate-Palmolive"},
            {"ticker": "KMB", "name": "Kimberly-Clark"},
            {"ticker": "PG", "name": "Procter & Gamble"},
        ],
    },
    {
        "id": "retail",
        "name": "Retail",
        "sector": "Consumer",
        "members": [
            {"ticker": "WMT", "name": "Walmart"},
            {"ticker": "TGT", "name": "Target"},
            {"ticker": "COST", "name": "Costco"},
            {"ticker": "BJ", "name": "BJ's Wholesale"},
            {"ticker": "KR", "name": "Kroger"},
        ],
    },
    {
        "id": "aerospace",
        "name": "Aerospace & Defense",
        "sector": "Industrials",
        "members": [
            {"ticker": "GE", "name": "GE Aerospace"},
            {"ticker": "BA", "name": "Boeing"},
            {"ticker": "RTX", "name": "RTX"},
            {"ticker": "LMT", "name": "Lockheed Martin"},
            {"ticker": "NOC", "name": "Northrop Grumman"},
        ],
    },
    {
        "id": "banks",
        "name": "Banks & Capital Markets",
        "sector": "Financials",
        "members": [
            {"ticker": "JPM", "name": "JPMorgan Chase"},
            {"ticker": "BAC", "name": "Bank of America"},
            {"ticker": "C", "name": "Citigroup"},
            {"ticker": "WFC", "name": "Wells Fargo"},
            {"ticker": "GS", "name": "Goldman Sachs"},
            {"ticker": "MS", "name": "Morgan Stanley"},
        ],
    },
    {
        "id": "payments",
        "name": "Payments",
        "sector": "Financials",
        "members": [
            {"ticker": "V", "name": "Visa"},
            {"ticker": "MA", "name": "Mastercard"},
            {"ticker": "AXP", "name": "American Express"},
            {"ticker": "PYPL", "name": "PayPal"},
            {"ticker": "COF", "name": "Capital One"},
        ],
    },
    {
        "id": "energy",
        "name": "Energy Majors",
        "sector": "Energy",
        "members": [
            {"ticker": "XOM", "name": "ExxonMobil"},
            {"ticker": "CVX", "name": "Chevron"},
            {"ticker": "COP", "name": "ConocoPhillips"},
            {"ticker": "EOG", "name": "EOG Resources"},
            {"ticker": "OXY", "name": "Occidental Petroleum"},
        ],
    },
    {
        "id": "telecom",
        "name": "Telecom & Connectivity",
        "sector": "Telecom",
        "members": [
            {"ticker": "T", "name": "AT&T"},
            {"ticker": "VZ", "name": "Verizon"},
            {"ticker": "TMUS", "name": "T-Mobile"},
            {"ticker": "CMCSA", "name": "Comcast"},
            {"ticker": "CHTR", "name": "Charter Communications"},
        ],
    },
]


def serialized_peer_groups():
    return {
        "version": UNIVERSE_VERSION,
        "groups": PEER_GROUPS,
        "limits": {
            "minimum_tickers": MIN_UNIVERSE_SIZE,
            "maximum_tickers": MAX_UNIVERSE_SIZE,
        },
        "methodology_note": (
            "Presets use today's liquid US-listed peers and are editable. Historical "
            "results are conditional on the selected tickers and may contain "
            "survivorship bias."
        ),
    }
