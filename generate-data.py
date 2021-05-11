""" Compile total values by month, org, sector, and country for IATI activities
Also disaggregate by strict vs loose C19, and humanitarian status

"""

import datetime, diterator, hxl, logging, re, sys

logger = logging.getLogger(__name__)


#
# Constants
#

DEFAULT_ORG = "(unspecified org)"

TRANSACTIONS_JSON = "transactions.json"

TRANSACTIONS_CSV = "transactions.csv"

TRANSACTION_HEADERS = [
    [
        "Month",
        "Reporting org",
        "Reporting org type",
        "Sector",
        "Recipient country",
        "Humanitarian?",
        "Strict?",
        "Transaction type",
        "Activity id",
        "Net money",
        "Total money"
    ],
    [
        "#date+month",
        "#org+name",
        "#org+type",
        "#sector",
        "#country",
        "#indicator+bool+humanitarian",
        "#indicator+bool+strict",
        "#x_transaction_type",
        "#activity+code",
        "#value+net",
        "#value+total"
    ],
]


FLOWS_JSON = "flows.json"

FLOWS_CSV = "flows.csv"

FLOW_HEADERS = [
    [
        "Reporting org",
        "Reporting org type",
        "Provider org",
        "Receiver org",
        "Humanitarian?",
        "Strict?",
        "Transaction type",
        "Transaction direction",
        "Total money",
    ],
    [
        "#org+name+reporting",
        "#org+reporting+type",
        "#org+name+provider",
        "#org+name+receiver",
        "#indicator+bool+humanitarian",
        "#indicator+bool+strict",
        "#x_transaction_type",
        "#x_transaction_direction",
        "#value+total"
    ],
]

TRANSACTION_TYPE_INFO = {
    "1": {
        "label": "Incoming Funds",
        "classification": "spending",
        "direction": "incoming",
    },
    "2": {
        "label": "Outgoing Commitment",
        "classification": "commitments",
        "direction": "outgoing",
    },
    "3": {
        "label": "Disbursement",
        "classification": "spending",
        "direction": "outgoing",
    },
    "4": {
        "label": "Expenditure",
        "classification": "spending",
        "direction": "outgoing",
    },
    "11": {
        "label": "Incoming Commitment",
        "classification": "commitments",
        "direction": "incoming",
    },
}    

#
# Global variables
#

json_files = {}
""" Cache for loaded JSON files """

org_names = None
""" Map from IATI identifiers to organisation names """


#
# Utility functions
#

def load_json (filename):
    """ Load a JSON file if not already in memory, then return it """
    global json_files
    if not filename in json_files:
        with open(filename, "r") as input:
            json_files[filename] = json.load(input)
    return json_files[filename]

def clean_string (s):
    """ Normalise whitespace in a single, and remove any punctuation at the start/end """
    s = re.sub(r'^\W*(\w.*)\W*$', r'\1', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

#
# Lookup functions
#

def get_org_name (org):
    """ Standardise organisation names
    For now, use the first name found for an identifier.
    Later, we can reference the registry.

    """
    global org_names

    # Prime with org identifiers from code4iati
    if org_names is None:
        map = load_json("data/IATIOrganisationIdentifier.json")
        org_names = {}
        for entry in map["data"]:
            code = clean_string(entry["code"]).lower()
            org_names[code] = clean_string(entry["name"])

    name = None if org is None or org.name is None else clean_string(str(org.name))
    ref = None if org is None or org.ref is None else clean_string(str(org.ref)).lower()

    # We have a ref and an existing match
    if ref and ref in org_names:
        # existing match
        return org_names[ref]

    # No existing match, but we have a name
    if name:
        if ref is not None:
            # if there's a ref, save it for future matching
            org_names[ref] = name
        return name

    # We can't figure out anything
    return DEFAULT_ORG

def get_sector_group_name (code):
    """ Look up a group name for a 3- or 5-digit sector code.

    """
    sector_info = load_json("data/dac3-sector-map.json")
    code = code[:3]
    if code in sector_info:
        return sector_info.get(code)["dac-group"]
    else:
        return "(Unspecified sector)"

def get_country_name (code):
    country_info = load_json("data/countries.json")
    for info in country_info["data"]:
        if info["iso2"] == code:
            return info["label"]["default"]
    return "(Unspecified country)"

def convert_to_usd (value, source_currency, isodate):
    # FIXME not using date
    source_currency = source_currency.upper().strip()
    if value != 0.0 and source_currency != "USD":
        rates = load_json("data/fallbackrates.json")
        if source_currency in rates["rates"]:
            value /= rates["rates"][source_currency]
        else:
            value = 0
    return int(round(value))


#
# Business-logic functions
#

def make_country_splits(entity, default_splits=None, default_country="XX"):
    """ Generate recipient-country splits by percentage for an activity or transaction
    FIXME - if there's no percentage for a country, default to 100% (could overcount)
    If there are no countries, assign 1.0 (100%) to the default provided.
    If default splits are provided (e.g. for an activity), use those.

    """
    splits = {}
    for country in entity.recipient_countries:
        code = country.code
        if code:
            splits[code.upper()] = float(country.percentage if country.percentage else 100.0) / 100.0
            
    if splits:
        # we have actual splits to return
        return splits
    elif default_splits is not None:
        # return the default splits
        return default_splits
    else:
        # default to 100% for unknown country
        return { default_country: 1.0 }


def make_sector_splits(entity, default_splits=None, default_sector="99999"):
    """ Generate sector splits by percentage for an activity or transaction
    FIXME - if there's no percentage for a sector, default to 100% (could overcount)
    If there are no sectors, assign 1.0 (100%) to the default provided.
    """
    splits = {}
    sectors = entity.sectors

    # Prefer 3-digit codes to 5-digit
    if "2" in [sector.vocabulary for sector in sectors]:
        vocabulary_code = "2"
    else:
        vocabulary_code = "1"
        
    for sector in sectors:
        code = sector.code
        if sector.vocabulary == vocabulary_code and code:
            splits[code.upper()] = float(sector.percentage if sector.percentage else 100.0) / 100.0
            
    if splits:
        # we have actual splits to return
        return splits
    elif default_splits is not None:
        # return the default splits
        return default_splits
    else:
        # default to 100% for unknown sector
        return { default_sector: 1.0 }


def has_c19_scope (scopes):
    """ Check if the COVID-19 GLIDE number or HRP code is present """
    for scope in scopes:
        if scope.type == "1" and scope.vocabulary == "1-2" and scope.code.upper() == "EP-2020-000012-001":
            return True
        elif scope.type == "2" and scope.vocabulary == "2-1" and scope.code.upper() == "HCOVD20":
            return True
    return False

def has_c19_tag (tags):
    """ Check if the COVID-19 tag is present """
    for tag in tags:
        if tag.vocabulary == "99" and tag.code.upper() == "COVID-19":
            return True
    return False

def has_c19_sector (sectors):
    """ Check if the DAC COVID-19 sector code is present """
    for sector in sectors:
        if sector.vocabulary == "1" and sector.code == "12264":
            return True
    return False

def is_c19_narrative (narratives):
    """ Check a dict of different-language text for the string "COVID-19" (case-insensitive) """
    for lang, text in narratives.items():
        if "COVID-19" in text.upper():
            return True
    return False

def is_activity_strict (activity):
    return True if (
        has_c19_scope(activity.humanitarian_scopes) or
        has_c19_tag(activity.tags) or
        has_c19_sector(activity.sectors) or
        is_c19_narrative(activity.title.narratives)
    ) else False

def is_transaction_strict (transaction):
    return True if (
        has_c19_sector(transaction.sectors) or
        (transaction.description and is_c19_narrative(transaction.description.narratives))
    ) else False

def sum_transactions (transactions, types):
    total = 0
    for transaction in transactions:
        if transaction.value is None:
            continue
        elif transaction.type in types:
            total += convert_to_usd(transaction.value, transaction.currency, transaction.date)
    return total


#
# Main processing function
#

def process_activities (filenames):

    transactions = list()

    flows = []

    activities_seen = set()

    this_month = datetime.datetime.utcnow().isoformat()[:7]

    for filename in filenames:
        for activity in diterator.XMLIterator(filename):

            # Don't use the same activity twice
            identifier = activity.identifier
            if identifier in activities_seen:
                continue
            activities_seen.add(identifier)

            # Skip activities from a secondary reporter (should have been filtered out already)
            if activity.secondary_reporter:
                continue

            # Get the reporting-org name and C19 strictness at activity level
            org = get_org_name(activity.reporting_org)
            org_type = str(activity.reporting_org.type)
            activity_strict = is_activity_strict(activity)

            # Figure out default country/sector percentage splits at the activity level
            activity_country_splits = make_country_splits(activity)
            activity_sector_splits = make_sector_splits(activity)

            #
            # Figure out how to factor new money
            #

            # Total up the 4 kinds of transactions (with currency conversion to USD)
            incoming_funds = sum_transactions(activity.transactions, ["1"])
            outgoing_commitments = sum_transactions(activity.transactions, ["2"])
            spending = sum_transactions(activity.transactions, ["3", "4"])
            incoming_commitments = sum_transactions(activity.transactions, ["11"])

            # Figure out total incoming money (never less than zero)
            incoming = max(incoming_commitments, incoming_funds)
            if incoming < 0:
                incoming = 0

            # Factor to apply to outgoing commitments for net new money
            if incoming == 0:
                commitment_factor = 1.0
            elif outgoing_commitments > incoming:
                commitment_factor = (outgoing_commitments - incoming) / outgoing_commitments
            else:
                commitment_factor = 0.0

            # Factor to apply to outgoing spending for net new money
            if incoming == 0:
                spending_factor = 1.0
            elif spending > incoming:
                spending_factor = (spending - incoming) / spending
            else:
                spending_factor = 0.0


            #
            # Walk through the activity's transactions one-by-one, and split by country/sector
            #

            for transaction in activity.transactions:

                month = transaction.date[:7]
                if month < "2020-01" or month > this_month or not transaction.value:
                    # Skip transactions with no values or with out-of-range months
                    continue

                type = transaction.type
                if type in TRANSACTION_TYPE_INFO:
                    type_info = TRANSACTION_TYPE_INFO[type]
                else:
                    # skip transaction types that don't interest us
                    continue

                # Convert the transaction value to USD
                value = convert_to_usd(transaction.value, transaction.currency, transaction.date)

                # Set the net (new money) factors based on the type (commitments or spending)
                if type_info["direction"] == "outgoing":
                    if type_info["classification"] == "commitments":
                        net_value = value * commitment_factor
                    else:
                        net_value = value * spending_factor

                # transaction status defaults to activity
                if transaction.humanitarian is None:
                    is_humanitarian = activity.humanitarian
                else:
                    is_humanitarian = transaction.humanitarian
                is_strict = activity_strict or is_transaction_strict(transaction)

                # Make the splits for the transaction (default to activity splits)
                country_splits = make_country_splits(transaction, activity_country_splits)
                sector_splits = make_sector_splits(transaction, activity_sector_splits)


                # Apply the country and sector percentage splits to the transaction
                # generate multiple split transactions
                for country, country_percentage in country_splits.items():
                    for sector, sector_percentage in sector_splits.items():

                        sector_name = get_sector_group_name(sector)
                        country_name = get_country_name(country)

                        #
                        # Add to transactions
                        #

                        net_money = int(round(net_value * country_percentage * sector_percentage))
                        total_money = int(round(value * country_percentage * sector_percentage))

                        # Fill in only if we end up with a non-zero value
                        if type_info["direction"] == "outgoing" and (net_money != 0 or total_money != 0):

                            # add to transactions
                            transactions.append([
                                month,
                                org,
                                org_type,
                                sector_name,
                                country_name,
                                1 if is_humanitarian else 0,
                                1 if is_strict else 0,
                                type_info["classification"],
                                identifier,
                                net_money,
                                total_money,
                            ])

                    #
                    # Add to flows
                    #
                    if type_info["direction"] == "incoming":
                        provider = get_org_name(transaction.provider_org)
                        receiver = None
                    else:
                        provider = None
                        receiver = get_org_name(transaction.receiver_org)
                    if org != provider and org != receiver and org != DEFAULT_ORG:
                        # ignore internal transactions or unknown reporting orgs
                        flows.append([
                            org,
                            org_type,
                            provider,
                            receiver,
                            1 if is_humanitarian else 0,
                            1 if is_strict else 0,
                            type_info["classification"],
                            type_info["direction"],
                            total_money
                        ])

    return (transactions, flows,)


#
# Main entry point for script
#

if __name__ == "__main__":

    import json, csv, os.path

    logging.basicConfig(stream=sys.stderr, level=logging.INFO)

    if len(sys.argv) < 3:
        print("Usage: python3 generate-data.py <output-dir> <xml-file ...>", file=sys.stderr)
        exit(2)

    output_dir = sys.argv[1]
    logger.info("Writing output to directory %s", output_dir)

    # Build the accumulators from the IATI activities and transactions
    transactions, flows = process_activities(sys.argv[2:])
    logger.info("Processed %d transactions", len(transactions))
    logger.info("Processed %d flows", len(flows))

    #
    # Write transactions
    #

    # Add headers and sort the transactions.
    transactions = TRANSACTION_HEADERS + sorted(transactions)

    # Write the JSON
    with open(os.path.join(output_dir, TRANSACTIONS_JSON), "w") as output:
        json.dump(transactions, output)

    # Write the CSV
    with open(os.path.join(output_dir, TRANSACTIONS_CSV), "w") as output:
        writer = csv.writer(output)
        for row in transactions:
            writer.writerow(row)

    #
    # Prepare and write flows
    #

    # Add headers and aggregate
    flows = hxl.data(FLOW_HEADERS + flows).count(
        FLOW_HEADERS[1][:-1], # make a list of patterns from all but the last column of the hashtag row
        aggregators="sum(#value+total) as Total money#value+total"
    ).cache()

    # Write the JSON
    with open(os.path.join(output_dir, FLOWS_JSON), "w") as output:
        for line in flows.gen_json():
            print(line, file=output, end="")

    # Write the CSV
    with open(os.path.join(output_dir, FLOWS_CSV), "w") as output:
        for line in flows.gen_csv():
            print(line, file=output, end="")

# end
