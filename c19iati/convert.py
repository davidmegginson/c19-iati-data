""" Convert IATI XML activities to (simplified) line-delimited JSON

Include just the fields we'll need for later use. Also add USD equivalents for currency values

Note that there is one JSON object on each line of the output file (it is not a JSON array).

Usage:

    python -m c19iati.convert <file1.xml> [file2.xml ...] > activities.lines.json

"""

import diterator, json, sys

from c19iati.currency import convert_to_usd

#
# Parsing functions
#

def parse_org (org, activity_ids=False, types=False):
    """ Parse an organisation record """
    if org is None:
        return None
    else:
        result = {
            "ref": org.ref,
            "name": str(org.name),
        }
        if types:
            result["type"] = org.type
        if activity_ids:
            result["activity_id"] = org.activity_id
        return result

def parse_participating_orgs (participating_orgs):
    """ Parse a list of participating orgs """
    result = {}
    for role, orgs in participating_orgs.items():
        for org in orgs:
            result.setdefault(role, []).append(parse_org(org, types=True))
    return result
            
def parse_coded_items (items, percentages=False):
    """ Parse a list of coded items (e.g. sectors, countries) """
    result = []
    for item in items:
        entry = {
            "code": item.code,
            "label": str(item.narrative),
        }
        if percentages:
            entry["percentage"] = float(item.percentage) if item.percentage else 100.0
        result.append(entry)
    return result

def parse_vocabulary_map (map, percentages=False, filter=None):
    """ Parse a map of coded items in different vocabularies (e.g. sectors, tags) """
    result = {}
    for vocabulary_code, items in map.items():
        if (filter is None or vocabulary_code in filter) and (len(items) > 0):
            result[vocabulary_code] = parse_coded_items(items, percentages)
    return result

def parse_sectors (map):
    """ Parse the sectors for an activity or transaction """
    return parse_vocabulary_map(map, percentages=True, filter=["1", "2", "10"])

def parse_tags (map):
    """ Parse the tags for an activity """
    return parse_vocabulary_map(map, filter=["2", "3", "99"])

def parse_humanitarian_scopes (map):
    """ Parse the humanitarian scopes for an activity """
    return parse_vocabulary_map(map, filter=["1-2", "2-1"])

def parse_transaction (transaction):
    """ Parse a single transaction for an activity """

    # We'll use these more than once
    value = transaction.value
    currency = transaction.currency
    value_date = transaction.value_date
    
    return {
        "ref": transaction.ref,
        "has_humanitarian_marker": transaction.humanitarian,
        "date": transaction.date,
        "value_orig": value,
        "currency_orig": currency,
        "conversion_date": transaction.value_date,
        "value_usd": convert_to_usd(value, currency, value_date),
        "recipient_countries": parse_coded_items(transaction.recipient_countries, percentages=True),
        "recipient_regions": parse_coded_items(transaction.recipient_regions, percentages=True),
        "sectors": parse_sectors(transaction.sectors_by_vocabulary),
        "provider_org": parse_org(transaction.provider_org, activity_ids=True),
        "receiver_org": parse_org(transaction.receiver_org, activity_ids=True),
    }

def parse_transactions (map):
    """ Parse all the transactions for an activity """
    result = {}
    for type in ("1", "2", "3", "4", "11",):
        transaction_data = [parse_transaction(transaction) for transaction in map.get(type, []) if transaction.value != 0]
        if len(transaction_data) > 0:
            result[type] = transaction_data
    return result

def parse_activity (activity):
    """ Top-level parser: create a JSON-like data structure for a single IATI activity """
    return {
        "identifier": activity.identifier,
        "reporting_org": parse_org(activity.reporting_org, types=True),
        "participating_orgs": parse_participating_orgs(activity.participating_orgs_by_role),
        "has_humanitarian_marker": activity.humanitarian,
        "title": activity.title.narratives,
        "description": activity.description.narratives,
        "recipient_countries": parse_coded_items(activity.recipient_countries, percentages=True),
        "recipient_regions": parse_coded_items(activity.recipient_regions, percentages=True),
        "sectors": parse_sectors(activity.sectors_by_vocabulary),
        "tags": parse_tags(activity.tags_by_vocabulary),
        "humanitarian_scopes": parse_humanitarian_scopes(activity.humanitarian_scopes_by_vocabulary),
        "transactions": parse_transactions(activity.transactions_by_type),
    }

#
# Main module entry point
#

def main (filenames, output):
    """ Parse IATI activities from the XML files provided, and write to output (file-like object) as line-delimited JSON """

    # for skipping duplicate activities
    identifiers_seen = set()

    # keep track of how many activities we've seen
    counter = 0

    # read each XML IATI file
    for filename in filenames:

        # parse each non-duplicate activity and send to output as JSON
        for activity in diterator.XMLIterator(filename):
            identifier = activity.identifier
            if identifier not in identifiers_seen:
                # we haven't seen this yet
                print(json.dumps(parse_activity(activity)), file=output)
                identifiers_seen.add(identifier)
                if (counter + 1) % 100 == 0:
                    # could replace with proper logging
                    print((counter + 1), "...", file=sys.stderr)
                counter += 1

    # could replace with proper logging
    print(counter, "unique IATI activities", file=sys.stderr)

#
# Script entry point
#
                    
if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1:], sys.stdout)
        exit(0)
    else:
        print("Usage: python -m c19iati.convert <file.xml> [...] > activities.lines.json", file=sys.stderr)
        exit(2)

# end
