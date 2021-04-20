""" Compile total values by month, org, sector, and country for IATI activities
Also disaggregate by strict vs loose C19, and humanitarian status

"""

import datetime, diterator, json, sys

json_files = {}

def load_json (filename):
    """ Load a JSON file if not already in memory, then return it """
    global json_files
    if not filename in json_files:
        with open(filename, "r") as input:
            json_files[filename] = json.load(input)
    return json_files[filename]

org_names = {}

def get_org_name (org):
    global org_names
    if not org.ref:
        return str(org)
    elif org.ref in org_names:
        return org_names[org.ref]
    else:
        org_names[org.ref] = str(org)
        return str(org)

def get_sector_name (code):
    sector_info = load_json("data/Sector.json")
    for info in sector_info["data"]:
        if info["code"] == code:
            return info["name"]
    return "(Unspecified sector)"

def get_country_name (code):
    country_info = load_json("data/countries.json")
    for info in country_info["data"]:
        if info["iso2"] == code:
            return info["label"]["default"]
    return "(Unspecified country)"

def make_country_splits(entity, default_country="XX"):
    """ Generate recipient-country splits by percentage for an activity or transaction
    FIXME - if there's no percentage for a country, default to 100% (could overcount)
    If there are no countries, assign 1.0 (100%) to the default provided.

    """
    splits = {}
    for country in entity.recipient_countries:
        code = country.code
        if code:
            splits[code.upper()] = float(country.percentage if country.percentage else 100.0) / 100.0
    return splits if splits else { default_country: 1.0 }


def make_sector_splits(entity, vocabulary_code="1", default_sector="99999"):
    """ Generate sector splits by percentage for an activity or transaction
    FIXME - if there's no percentage for a sector, default to 100% (could overcount)
    If there are no sectors, assign 1.0 (100%) to the default provided.
    """
    splits = {}
    for sector in entity.sectors:
        code = sector.code
        if sector.vocabulary == "1" and code:
            splits[code.upper()] = float(sector.percentage if sector.percentage else 100.0) / 100.0
    return splits if splits else { default_sector: 1.0 }


def convert_to_usd (value, source_currency, isodate):
    # FIXME not using date
    value = float(value)
    source_currency = source_currency.upper().strip()
    if source_currency != "USD":
        rates = load_json("data/fallbackrates.json")
        if source_currency in rates["rates"]:
            value /= rates["rates"][source_currency]
        else:
            value = 0
    return int(round(value))
            
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

def add_transactions (transactions, types):
    total = 0
    for transaction in transactions:
        if transaction.value is None:
            continue
        elif transaction.type in types:
            total += convert_to_usd(transaction.value, transaction.currency, transaction.date)
    return total

def pack_key (parts):
    return (
        parts["month"],
        parts["org"],
        parts["country"],
        parts["sector"],
        parts["is_humanitarian"],
        parts["is_strict"],
    )

def unpack_key (key):
    return {
        "month": key[0],
        "org": key[1],
        "country": key[2],
        "sector": key[3],
        "is_humanitarian": key[4],
        "is_strict": key[5],
    }


def process_activities (filenames):

    accumulators = dict()

    activities_seen = set()

    this_month = datetime.datetime.utcnow().isoformat()[:7]

    for filename in filenames:
        for activity in diterator.XMLIterator(filename):

            #
            # Don't use the same activity twice
            #
            
            if activity.identifier in activities_seen:
                continue
            activities_seen.add(activity.identifier)

            #
            # Get the org name and C19 strictness (at activity level)
            #
            
            org = get_org_name(activity.reporting_org)
            activity_strict = is_activity_strict(activity)

            #
            # Figure out default country/sector percentage splits at the activity level
            #
            
            activity_country_splits = make_country_splits(activity)
            if not activity_country_splits:
                activity_country_splits = { "(unspecified)": 1.0 }

            activity_sector_splits = make_sector_splits(activity)
            if not activity_sector_splits:
                activity_sector_splits = { "(unspecified)": 1.0 }


            #
            # Figure out how to factor new money
            #

            # Total up the 4 kinds of transactions (with currency conversion)
            incoming_funds = add_transactions(activity.transactions, ["1"])
            outgoing_commitments = add_transactions(activity.transactions, ["2"])
            spending = add_transactions(activity.transactions, ["3", "4"])
            incoming_commitments = add_transactions(activity.transactions, ["11"])

            # Figure out total incoming money (never less than zero)
            incoming = max(incoming_commitments, incoming_funds)
            if incoming < 0:
                incoming = 0

            # Factor to apply to outgoing commitments
            if incoming == 0:
                commitment_factor = 1.0
            elif outgoing_commitments > incoming:
                commitment_factor = (outgoing_commitments - incoming) / outgoing_commitments
            else:
                commitment_factor = 0.0

            # Factor to apply to outgoing spending
            if incoming == 0:
                spending_factor = 1.0
            elif spending > incoming:
                spending_factor = (spending - incoming) / spending
            else:
                spending_factor = 0.0


            #
            # Walk through the transactions
            #

            for transaction in activity.transactions:

                #
                # Skip transactions with no values, or with out-of-range months
                #

                month = transaction.date[:7]
                if month < "2020-01" or month > this_month:
                    continue
                
                if transaction.value is None:
                    continue
                else:
                    value = convert_to_usd(transaction.value, transaction.currency, transaction.date)

                #
                # Set the factors based on the type (commitments or spending)
                #
                
                if transaction.type == "2":
                    # outgoing commitment
                    type = "commitments"
                    net_value = value * commitment_factor
                elif transaction.type in ["3", "4"]:
                    # disbursement or expenditure (== spending)
                    type = "spending"
                    net_value = value * spending_factor
                else:
                    # if it's anything else, skip it
                    continue

                #
                # Values that go into the unique key
                #
                
                parts = {
                    "month": month,
                    "org": org,
                    "country": None,
                    "sector": None,
                    "is_humanitarian": activity.humanitarian or transaction.humanitarian,
                    "is_strict": activity_strict or is_transaction_strict(transaction),
                }
                    

                #
                # Make the splits for the transaction (default to activity splits)
                #
                
                country_splits = make_country_splits(transaction)
                if not country_splits:
                    country_splits = activity_country_splits

                sector_splits = make_sector_splits(transaction)
                if not sector_splits:
                    sector_splits = activity_sector_splits

                #
                # Apply the country and sector percentage splits to the transaction
                # We may end up with multiple entries
                #

                for country, country_percentage in country_splits.items():
                    for sector, sector_percentage in sector_splits.items():

                        net_money = int(round(net_value * country_percentage * sector_percentage))
                        total_money = int(round(value * country_percentage * sector_percentage))

                        # Fill in only if we end up with a non-zero value
                        if net_money or total_money:

                            # Fill in remaining parts for the key
                            parts["country"] = country
                            parts["sector"] = sector
                            key = pack_key(parts)

                            # Add a default entry if it doesn't exist yet
                            accumulators.setdefault(key, {
                                "net": {
                                    "commitments": 0,
                                    "spending": 0,
                                },
                                "total": {
                                    "commitments": 0,
                                    "spending": 0,
                                }
                            })

                            # Add the money to the accumulators
                            accumulators[key]["net"][type] += net_money
                            accumulators[key]["total"][type] += total_money

    #
    # Return the accumulators after processing all activities and transactions
    #
    
    return accumulators


def unpack_accumulators (accumulators):
    """ Unpack the accumulators into a usable data structure """
    
    rows = []
    for key in sorted(accumulators.keys()):
        value = accumulators[key]
        parts = unpack_key(key)
        parts["net"] = accumulators[key]["net"]
        parts["total"] = accumulators[key]["total"]
        rows.append(parts)
        parts["country"] = get_country_name(parts["country"])
        parts["sector"] = get_sector_name(parts["sector"])
    return rows


#
# Main entry point
#

if __name__ == "__main__":

    # Build the accumulators from the IATI activities and transactions
    accumulators = process_activities(sys.argv[1:])

    # Unpack the accumulators into a usable data structure
    rows = unpack_accumulators(accumulators)
    print("Found {} unique data rows".format(len(rows)), file=sys.stderr)

    # Dump the result as JSON
    print(json.dumps(rows, indent=4))

