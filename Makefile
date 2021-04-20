
VENV=venv/bin/activate
SCRIPT=iati-values.py
MASTER_DATA=data/fallbackrates.json data/countries.json data/Sector.json
IATI_DATA=iati-downloads/*.xml

all: outputs/contributions-spending.json

outputs/contributions-spending.json: $(SCRIPT) $(MASTER_DATA) iati-downloads/*.xml
	. $(VENV) && mkdir -p outputs & time python $(SCRIPT) $(IATI_DATA) > outputs/contributions-spending.json

$(VENV): requirements.txt
	python3 -m venv venv && . $(VENV) && pip install -r requirements.txt

clean:
	rm -rf venv outputs
