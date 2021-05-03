COVID-19 IATI data
==================

Extract commitment and spending data from IATI.

## Usage

You can run the whole process by simply invoking

```
$ make all
```

or, if you prefer, execute the steps individually as shown below.

### Create and activate a Python3 virtual environment

```
$ make create-venv
```

…or…

```
$ python3 -m venv venv
$ . venv/bin/activate
(venv)$ pip install -r requirements.txt
```

### Download IATI data

```
(venv)$ make download-iata
```

…or…

```
(venv)$ rm -rf iati-downloads
(venv)$ mkdir iati-downloads
(venv)$ python3 download-iata.py docs/data
```

### Generate output

```
$ make generate-output
```

…or…

```
(venv)$ mkdir -p docs/data
(venv)$ python3 generate-data.py docs/data iati-downloads/*.xml
```

## Outputs

After running (which will take a few minutes), the docs/data/ directory will contain the following JSON files:

``transactions.json`` - a list of transactions in row-oriented JSON
``transactions.csv`` - a list of transactions in CSV format

### Transactions

The transactions are split by recipient country and sector, and all values are converted to USD.  For example, if a transaction or activity has 3 recipient countries and three sectors, it will result in 9 rows in the transactions table. The table has the following columns:

Name | HXL hashtag | Type | Description
-- | -- | -- | -- 
Month | #date+month | string | Transaction month in YYYY-MM format
Org | #org | string | A normalised name for the reporting organisation
Sector | #sector | string | An OECD-DAC sector grouping (higher-level than the purpose codes)
Country | #country | string | The recipient country name
Humanitarian | #indicator+bool+humanitarian | integer | 1 if the transaction is humanitarian, 0 otherwise
Strict | #indicator+bool+strict | integer | 1 if the transaction strictly meets the IATI COVID-19 guidance, 0 if it is only a loose match
Transaction type | #x_transaction_type | string | "commitments" or "spending"
Activity id | #activity+code | string | The IATI identifier for the transactions activity
Net money | #value+net | integer | _New_ money in the commitment or spending, after deduplication, in USD.
Total money | #value+total | integer | _Total_ money in the commitment or spending, without deduplication, in USD.

#### Transactions example

#date+month | #org | #sector | #country | #indicator+bool+humanitarian | #indicator+bool+strict | #x_transaction_type | #activity+code | #value+net | #value+total
-- | -- | -- | -- | -- | -- | -- | -- | -- | --
2020-01 | AECID Spanish Agency for International Development Cooperation | Agriculture, Forestry, Fishing | Bolivia (Plurinational State of) | 0 | 1 | commitments | ES-DIR3-EA0035768-Z02-20-P1-00900 | 36599 | 36599
2020-01 | AECID Spanish Agency for International Development Cooperation | Agriculture, Forestry, Fishing | Bolivia (Plurinational State of) | 0 | 1 | commitments | ES-DIR3-EA0035768-Z02-20-P1-00900 | 48799 | 48799
2020-01 | AECID Spanish Agency for International Development Cooperation | Agriculture, Forestry, Fishing | Bolivia (Plurinational State of) | 0 | 1 | commitments | ES-D

## License

This software is released into the Public Domain, and comes with NO WARRANTY. See Unlicense.md for details.


