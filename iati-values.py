import diterator, json, sys


def make_country_splits(entity):
    """ Generate recipient-country splits by percentage for an activity or transaction """
    splits = {}
    for country in entity.recipient_countries:
         # TODO: check for bad values
        code = country.code.upper()
        splits[code] = float(country.percentage if country.percentage else 100.0) / 100.0
    return splits


def make_sector_splits(entity, vocabulary_code):
    """ Generate sector splits by percentage for an activity or transaction """
    splits = {}
    for sector in entity.sectors_by_vocabulary.get(vocabulary_code, []):
         # TODO: check for bad values
        code = sector.code.upper()
        splits[code] = float(sector.percentage if sector.percentage else 100.0) / 100.0
    return splits


def convert_currency (value, source_currency, destination_currency, isodate):
    # FIXME actually convert
    return int(round(value))


def is_activity_humanitarian (activity):
    # FIXME actually check
    return True

def is_transaction_humanitarian (transaction):
    # FIXME actually check
    return True

def is_activity_strict (activity):
    # FIXME actually check
    return True

def is_transaction_strict (transaction):
    # FIXME actually check
    return True

def add_transactions (transactions, types):
    total = 0
    for transaction in transactions:
        if transaction.value is None:
            continue
        elif transaction.type in types:
            total += convert_currency(transaction.value, transaction.currency, "USD", transaction.date)
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

    for filename in filenames:
        for activity in diterator.XMLIterator(filename):

            # Don't use the same activity twice
            if activity.identifier in activities_seen:
                continue
            activities_seen.add(activity.identifier)

            org = str(activity.reporting_org)

            activity_country_splits = make_country_splits(activity)
            if not activity_country_splits:
                activity_country_splits = { "(unspecified)": 1.0 }

            activity_sector_splits = make_sector_splits(activity, "1")
            if not activity_sector_splits:
                activity_sector_splits = { "(unspecified)": 1.0 }

            activity_humanitarian = is_activity_humanitarian(activity)
            activity_strict = is_activity_strict(activity)


            # Figure out how to factor new money

            incoming_funds = add_transactions(activity.transactions, ["1"])
            outgoing_commitments = add_transactions(activity.transactions, ["2"])
            spending = add_transactions(activity.transactions, ["3", "4"])
            incoming_commitments = add_transactions(activity.transactions, ["11"])

            incoming = max(incoming_commitments, incoming_funds)
            if incoming < 0:
                incoming = 0

            if outgoing_commitments > incoming:
                commitment_factor = (outgoing_commitments - incoming) / outgoing_commitments
            else:
                commitment_factor = 0.0

            if spending > incoming:
                spending_factor = (spending - incoming) / spending
            else:
                spending_factor = 0.0


            # Walk through the transactions

            for transaction in activity.transactions:

                if transaction.value is None:
                    continue
                else:
                    value = convert_currency(transaction.value, transaction.currency, "USD", transaction.date)

                if transaction.type == "2":
                    type = "commitments"
                    net_value = value * commitment_factor
                elif transaction.type in ["3", "4"]:
                    type = "spending"
                    net_value = value * spending_factor
                else:
                    continue

                parts = {
                    "month": transaction.date[:7],
                    "org": org,
                    "country": None,
                    "sector": None,
                    "is_humanitarian": activity_humanitarian or is_transaction_humanitarian(transaction),
                    "is_strict": activity_strict or is_transaction_strict(transaction),
                }
                    

                country_splits = make_country_splits(transaction)
                if not country_splits:
                    country_splits = activity_country_splits
                sector_splits = make_sector_splits(transaction, "1")
                if not sector_splits:
                    sector_splits = activity_sector_splits

                for country, country_percentage in country_splits.items():
                    for sector, sector_percentage in sector_splits.items():

                        net_money = int(round(net_value * country_percentage * sector_percentage))
                        total_money = int(round(value * country_percentage * sector_percentage))

                        if net_money or total_money:

                            parts["country"] = country
                            parts["sector"] = sector
                            key = pack_key(parts)
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


                            accumulators[key]["net"][type] += net_money
                            accumulators[key]["total"][type] += total_money

    return accumulators


def unpack_accumulators (accumulators):
    rows = []
    for key in sorted(accumulators.keys()):
        value = accumulators[key]
        parts = unpack_key(key)
        parts["net"] = accumulators[key]["net"]
        parts["total"] = accumulators[key]["total"]
        rows.append(parts)
    return rows

if __name__ == "__main__":
    accumulators = process_activities(sys.argv[1:])
    rows = unpack_accumulators(accumulators)
    print(json.dumps(rows, indent=4))
