# Regenerate every result, figure and document in the repository.
CFS = data/Divisia.xlsx

.PHONY: all data replication extensions figures paper clean

all: replication extensions figures paper

data:
	python pstar_replication.py --download-cfs $(CFS) --out output/pstar.csv
	python vintages.py --fetch

replication:
	python pstar_replication.py --cfs $(CFS) --nowcast --out output/pstar.csv
	python pstar_replication.py --cfs $(CFS) --compare-filters
	python vintages.py

extensions:
	python diagnostics/regime.py
	python diagnostics/velocity_comparison.py
	python diagnostics/uncertainty.py
	python diagnostics/attenuation.py
	python supply_shocks.py
	python nominal_gdp.py
	python filters.py
	python current_reading.py

figures:
	python plot_price_gaps.py --cfs $(CFS) --out price_gaps.png
	python plot_uncertainty.py
	python plot_frontier.py
	python plot_models.py

paper:
	mkdir -p paper
	pandoc PAPER.md -o paper/pstar-comment.docx --toc --toc-depth=2
	pandoc PAPER.md -s --toc --toc-depth=2 \
	  --metadata title="The P-Star Price Gap Is Not Identified in Real Time" \
	  -o paper/pstar-comment.html

clean:
	rm -rf output/*.csv paper/pstar-comment.*
