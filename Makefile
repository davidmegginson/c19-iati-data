
VENV=venv/bin/activate
SCRIPT=generate-data.py
MASTER_DATA=data/fallbackrates.json data/countries.json data/dac3-sector-map.json
IATI_DATA=iati-downloads/*.xml

OUTPUTS=outputs/contributions-spending.json outputs/activity-counts.json

all: $(OUTPUTS)

venv: $(VENV)

$(OUTPUTS): $(SCRIPT) $(MASTER_DATA) iati-downloads/*.xml $(VENV)
	. $(VENV) && mkdir -p outputs && time python $(SCRIPT) $(IATI_DATA)

$(VENV): requirements.txt
	python3 -m venv venv && . $(VENV) && pip install -r requirements.txt

clean:
	rm -rf venv outputs
