COVID-19 IATI data
==================

Extract commitment, spending, and financial-flow data from IATI for the international COVID-19 response.

## Usage

You must first create a directory iati-downloads/ and download all of the relevant IATI data into it. The files should be named activities-1.xml, activities-2.xml, etc.

(TODO: add a script to download the data from D-Portal)

Next, create a Python3 virtual environment and install the prerequisites:

```
$ python3 -m venv venv
$ . venv/bin/activate && pip install -r requirements.txt
```

Finally, create the directory outputs/ if it doesn't already exist, then run the Python script inside the virtual environment to generate the output data:

```
(venv)$ mkdir -p outputs && python generate-data.py iati-downloads/activities*.xml
```

After running (which will take a few minutes), the outputs/ directory will contain the following JSON files:

``outputs/activity-counts.json`` - total activities for each org, sector, and country.

``outputs/commitments-spending.json`` - commitments and spending, broken down by month, org, sector, country, humanitarian status, and strict/loose COVID-19 matching

## Output formats

### Activity counts

The file ``outputs/activity-counts.json`` consists of three top-level sections:

```
{
    "org": [ ... ],
    "sector": [ ... ],
    "country": [ ... ]
}
```

Within each section is a list of JSON objects that look like this:

```
{
    "org": "New Zealand Ministry of Foreign Affairs and Trade",
    "is_humanitarian": false,
    "is_strict": false,
    "activities": 9
}
```

(The first property will be "sector" or "country" rather than "org", depending on the section.)

``is\_humanitarian`` - true if these are activities specifically flagged as humanitarian; false otherwise

``is\_strict`` - true if these are activities that pass a strict test for relevance to COVID-19; false if they pass only a looser test

``activities`` - the total number of activities for the org, sector, or country that match the _is\_strict_ and _is\_humanitarian_ values


### Commitments and spending

The file ``outputs/commitments-spending.json`` is a list of JSON objects that look like this:

```
{
    "month": "2020-03",
    "org": "U.S. Agency for International Development",
    "country": "Afghanistan",
    "sector": "Agriculture, Forestry, Fishing",
    "is_humanitarian": false,
    "is_strict": false,
    "net": {
        "commitments": 0,
        "spending": 2311832
    },
    "total": {
        "commitments": 0,
        "spending": 2311832
    }
}
```

Each object is a breakdown of commitments and spending for each unique combination of the following independent variables:

``month`` - the month in which the money was reported, in ISO YYYY-MM format.

``org`` - the name of the reporting organisation

``country`` - the name of the recipient country

``sector`` - the name of the sector to which the money applies

``is\_humanitarian`` - true if this money was specifically flagged as humanitarian; false otherwise

``is\_strict`` - true if this money passes a stricter test for relevance to COVID-19; false if it passes only a looser test

The dependent variables are different financial amounts, in US dollars (USD):

``net`` - estimated _new_ money, excluding that received from another activity or organisation)

``total`` - estimated total money reported, including that received from another activity or organisation

Inside each of those are two different categories of outgoing money:

``commitments`` - estimated amount legally commited, in USD dollars

``spending`` - estimated disbursements and expenses, in USD dollars

## License

This software is released into the Public Domain, and comes with NO WARRANTY. See Unlicense.md for details.


