
VENV=venv/bin/activate
MASTER_DATA=data/fallbackrates.json data/countries.json data/dac3-sector-map.json
IATI_DATA=iati-downloads/*.xml

DOWNLOAD_DIR=iati-downloads
OUTPUT_DIR=docs/data

OUTPUT_TIMESTAMP=$(OUTPUT_DIR)/timestamp

all: generate-output

download-iati: $(IATI_DIR)

generate-output: $(OUTPUT_TIMESTAMP)

publish-output: $(OUTPUT_TIMESTAMP)
	cd docs && git add . && git commit -m "Updated data" && git push

create-venv: $(VENV)

clean:
	rm -rf venv $(OUTPUT_DIR)/* $(DOWNLOAD_DIR)

$(OUTPUT_TIMESTAMP): generate-data.py $(MASTER_DATA) $(IATI_DATA) $(VENV)
	. $(VENV) && mkdir -p outputs && time python generate-data.py $(OUTPUT_DIR) $(IATI_DATA) && touch $(OUTPUT_TIMESTAMP)

$(VENV): requirements.txt
	(python3 -m venv venv && . $(VENV) && pip install --no-cache-dir -r requirements.txt) || rm -rf venv

$(IATI_DATA): $(DOWNLOAD_DIR)

$(DOWNLOAD_DIR): $(VENV)
	. $(VENV) && rm -rf $(DOWNLOAD_DIR) && mkdir $(DOWNLOAD_DIR) && python download-iati.py $(DOWNLOAD_DIR)

