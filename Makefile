
VENV=venv/bin/activate
SCRIPT=generate-data.py
MASTER_DATA=data/fallbackrates.json data/countries.json data/dac3-sector-map.json
IATI_DATA=iati-downloads/*.xml

OUTPUT_DIR=docs/data

TIMESTAMP=$(OUTPUT_DIR)/timestamp

all: $(TIMESTAMP)

venv: $(VENV)

$(TIMESTAMP): $(SCRIPT) $(MASTER_DATA) iati-downloads/*.xml $(VENV)
	. $(VENV) && mkdir -p outputs && time python $(SCRIPT) $(OUTPUT_DIR) $(IATI_DATA) && touch $(TIMESTAMP)

$(VENV): requirements.txt
	(python3 -m venv venv && . $(VENV) && pip install --no-cache-dir -r requirements.txt) || rm -rf venv

push-output: $(TIMESTAMP)
	cd docs && git add . && git commit -m "Updated data" && git push

clean:
	rm -rf venv $(TIMESTAMP)
