Methology notes
===============

## Currency

We convert all transaction values to USD before performing any other operations.

## Deduplication

To avoid duplicate counting, we calculate a "net" value for new commitments in each activity, as well as a "total" value for all commitments and spending. To come up with a net value, we take the following steps:

1. Take the higher of the sum of all incoming commitments (type "11") or the sum of all incoming funding (type "1") as _incoming money_: if negative, use 0.
2. Add the values of all outgoing commitments (type "2") to get _total commitments_.
3. Subtract the _incoming money_ from _total commitments_ to get _net (new) commitments_ (but replace a negative result with zero).
4. Add the values of all disbursements (type "3") and expenditures (type "4") to get _total spending_.
5. Subtract the _incoming money_ from _total spending_ to get _net (new) spending_ (but replace a negative result with zero).

Note that we don't always subtract incoming commitments from outgoing commitments, or incoming funding from disbursements or expenditures; instead, we're looking for the highest value of incoming money we can find for the activity (commitments or funding) and subtracting that from everything. That gives the best approximation of what part of the activity is "new" money.

When we are filtering the data to just a single organisation, we use _total commitments_ and _total spending_, because there is (or should be) no risk of duplicate counting; in every other situation, where we are potentially counting money reported by more than one organisation, we use _net commitments_ and _net spending_, calculated as described above.

## Organisations

We look up organisations based on IATI identifiers when possible. All organisation names have leading/trailing whitespace removed and internal whitespace normalised.

## Sectors

We use OECD DAC3 and DAC5 purpose codes for our sectors, but roll them up one further level to DAC _groups_.  See [data/dac3-sector-map.json](data/dac3-sector-map.json) for the mappings.  The groups are at a higher level of abstraction, closer to humanitarian sectors, so they make more sense for a humanitarian audience.

## Disaggregation

If an activity or transaction lists multiple sectors or recipient countries, we divide each transaction by the percentages given for both. We use the sectors and recipient countries for the transaction if provided, and otherwise default to those for the transaction's activity.  For example, if a transaction with a value of $1,000,000 was assigned 30% to Senegal and 70% to Mali, and 50% to Health and 50% to education, we would split it into four virtual transactions:

1. Senegal, Health: $150,000
2. Senegal, Education: $150,000
3. Mali, Health: $350,000
4. Mali, Education: $350,000

## Relevance

We exclude all transactions that meet any of the following criteria:

* the activity's reporting organisation is a secondary reporter
* the activity's reporting organisation is unspecified
* the transaction's value is 0
* the transaction is not of types 1 (Incoming Funding), 2 (Outgoing Commitment), 3 (Disbursement), 4 (Expenditure), or 11 (Incoming Commitment)

If a transaction or its activity meets the strict conditions in the [IATI COVID-19 Guidance](https://iatistandard.org/en/news/updated-covid-19-guidance-iati-publishers/) or uses the new DAC sector code "12264", we consider it as strictly relevant to COVID-19, *except* that we do not accept the string "COVID-19" in the _activity_ description (rather than title), because it appears there too often by accident.

If a transaction has the string "COVID-19" in the _activity_ description, or if it uses a similar free-text string like "COVID" or "CORONAVIRUS" (case-insensitive), we consider it as only loosely relevant to COVID-19.

## Humanitarian status

We consider an activity as a whole to be humanitarian if it has the attribute iati-activity/@humanitarian set to "1".  We consider a transaction to be humanitarian if it has transaction/@humanitarian set to "1", or if transaction/@humanitarian is not present and the transaction's activity is humanitarian.

## Dates

We roll all dates up to the month level for easier aggregation.

## Flows

For the flows data, we ignore all transactions within the same organisation. We aggregate transactions with the same metadata so that there is just one row for each combination.
