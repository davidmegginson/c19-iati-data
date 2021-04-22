""" Convert IATI XML to a (simplified) JSON

Include just the fields we'll need for later use.
Also add USD equivalents for currency values

"""

import diterator, json, sys


def parse_org (org, activity_ids=False, types=False):
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
    result = {}
    for role, orgs in participating_orgs.items():
        for org in orgs:
            result.setdefault(role, []).append(parse_org(org, types=True))
    return result
            
def parse_coded_items (items, percentages=False):
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
    result = {}
    for vocabulary_code, items in map.items():
        if (filter is None or vocabulary_code in filter) and (len(items) > 0):
            result[vocabulary_code] = parse_coded_items(items, percentages)
    return result

def parse_sectors (map):
    return parse_vocabulary_map(map, percentages=True, filter=["1", "2", "10"])

def parse_tags (map):
    return parse_vocabulary_map(map, filter=["2", "3", "99"])

def parse_humanitarian_scopes (map):
    return parse_vocabulary_map(map, filter=["1-2", "2-1"])

def parse_transaction (transaction):
    return {
        "ref": transaction.ref,
        "has_humanitarian_marker": transaction.humanitarian,
        "date": transaction.date,
        "value_orig": transaction.value,
        "currency_orig": transaction.currency,
        "conversion_date": transaction.value_date,
        "recipient_countries": parse_coded_items(transaction.recipient_countries, percentages=True),
        "recipient_regions": parse_coded_items(transaction.recipient_regions, percentages=True),
        "sectors": parse_sectors(transaction.sectors_by_vocabulary),
        "provider_org": parse_org(transaction.provider_org, activity_ids=True),
        "receiver_org": parse_org(transaction.receiver_org, activity_ids=True),
    }

def parse_transactions (map):
    result = {}
    for type in ("1", "2", "3", "4", "11",):
        transaction_data = [parse_transaction(transaction) for transaction in map.get(type, []) if transaction.value != 0]
        if len(transaction_data) > 0:
            result[type] = transaction_data
    return result

def parse_activity (activity):
    """ Create a JSON-like data structure for a single IATI activity """
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


def main (filenames, output):
    identifiers_seen = set()
    print("[", file=output)
    for filename in filenames:
        for activity in diterator.XMLIterator(filename):
            identifier = activity.identifier
            if identifier not in identifiers_seen:
                data = parse_activity(activity)
                if identifiers_seen:
                    print(",\n", file=output) # not the first activity
                else:
                    print("\n", file=output)
                print(json.dumps(data, indent=4), file=output)
                identifiers_seen.add(identifier)
    print("\n]", file=output)

if __name__ == "__main__":
    main(sys.argv[1:], sys.stdout)

    
    
    

        
