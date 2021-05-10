""" Download IATI files from D-Portal
Produces multiple output files, each containing up to 1,000 IATI activities

Usage:

    python3 download-iati.py <output_dir>

"""

import pathlib, requests, sys, urllib.parse

#
# Constants
#

LIMIT = 1000
""" Maximum activities in each output file """

DPORTAL_URL = "http://d-portal.org/dquery?form=xml&sql="
""" URL base for API queries """

DPORTAL_QUERY = """
SELECT * FROM xson WHERE root = '/iati-activities/iati-activity' AND
    (xson->>'/reporting-org@secondary-reporter'='0' OR xson->>'/reporting-org@secondary-reporter'='' OR
    xson->>'/reporting-org@secondary-reporter' IS NULL) AND aid IN (
    SELECT aid FROM xson WHERE
    (
        root='/iati-activities/iati-activity/humanitarian-scope' AND
        xson->>'@type'='1' AND
        xson->>'@vocabulary'='1-2' AND
        xson->>'@code'='EP-2020-000012-001'
    ) OR (
        root='/iati-activities/iati-activity/humanitarian-scope' AND
        xson->>'@type'='2' AND
        xson->>'@vocabulary'='2-1' AND
        xson->>'@code'='HCOVD20'
    ) OR (
        root='/iati-activities/iati-activity/tag' AND
        xson->>'@vocabulary'='99' AND
        xson->>'@vocabulary-uri' IS NULL AND
        UPPER(xson->>'@code')='COVID-19'
    ) OR (
        root='/iati-activities/iati-activity/title/narrative' AND
        to_tsvector('simple', xson->>'') @@ to_tsquery('simple','COVID | CORONAVIRUS')
    ) OR (
        root='/iati-activities/iati-activity/description/narrative' AND
        to_tsvector('simple', xson->>'') @@ to_tsquery('simple','COVID | CORONAVIRUS')
    ) OR (
        root='/iati-activities/iati-activity/transaction/description/narrative' AND
        to_tsvector('simple', xson->>'') @@ to_tsquery('simple','COVID | CORONAVIRUS')
    ) OR (
        root='/iati-activities/iati-activity/sector' AND
        xson->>'@code'='12264' AND
        (xson->>'@vocabulary'='1' OR xson->>'@vocabulary'='' OR xson->>'@vocabulary' IS NULL)  
    ) OR (
        root='/iati-activities/iati-activity/transaction/sector' AND
        xson->>'@code'='12264' AND
        (xson->>'@vocabulary'='1' OR xson->>'@vocabulary'='' OR xson->>'@vocabulary' IS NULL)  
    ) GROUP BY aid ORDER BY max(xson->>'@iati-activities:generated-datetime'), max(xson->>'@last-updated-datetime'), aid LIMIT {limit} OFFSET {offset}
)

"""
""" Query in D-Portal's SQL-like language - see https://d-portal.org/dquery/ """

#
# Main function
#

def main (output_dir):
    """ Download IATI into the specified output directory """
    output_dir = pathlib.Path(output_dir) # wrap as a pathlib object
    offset = 0
    file_template = "iati-activities-{:0>3d}.xml"

    while True:
        url = DPORTAL_URL + format(urllib.parse.quote(DPORTAL_QUERY.format(limit=LIMIT, offset=offset)))
        response = requests.get(url)
        # print(response.status_code, response.text, file=sys.stderr)
        response.raise_for_status()
        if "<iati-activity" not in response.text:
            # If the result doesn't contain any IATI activities, we're done
            return
        offset += LIMIT
        filename = output_dir / file_template.format(int(offset/LIMIT))
        with open(filename, "w") as output:
            print(response.text, file=output)

        # could replace with a proper logging function
        print(filename, "...", file=sys.stderr)    

#
# Script entry point
#
if __name__ == "__main__":
    if len(sys.argv) == 2:
        main(sys.argv[1])
        exit(0)
    else:
        print("Usage: python3 download-iati.py <output_dir>", file=sys.stderr)
        exit(2)

# end
