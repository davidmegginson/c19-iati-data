
VENV=venv/bin/activate
MASTER_DATA=data/fallbackrates.json data/countries.json data/dac3-sector-map.json

DOWNLOAD_DIR=iati-downloads
OUTPUT_DIR=docs/data

DOWNLOAD_TARGET=$(DOWNLOAD_DIR)/iati-activities-001.xml

OUTPUT_TARGET=$(OUTPUT_DIR)/transactions.json

all: generate-output

download-iati: $(DOWNLOAD_TARGET)

generate-output: $(OUTPUT_TARGET)

publish-output: $(OUTPUT_TIMESTAMP)
	cd docs && git add . && git commit -m "Updated data" && git push

create-venv: $(VENV)

clean:
	rm -rf venv $(OUTPUT_DIR)/* $(DOWNLOAD_DIR)/*

$(OUTPUT_TARGET): generate-data.py $(MASTER_DATA) $(IATI_TARGET) $(DOWNLOAD_TARGET) $(VENV)
	. $(VENV) && mkdir -p $(OUTPUT_DIR) && (time python generate-data.py $(OUTPUT_DIR) $(DOWNLOAD_DIR)/*.xml || rm -f $(OUTPUT_DIR)/*)

$(DOWNLOAD_TARGET): $(VENV)
	. $(VENV) && rm -rf $(DOWNLOAD_DIR) && mkdir $(DOWNLOAD_DIR) && (python download-iati.py $(DOWNLOAD_DIR) || rm -rf $(DOWNLOAD_DIR)/*.xml)

$(VENV): requirements.txt
	(python3 -m venv venv && . $(VENV) && pip install --no-cache-dir -r requirements.txt) || rm -rf venv

